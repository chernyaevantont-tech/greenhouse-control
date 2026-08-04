"""E3 boiler knock-out / knock-in ablation (reviewer item #1).

Causal test of the central methodological finding: the frozen confirmatory recipe
(``physics_no_cross`` + ensemble threshold) drops the small-magnitude but
control-critical boiler term Xi(uBoil -> t_in), and THAT term -- not anything else --
governs closed-loop EPI. We hold the identification recipe, training data, MPC and
test season fixed and change ONLY that one coefficient, three ways per seed:

  baseline : the frozen recipe's model, coefficient left as identified;
  knockout : Xi(uBoil -> t_in) forced to exactly 0.0;
  knockin  : Xi(uBoil -> t_in) set to the grey-box (dense-STLSQ) value, which recovers
             the physical boiler gain the sparse recipe discarded.

Because baseline/knockout/knockin differ in a SINGLE scalar, the EPI/violation deltas are
a clean paired ablation (same seed, same everything else) -- the knock-out/knock-in design
the reviewer asked for.

Interaction check (physics library): ``physics_no_cross`` has no temperature x boiler cross
term by construction, so the paired term t*uBoil cannot be probed there. We therefore ALSO
fit the full ``physics`` library (which contains both ``uBoil`` and ``t_uBoil`` -> t_in) and
compare knocking out ``uBoil`` ALONE vs ``uBoil`` AND ``t_uBoil`` TOGETHER -- isolating
whether the linear boiler term alone carries the effect or its temperature interaction
matters too.

Mechanism (validated against pysindy 2.1.0): ``build_mpc_controller`` bakes
``bundle.model.coefficients()`` (a scaled-space matrix, rows = STATE_NAMES, columns =
["1"] + STATE_NAMES + bundle.feature_names) into CasADi at build time and never calls the
model again during the rollout. So a variant is produced by wrapping the fitted model in a
thin shim whose ``.coefficients()`` returns an edited copy of the matrix -- NO pysindy
internals are touched and the baseline bundle is never mutated. The uBoil column is located
exactly as ``coefficient_table`` / ``e3_lambda_sweep.uboil_coef`` do, so the edited cell is
guaranteed to be the same coefficient the sweep reports.

Distributed like run_e3_seeds.py / e3_lambda_sweep.py: workers shard by seed and write
e3_knockout_<tag>.csv; ``--merge`` aggregates all shards into e3_knockout_ablation.csv.

Examples
  python run_knockout_ablation.py --seeds 0,1,2 --tag s012            # explicit seeds
  python run_knockout_ablation.py --shard-index 3 --num-shards 20 \
      --seeds-all 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19 \
      --tag shard3 --out /results                                     # k8s indexed shard
  python run_knockout_ablation.py --merge --out /results              # aggregate + summary
  python run_knockout_ablation.py --seeds 0 --fast --tag smoke        # minutes-long smoke
"""
from __future__ import annotations

import argparse
import dataclasses
import glob
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402
import protocol_config as P  # noqa: E402

# Fallback grey-box uBoil->t_in gain (scaled space), the 20-seed mean of the dense
# STLSQ lambda=1e-6 row in tables/e3_lambda_sweep_table.csv. Only used if a per-seed
# grey-box refit yields a (near-)zero/NaN coefficient (should not happen at lambda=1e-6).
GREY_UBOIL_REF = 0.03568


# ── coefficient-edit shim (no pysindy internals) ─────────────────────────────

class _CoefOverride:
    """Stand-in for ``bundle.model`` that returns an edited coefficient matrix.

    ``build_mpc_controller`` only calls ``bundle.model.coefficients()`` (baked into
    CasADi at build time); every other attribute is delegated to the real fitted model,
    so ``coefficient_table``/diagnostics still work on the variant if needed.
    """

    def __init__(self, base_model, coef_matrix):
        self._base = base_model
        self._C = np.asarray(coef_matrix, dtype=float)

    def coefficients(self):
        return self._C

    def __getattr__(self, name):
        return getattr(self._base, name)


