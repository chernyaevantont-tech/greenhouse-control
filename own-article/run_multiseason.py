"""E3 multi-season main comparison (reviewer item #3).

Same closed-loop benchmark as run_e3_seeds.py, but evaluated across SEVERAL test
seasons instead of the single 2020 in-distribution year -- so the EPI ranking is shown
to hold out-of-distribution (2021/2022/2023), not just on one held-out year.

Reuses the run_e3_seeds.py controller dispatch and the article_experiment_utils API
verbatim; the only additions are (1) a test-year loop and (2) index-based sharding for
the Kubernetes indexed Job. Training/identification is leakage-free and year-independent
(TRAIN = 2018/2019 always), so each surrogate/RL model is fit/trained ONCE per
(seed, controller) and then rolled out on every test year -- the expensive step (nn/RL
training, ensemble fit) is not repeated per season.

Beyond run_e3_seeds' 7 controllers this runner also covers the three remaining SINDy-UPM
variants of the single-season E3 table (reviewer item #3 completeness), reusing the
e3_dagger_compare recipes/DAgger loop verbatim:
  sindy_mpc_dense         boiler-preserving stlsq/1e-3 recipe (rolled like sindy_mpc)
  sindy_mpc_conf_dagger   DAgger refinement of the frozen/confirmatory recipe
  sindy_mpc_dense_dagger  DAgger refinement of the dense recipe
The DAgger loop trains only on the TRAIN scenario (expert = rule-based on 2018/2019), so
these too are YEAR-INDEPENDENT: fit ONCE per seed, then rolled on every test year.

Sharding: round-robin by seed (``--shard-index i --num-shards M --seeds-all ...`` -> this
pod owns ``seeds_all[i::M]``). One shard runs all requested controllers x all test years
for its seeds. Split cheap vs expensive controllers into separate Job submissions via
``--controllers`` (as server0/server1 did) to keep pod wallclock balanced.

Examples
  python run_multiseason.py --seeds 0,1 --controllers rule_based,sindy_mpc,grey_box_mpc \
      --test-years 2020,2021,2022,2023 --tag s01cheap
  python run_multiseason.py --shard-index 0 --num-shards 20 --seeds-all 0,1,2,3,4,5,6,7,8,9 \
      --controllers ppo,sac --test-years 2020,2021,2022,2023 --tag shard0rl --out /results
  python run_multiseason.py --merge --out /results
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
import numpy as np  # noqa: E402,F401
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402
import protocol_config as P  # noqa: E402
# Single source of truth for the SINDy-UPM counter-experiment recipes/DAgger loop:
# reuse e3_dagger_compare's CONF/DENSE recipe dicts + dagger_final verbatim so the
# multiseason in-distribution (2020) rows reproduce the single-season E3 table exactly.
import e3_dagger_compare as D  # noqa: E402

ALL_CONTROLLERS = ["rule_based", "sindy_mpc", "sindy_mpc_dense", "grey_box_mpc", "nn_mpc",
                   "ppo", "sac", "oracle_mpc", "sindy_mpc_conf_dagger", "sindy_mpc_dense_dagger"]
# Controllers that consume the rule-based+PRBS identification dataset (train_s).
# The DAgger variants also need it as the DAgger seed dataset.
_NEEDS_TRAIN = {"sindy_mpc", "sindy_mpc_dense", "grey_box_mpc", "nn_mpc",
                "sindy_mpc_conf_dagger", "sindy_mpc_dense_dagger"}


def _build_model(c: str, pc, train_sc, train_s, recipe, fast: bool, seed: int):
    """Fit/train the (year-independent) model for a controller once. Returns an opaque
    handle consumed by _rollout_on_year (None for controllers that need no model)."""
    if c == "sindy_mpc":
        return U.fit_sindy(train_s, period=float(pc.period), metadata={"label": "sindy_mpc"}, **recipe)
    if c == "sindy_mpc_dense":
        # Boiler-preserving "dense" recipe (stlsq + low threshold 1e-3): keeps the
        # small-magnitude but control-critical uBoil->t_in term the frozen recipe drops.
        return U.fit_sindy(train_s, period=float(pc.period), metadata={"label": "sindy_mpc_dense"}, **D.DENSE)
    if c in ("sindy_mpc_conf_dagger", "sindy_mpc_dense_dagger"):
        # DAgger dual-loop refinement. dagger_final runs ENTIRELY on the TRAIN scenario
        # (aggregate -> fit -> roll rule-based-expert episodes -> refit); the test year
        # only enters at rollout time. So the refined surrogate is YEAR-INDEPENDENT and is
        # fit ONCE per (seed) here, then rolled on every test year (fit-once-roll-many).
        # conf_dagger uses the frozen/confirmatory recipe (== D.CONF); dense_dagger uses D.DENSE.
        cfg_tr = pc.cfg_for(train_sc, seed=seed)
        rec = recipe if c == "sindy_mpc_conf_dagger" else D.DENSE
        iters = 1 if fast else 3  # mirrors e3_dagger_compare's default (fast -> 1 iteration)
        return D.dagger_final(train_s, cfg_tr, rec, iterations=iters)
    if c == "grey_box_mpc":
        return U.fit_sindy(train_s, feature_variant="physics_no_cross", library_degree=1,
                           threshold=1e-6, period=float(pc.period), metadata={"label": "grey_box_mpc"})
    if c == "nn_mpc":
        return U.fit_nn_surrogate(train_s, feature_variant="physics", hidden_sizes=[64, 64],
                                  epochs=(60 if fast else 300), period=float(pc.period),
                                  metadata={"label": "nn_mpc"})
    if c in ("ppo", "sac"):
        return U.train_rl(c, pc.cfg_for(train_sc, seed=seed), pc.rl_train_steps,
                          train_start_date=train_sc["start_date"], seed=seed)
    return None  # rule_based / oracle_mpc need no pre-built model


def _rollout_on_year(c: str, model, pc, year: int, seed: int, fast: bool):
    """Roll a controller out on one test season. cfg is rebuilt for the given test year."""
    pc_y = dataclasses.replace(pc, test_year=int(year))
    test_scen = pc_y.test_scenario()
    cfg_sy = pc_y.cfg_for(test_scen, seed=seed)
    start = test_scen["start_date"]
    N = pc_y.n_days_test
    if c == "rule_based":
        return U.rollout_rule_based(cfg_sy, n_days=N, start_date=start, noise_scale=0.0, seed=seed)
    if c in ("sindy_mpc", "grey_box_mpc", "sindy_mpc_dense",
             "sindy_mpc_conf_dagger", "sindy_mpc_dense_dagger"):
        # All are SINDyBundles (dense/dagger included) -> identical closed-loop MPC rollout.
        return U.rollout_mpc(model, cfg_sy, n_days=N, start_date=start)
    if c == "nn_mpc":
        return U.rollout_mpc_nn(model, cfg_sy, n_days=N, start_date=start, horizon=pc_y.horizon)
    if c in ("ppo", "sac"):
        return U.rollout_rl(model, cfg_sy, n_days=N, start_date=start, label=c)
    if c == "oracle_mpc":
        return U.rollout_oracle_mpc(cfg_sy, n_days=N, start_date=start,
                                    horizon=(8 if fast else 12),
                                    n_samples=(32 if fast else 48), n_iters=2)
    raise ValueError(f"unknown controller {c}")


def worker(args) -> int:
    seeds = _resolve_seeds(args)
    ctrls = [c for c in args.controllers.split(",") if c.strip() != ""]
    years = [int(y) for y in args.test_years.split(",") if y.strip() != ""]
    fast = bool(args.fast)
    try:  # 1 thread/proc: many seed-pods share a node; avoids torch oversubscription
        import torch
        torch.set_num_threads(1)
    except Exception:
        pass

    pc = P.DEFAULT.resolved(fast)
    recipe = P.load_frozen_recipe()
    econ = P.read_env_economics(pc.location)
    CORR, PRICES = econ["corridors"], econ["prices"]
    train_sc = pc.train_scenarios()[0]
    out = _out_dir(args.out) / f"e3_multiseason_{args.tag}.csv"
    print(f"[multiseason {args.tag}] seeds={seeds} controllers={ctrls} years={years} "
          f"fast={fast} recipe={recipe} out={out}", flush=True)

    records: list[dict] = []

    def _flush():
        pd.DataFrame(records).to_csv(out, index=False)

    for s in seeds:
        train_s = None
        if any(c in _NEEDS_TRAIN for c in ctrls):
            train_s = U.collect_rule_based_dataset(
                pc.cfg_for(train_sc, seed=s), n_days=pc.n_days_train, prbs_scale=0.3)
        for c in ctrls:
            try:
                model = _build_model(c, pc, train_sc, train_s, recipe, fast, s)  # fit ONCE
            except Exception as exc:  # noqa: BLE001
                print(f"[multiseason {args.tag}] seed {s} {c} BUILD-FAILED "
                      f"{type(exc).__name__}: {str(exc)[:140]}", flush=True)
                continue
            for y in years:
                t0 = time.time()
                try:
                    df = _rollout_on_year(c, model, pc, y, s, fast)
                    m = U.epi_metrics(df, corridors=CORR, prices=PRICES)
                    m.update({"method": c, "seed": s, "test_year": y,
                              "secs": round(time.time() - t0, 1)})
                    records.append(m)
                    _flush()
                    print(f"[multiseason {args.tag}] seed {s} {c} y{y} "
                          f"EPI={m.get('epi', float('nan')):.3f} "
                          f"viol={m.get('violation_steps_total', -1)} ({m['secs']}s)", flush=True)
                except Exception as exc:  # noqa: BLE001
                    print(f"[multiseason {args.tag}] seed {s} {c} y{y} FAILED "
                          f"{type(exc).__name__}: {str(exc)[:140]}", flush=True)
    _flush()
    print(f"[multiseason {args.tag}] DONE wrote {out} ({len(records)} rows)", flush=True)
    return 0


def merge(args) -> int:
    outd = _out_dir(args.out)
    parts = sorted(glob.glob(str(outd / "e3_multiseason_*.csv")))
    parts = [p for p in parts if os.path.basename(p) not in
             ("e3_multiseason.csv", "e3_multiseason_table.csv")]
    frames = [pd.read_csv(p) for p in parts if os.path.getsize(p) > 0]
    if not frames:
        print("no multiseason partials found in", outd)
        return 1
    d = pd.concat(frames, ignore_index=True).drop_duplicates(
        ["method", "seed", "test_year"], keep="last")
    d.to_csv(outd / "e3_multiseason.csv", index=False)
    agg = (d.groupby(["test_year", "method"])
           .agg(epi_mean=("epi", "mean"), epi_std=("epi", "std"),
                viol_mean=("violation_steps_total", "mean"), n=("epi", "size"))
           .reset_index().sort_values(["test_year", "epi_mean"], ascending=[True, False]))
    agg.to_csv(outd / "e3_multiseason_table.csv", index=False)
    print(f"merged {len(parts)} partials -> {len(d)} rows, "
          f"{d.method.nunique()} methods x {d.test_year.nunique()} years")
    print(agg.round(3).to_string(index=False))
    return 0


# ── shard / io helpers (shared shape with run_knockout_ablation.py) ──────────

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
        return alls[args.shard_index::args.num_shards]
    raise SystemExit("need --seeds, or --shard-index/--num-shards/--seeds-all, or --merge")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", help="comma-separated seeds (explicit worker mode)")
    ap.add_argument("--shard-index", type=int, default=None, help="JOB_COMPLETION_INDEX")
    ap.add_argument("--num-shards", type=int, default=None, help="total shards (= completions)")
    ap.add_argument("--seeds-all", help="full seed list to shard, e.g. 0,1,...,19")
    ap.add_argument("--controllers", default=",".join(ALL_CONTROLLERS))
    ap.add_argument("--test-years", default="2020,2021,2022,2023")
    ap.add_argument("--tag", default="local")
    ap.add_argument("--out", default=None, help="output dir (default results_scenarios/tables)")
    ap.add_argument("--fast", type=int, default=0)
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    if args.merge:
        return merge(args)
    return worker(args)


if __name__ == "__main__":
    raise SystemExit(main())