def _term_index(bundle, equation: str, term: str) -> tuple[int, int]:
    """(row, col) of a coefficient in ``bundle.model.coefficients()``.

    Identical column construction to ``coefficient_table``: names = ["1"] + STATE_NAMES
    + feature_names, mirroring the CasADi library ``vertcat(1, x_sc, u_sc)`` in
    build_mpc_controller. Raises if the term is absent from this library variant.
    """
    names = ["1"] + list(U.STATE_NAMES) + list(bundle.feature_names)
    if equation not in U.STATE_NAMES:
        raise KeyError(f"unknown equation {equation!r}")
    if term not in names:
        raise KeyError(f"term {term!r} not in feature library {bundle.feature_variant!r}")
    return U.STATE_NAMES.index(equation), names.index(term)


def _variant_bundle(bundle, edits: dict[tuple[int, int], float], label: str):
    """A SINDyBundle sharing scalers/library with ``bundle`` but with edited coefficients.

    ``edits`` maps (row, col) -> new scalar value. Uses ``dataclasses.replace`` so scalers,
    feature_variant, library_degree, period etc. are carried over unchanged (by reference);
    only the model wrapper and the metadata label differ.
    """
    C = np.array(bundle.model.coefficients(), dtype=float, copy=True)
    for (r, c), v in edits.items():
        C[r, c] = float(v)
    return dataclasses.replace(
        bundle,
        model=_CoefOverride(bundle.model, C),
        metadata={**dict(bundle.metadata), "label": label},
    )


def _coef(bundle, r: int, c: int) -> float:
    return float(np.asarray(bundle.model.coefficients())[r, c])


# ── per-seed ablation ────────────────────────────────────────────────────────

def _metrics_row(df, corridors, prices) -> dict:
    m = U.epi_metrics(df, corridors=corridors, prices=prices)
    return {
        "epi": m.get("epi", float("nan")),
        "viol": m.get("violation_steps_total", -1),
        "t_in_in_corridor_pct": m.get("t_in_in_corridor_pct", float("nan")),
        "t_in_violation_steps": m.get("t_in_violation_steps", -1),
        "boiler_sum": m.get("boiler_sum", float("nan")),
        "solver_failures": m.get("solver_failures", -1),
    }


def run_seed(seed: int, pc, recipe, TEST_START, N_TEST, train_sc, test_scen,
             CORR, PRICES) -> list[dict]:
    """All ablation conditions (main + interaction) for one seed. Paired by construction."""
    rows: list[dict] = []
    cfg_s = pc.cfg_for(test_scen, seed=seed)
    # Same excitation recipe as run_e3_seeds.py / e3_lambda_sweep.py (prbs_scale=0.3).
    train_s = U.collect_rule_based_dataset(
        pc.cfg_for(train_sc, seed=seed), n_days=pc.n_days_train, prbs_scale=0.3)

    # ---- main ablation: frozen recipe (physics_no_cross) --------------------
    b = U.fit_sindy(train_s, period=float(pc.period), metadata={"label": "baseline"}, **recipe)
    r, c = _term_index(b, "t_in", "uBoil")
    base_uboil = _coef(b, r, c)

    # Knock-in target = per-seed grey-box (dense STLSQ) gain. Same training data => the
    # StandardScalers are identical to the frozen model's (validated), so the coefficient
    # is directly transferable in scaled space. Same fit as grey_box_mpc in run_e3_seeds.py.
    b_grey = U.fit_sindy(train_s, feature_variant="physics_no_cross", library_degree=1,
                         threshold=1e-6, period=float(pc.period),
                         metadata={"label": "grey_box_mpc"})
    grey_uboil = _coef(b_grey, r, c)
    if not np.isfinite(grey_uboil) or abs(grey_uboil) < 1e-9:
        grey_uboil = GREY_UBOIL_REF

    variants = {
        "baseline": b,
        "knockout": _variant_bundle(b, {(r, c): 0.0}, "knockout"),
        "knockin": _variant_bundle(b, {(r, c): grey_uboil}, "knockin"),
    }
    for cond, vb in variants.items():
        t0 = time.time()
        df = U.rollout_mpc(vb, cfg_s, n_days=N_TEST, start_date=TEST_START)
        rec = {"family": "main", "condition": cond, "seed": seed,
               "feature_variant": "physics_no_cross",
               "xi_uboil": _coef(vb, r, c), "xi_t_uboil": float("nan"),
               "xi_uboil_baseline": base_uboil, "xi_uboil_greybox": grey_uboil,
               "secs": round(time.time() - t0, 1)}
        rec.update(_metrics_row(df, CORR, PRICES))
        rows.append(rec)
        print(f"[knockout] seed {seed} main/{cond} xi_uBoil={rec['xi_uboil']:.4f} "
              f"EPI={rec['epi']:.3f} viol={rec['viol']} ({rec['secs']}s)", flush=True)

    # ---- interaction check: full physics library (has t_uBoil cross term) ----
    # Keep the frozen recipe's optimizer/denoise; only the library is widened so the
    # temperature x boiler interaction term exists to be probed.
    b_phys = U.fit_sindy(train_s, feature_variant="physics", library_degree=1,
                         optimizer=recipe.get("optimizer", "ensemble"),
                         denoise=recipe.get("denoise", "none"),
                         period=float(pc.period), metadata={"label": "phys_baseline"})
    pr, pc_u = _term_index(b_phys, "t_in", "uBoil")
    _, pc_t = _term_index(b_phys, "t_in", "t_uBoil")
    phys_uboil, phys_t_uboil = _coef(b_phys, pr, pc_u), _coef(b_phys, pr, pc_t)

    inter = {
        # "alone" = knock out the linear boiler term only (leave the cross term)
        "phys_baseline": b_phys,
        "phys_ko_uboil_alone": _variant_bundle(b_phys, {(pr, pc_u): 0.0}, "phys_ko_uboil_alone"),
        # "together" = knock out the linear boiler term AND its t*uBoil interaction
        "phys_ko_uboil_and_cross": _variant_bundle(
            b_phys, {(pr, pc_u): 0.0, (pr, pc_t): 0.0}, "phys_ko_uboil_and_cross"),
    }
    for cond, vb in inter.items():
        t0 = time.time()
        df = U.rollout_mpc(vb, cfg_s, n_days=N_TEST, start_date=TEST_START)
        rec = {"family": "interaction", "condition": cond, "seed": seed,
               "feature_variant": "physics",
               "xi_uboil": _coef(vb, pr, pc_u), "xi_t_uboil": _coef(vb, pr, pc_t),
               "xi_uboil_baseline": phys_uboil, "xi_uboil_greybox": float("nan"),
               "secs": round(time.time() - t0, 1)}
        rec.update(_metrics_row(df, CORR, PRICES))
        rows.append(rec)
        print(f"[knockout] seed {seed} inter/{cond} xi_uBoil={rec['xi_uboil']:.4f} "
              f"xi_t_uBoil={rec['xi_t_uboil']:.4f} EPI={rec['epi']:.3f} "
              f"viol={rec['viol']} ({rec['secs']}s)", flush=True)
    return rows


# ── worker / shard / merge ───────────────────────────────────────────────────

def _out_dir(out: str | None):
    from pathlib import Path
    if out:
        d = Path(out)
        d.mkdir(parents=True, exist_ok=True)
        return d
    return U.results_dir() / "tables"


def _resolve_seeds(args) -> list[int]:
    if args.seeds:
        return [int(s) for s in args.seeds.split(",") if s.strip() != ""]
    if args.shard_index is not None and args.num_shards and args.seeds_all:
        alls = [int(s) for s in args.seeds_all.split(",") if s.strip() != ""]
        # round-robin: seeds are equal-cost, so index::num_shards balances shards evenly
        return alls[args.shard_index::args.num_shards]
    raise SystemExit("need --seeds, or --shard-index/--num-shards/--seeds-all, or --merge")


def worker(args) -> int:
    seeds = _resolve_seeds(args)
    pc = P.DEFAULT.resolved(bool(args.fast))
    recipe = P.load_frozen_recipe()
    econ = P.read_env_economics(pc.location)
    CORR, PRICES = econ["corridors"], econ["prices"]
    test_scen = pc.test_scenario()
    TEST_START = test_scen["start_date"]
    N_TEST = pc.n_days_test
    train_sc = pc.train_scenarios()[0]
    out = _out_dir(args.out) / f"e3_knockout_{args.tag}.csv"
    print(f"[knockout {args.tag}] seeds={seeds} N_TEST={N_TEST} recipe={recipe} out={out}",
          flush=True)

    records: list[dict] = []
    for s in seeds:
        try:
            records.extend(run_seed(s, pc, recipe, TEST_START, N_TEST, train_sc, test_scen,
                                    CORR, PRICES))
            # incremental flush: completed seeds survive interruption (as run_e3_seeds does)
            pd.DataFrame(records).to_csv(out, index=False)
        except Exception as exc:  # noqa: BLE001
            print(f"[knockout {args.tag}] seed {s} FAILED {type(exc).__name__}: "
                  f"{str(exc)[:160]}", flush=True)
    pd.DataFrame(records).to_csv(out, index=False)
    print(f"[knockout {args.tag}] DONE wrote {out} ({len(records)} rows)", flush=True)
    return 0


def merge(args) -> int:
    outd = _out_dir(args.out)
    parts = sorted(glob.glob(str(outd / "e3_knockout_*.csv")))
    # never re-consume the merged artifact as a partial
    parts = [p for p in parts if os.path.basename(p) != "e3_knockout_ablation.csv"]
    frames = [pd.read_csv(p) for p in parts if os.path.getsize(p) > 0]
    if not frames:
        print("no knockout partials found in", outd)
        return 1
    d = pd.concat(frames, ignore_index=True).drop_duplicates(
        ["family", "condition", "seed"], keep="last")
    merged = outd / "e3_knockout_ablation.csv"
    d.to_csv(merged, index=False)

    agg = (d.groupby(["family", "condition"])
           .agg(epi_mean=("epi", "mean"), epi_std=("epi", "std"),
                viol_mean=("viol", "mean"), xi_uboil_mean=("xi_uboil", "mean"),
                n=("epi", "size"))
           .reset_index())
    print(f"merged {len(parts)} partials -> {len(d)} rows -> {merged}")
    print(agg.round(4).to_string(index=False))

    # Paired knock-in vs knock-out effect on EPI (the headline number), if both present.
    try:
        main = d[d.family == "main"].pivot_table(index="seed", columns="condition", values="epi")
        if {"knockin", "knockout"} <= set(main.columns):
            delta = (main["knockin"] - main["knockout"]).dropna()
            print(f"\npaired dEPI (knockin - knockout): mean={delta.mean():.3f} "
                  f"std={delta.std():.3f} n={len(delta)}")
    except Exception as exc:  # noqa: BLE001
        print("paired summary skipped:", type(exc).__name__, str(exc)[:100])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", help="comma-separated seeds (explicit worker mode)")
    ap.add_argument("--shard-index", type=int, default=None,
                    help="this pod's JOB_COMPLETION_INDEX (indexed-Job shard mode)")
    ap.add_argument("--num-shards", type=int, default=None, help="total shards (= completions)")
    ap.add_argument("--seeds-all", help="full seed list to shard, e.g. 0,1,...,19")
    ap.add_argument("--tag", default="local", help="output tag (partial CSV suffix)")
    ap.add_argument("--out", default=None, help="output dir (default results_scenarios/tables)")
    ap.add_argument("--fast", type=int, default=0, help="1 = downscaled smoke run")
    ap.add_argument("--merge", action="store_true", help="aggregate shards -> e3_knockout_ablation.csv")
    args = ap.parse_args()
    if args.merge:
        return merge(args)
    return worker(args)


if __name__ == "__main__":
    raise SystemExit(main())
