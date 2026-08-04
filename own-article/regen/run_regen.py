"""Unified runner for the article regeneration (regen-v2).

ONE driver produces EVERY number in the paper, from ONE config (`regen_config.py`), into
ONE output tree. The 2026-07 state had four runners writing four mutually inconsistent
headline tables; this replaces that.

Experiments
  main       10 controllers x 4 test years x 20 seeds  (the E3 table, multi-season)
  mechanism  lambda sweep + single-coefficient knock-out/knock-in + cross-term interaction
  parity     oracle horizon sweep + action-replay model-error decomposition

Compute is NOT reimplemented: every rollout calls the already-validated
`article_experiment_utils` API. What this driver owns is the parts that were inconsistent:
recipe (with an explicit threshold), horizon, solver budget, train years, seed set, and a
provenance stamp on every row.

Sharding: round-robin by seed, matching the existing cluster harness
(``--shard-index $JOB_COMPLETION_INDEX --num-shards N --seeds-all 0,...,19``).

Examples
  python run_regen.py --experiment main --seeds 0,1 --controllers rule_based,sindy_mpc_conf --fast
  python run_regen.py --experiment main --shard-index 0 --num-shards 20 \
      --controllers rule_based,sindy_mpc_conf,sindy_mpc_dense,sindy_mpc_lowthr,nn_mpc \
      --tag cheap --out /results
  python run_regen.py --merge --out /results
"""
from __future__ import annotations

import argparse
import dataclasses
import glob
import hashlib
import os
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import article_experiment_utils as U  # noqa: E402
import e3_dagger_compare as D  # noqa: E402
import regen_config as C  # noqa: E402
# Coefficient surgery is NOT reimplemented here: run_knockout_ablation already ships a
# validated shim (`_CoefOverride` + `_term_index` + `_variant_bundle`) that edits the
# coefficient matrix without touching pysindy internals and without deep-copying a fitted
# model. build_mpc_controller only reads `bundle.model.coefficients()`, which is exactly
# what that shim overrides. Reused verbatim so the intervention is identical to the
# 2026-07 knockout run and differences between the two are data, not implementation.
import run_knockout_ablation as K  # noqa: E402
import repro  # noqa: E402


# ── determinism (D7) ─────────────────────────────────────────────────────────
# `_make_optimizer` builds `ps.EnsembleOptimizer(base, bagging=True, n_models=20)` with NO
# random_state, so its bootstrap draws from numpy's GLOBAL RNG, which no runner ever pinned.
# Measured consequence on the confirmatory recipe, same seed, same identification dataset:
#
#     baseline state          xi(uBoil->t_in) = 0.0
#     np.random.seed(2)       xi = 0.0
#     np.random.seed(7)       xi = 0.056325
#     after 37 extra draws    xi = 0.057179
#
# i.e. whether the boiler term -- the single quantity this paper is about -- survives
# sparsification was decided by how much randomness the process happened to have consumed
# before the fit. "18 of 20 seeds drop the boiler" was therefore a property of execution
# order, not of the frozen recipe, and it explains the confirmatory controller's huge
# dispersion (+-4.33 EUR/m2 on a mean of 1.18): that spread is a mixture of
# boiler-survived and boiler-dropped draws.
#
# Fixed HERE rather than in article_experiment_utils so the shared module keeps behaving
# as the 2026-07 runs did (their numbers stay interpretable); the regen pins the global RNG
# from the run coordinates before every fit and records the value it used.

def pin_rng(*parts) -> int:
    """Seed every global RNG from the run coordinates. Returns the seed for the record.

    Delegates the actual seeding to `repro.seed_everything` so there is exactly one
    implementation of "pin all global state" (it also covers python `random`, torch CUDA
    and the deterministic-kernel flags, and pins BLAS threads -- float reduction order
    depends on the thread count, and a one-bit difference compounds over a 5760-step loop).
    """
    blob = "|".join(str(p) for p in parts).encode("utf-8")
    rs = int.from_bytes(hashlib.sha256(blob).digest()[:4], "big")
    repro.seed_everything(rs)
    return rs


def fit_sindy_seeded(data, pc, *, seed: int, label: str, recipe: dict):
    """The ONLY way this driver fits a surrogate: RNG pinned first, seed recorded in metadata.

    The recipe dict is folded into the RNG key, so two recipes on one seed get independent
    draws while a rerun of the same (seed, label, recipe) reproduces bit-for-bit.
    """
    key = ",".join(f"{k}={recipe[k]}" for k in sorted(recipe))
    rs = pin_rng(C.REGEN_ID, "fit", label, key, seed)
    b = U.fit_sindy(data, period=float(pc.period),
                    metadata={"label": label, "rng_seed": rs}, **recipe)
    return b


def _rng_of(model) -> int:
    try:
        return int(dict(model.metadata).get("rng_seed", -1))
    except Exception:
        return -1


# ── model construction (year-independent: fit once, roll on every test year) ──

def build_model(ctrl: str, pc, train_s, seed: int, fast: bool):
    """Fit/train the year-independent model for one controller. None if it needs none.

    Leakage note: every branch below sees TRAIN years only. The DAgger loop
    (`D.dagger_final`) aggregates rollouts on the TRAIN scenario, so the refined surrogate
    is year-independent and the test season enters at rollout time only.
    """
    recipe_of = {"sindy_mpc_conf": "confirmatory", "sindy_mpc_dense": "dense",
                 # `sindy_mpc_lowthr` was `grey_box_mpc`. Same estimator as `dense`, only
                 # threshold 1e-6. NOT a first-principles model -- README G-1.
                 "sindy_mpc_lowthr": "lowthr"}
    if ctrl in recipe_of:
        return fit_sindy_seeded(train_s, pc, seed=seed, label=ctrl,
                                recipe=C.load_recipe(recipe_of[ctrl]))
    if ctrl in ("sindy_mpc_conf_dagger", "sindy_mpc_dense_dagger"):
        rec = C.load_recipe("confirmatory" if ctrl == "sindy_mpc_conf_dagger" else "dense")
        cfg_tr = pc.cfg_for(pc.train_scenarios()[0], seed=seed)
        iters = 1 if fast else C.DAGGER_ITERS
        # dagger_final refits internally; pinning once makes the WHOLE loop reproducible.
        rs = pin_rng(C.REGEN_ID, "fit", ctrl, seed)
        b = D.dagger_final(train_s, cfg_tr, rec, iterations=iters,
                           episode_days=C.DAGGER_EPISODE_DAYS)
        b.metadata.setdefault("rng_seed", rs)
        return b
    if ctrl == "nn_mpc":
        pin_rng(C.REGEN_ID, "fit", ctrl, seed)     # torch weight init + batch shuffling
        return U.fit_nn_surrogate(train_s, feature_variant="physics",
                                  hidden_sizes=list(C.NN_HIDDEN),
                                  epochs=(60 if fast else C.NN_EPOCHS),
                                  period=float(pc.period), metadata={"label": ctrl})
    if ctrl in ("ppo", "sac"):
        sc = pc.train_scenarios()[0]
        pin_rng(C.REGEN_ID, "fit", ctrl, seed)     # SB3 takes `seed`, but its env/torch
        return U.train_rl(ctrl, pc.cfg_for(sc, seed=seed), pc.rl_train_steps,
                          train_start_date=sc["start_date"], seed=seed)
    if ctrl in ("rule_based", "oracle_mpc"):
        return None
    raise ValueError(f"unknown controller {ctrl}")


def rollout(ctrl: str, model, pc, year: int, seed: int, fast: bool,
            horizon: int | None = None) -> pd.DataFrame:
    """One closed-loop season. Horizon and solver budget are the SAME for everyone (D4/D5)."""
    pc_y = dataclasses.replace(pc, test_year=int(year))
    sc = C.test_scenario(pc_y, year)
    cfg = pc_y.cfg_for(sc, seed=seed)
    N, start = pc_y.n_days_test, sc["start_date"]
    h = int(horizon if horizon is not None else pc_y.horizon)

    if ctrl == "rule_based":
        # noise_scale=0: excitation belongs to identification, never to evaluation.
        return U.rollout_rule_based(cfg, n_days=N, start_date=start, noise_scale=0.0, seed=seed)
    if ctrl in ("sindy_mpc_conf", "sindy_mpc_dense", "sindy_mpc_lowthr",
                "sindy_mpc_conf_dagger", "sindy_mpc_dense_dagger"):
        return U.rollout_mpc(model, cfg, n_days=N, start_date=start, objective="full",
                             max_solver_failures=C.MAX_SOLVER_FAILURES)
    if ctrl == "nn_mpc":
        return U.rollout_mpc_nn(model, cfg, n_days=N, start_date=start, horizon=h,
                                max_solver_failures=C.MAX_SOLVER_FAILURES)
    if ctrl in ("ppo", "sac"):
        return U.rollout_rl(model, cfg, n_days=N, start_date=start, label=ctrl)
    if ctrl == "oracle_mpc":
        return U.rollout_oracle_mpc(cfg, n_days=N, start_date=start, horizon=h,
                                    n_samples=(32 if fast else C.ORACLE_CEM["n_samples"]),
                                    n_iters=C.ORACLE_CEM["n_iters"],
                                    elite_frac=C.ORACLE_CEM["elite_frac"],
                                    sample_std=C.ORACLE_CEM["sample_std"],
                                    max_solver_failures=C.MAX_SOLVER_FAILURES)
    raise ValueError(f"unknown controller {ctrl}")


def score(df: pd.DataFrame, econ, pc) -> dict:
    """EPI metrics + the truncation fields the old pipeline silently dropped.

    A truncated season is NOT comparable: an aborted run forgoes both revenue and cost, so
    its EPI is on a shorter horizon than everyone else's. Recorded here, gated in
    verify_regen.py.
    """
    m = U.epi_metrics(df, corridors=econ["corridors"], prices=econ["prices"])
    expected = int(pc.n_days_test * 86400 // pc.period)
    steps = int(m.get("steps", len(df)))
    m["steps_expected"] = expected
    m["season_fraction"] = round(steps / expected, 4) if expected else float("nan")
    m["truncated"] = bool(steps < expected)
    return m


def _uboil(model) -> float:
    """Signed uBoil->t_in coefficient, or NaN for non-SINDy controllers."""
    try:
        return float(D.uboil_coef(model))
    except Exception:
        return float("nan")


# ── experiments ──────────────────────────────────────────────────────────────

def exp_main(args, seeds, pc, econ, out: Path) -> int:
    ctrls = _split(args.controllers) or C.ALL_CONTROLLERS
    years = [int(y) for y in _split(args.test_years)] or list(C.TEST_YEARS)
    rows, path = [], out / f"main_{args.tag}.csv"
    for s in seeds:
        train_s = None
        if any(c in C.NEEDS_TRAIN for c in ctrls):
            train_s = C.build_train_dataset(pc, seed=s, fast=args.fast)
        for c in ctrls:
            try:
                model = build_model(c, pc, train_s, s, args.fast)
            except Exception as exc:  # noqa: BLE001
                _log(f"seed {s} {c} BUILD-FAILED {type(exc).__name__}: {str(exc)[:160]}")
                continue
            xi = _uboil(model)
            for y in years:
                t0 = time.time()
                try:
                    df = rollout(c, model, pc, y, s, args.fast)
                    m = score(df, econ, pc)
                    m.update({"method": c, "seed": s, "test_year": y,
                              "xi_uboil": xi, "rng_seed": _rng_of(model),
                              "horizon": pc.horizon,
                              "max_solver_failures": C.MAX_SOLVER_FAILURES,
                              "secs": round(time.time() - t0, 1), **C.stamp()})
                    rows.append(m)
                    _write(rows, path)
                    _log(f"seed {s} {c} y{y} EPI={m.get('epi', float('nan')):.3f} "
                         f"viol={m.get('violation_steps_total', -1)} "
                         f"frac={m['season_fraction']} ({m['secs']}s)")
                except Exception as exc:  # noqa: BLE001
                    _log(f"seed {s} {c} y{y} FAILED {type(exc).__name__}: {str(exc)[:160]}")
    _write(rows, path)
    return 0


def exp_mechanism(args, seeds, pc, econ, out: Path) -> int:
    """Why the confirmatory surrogate fails, with the confounds removed.

    Three blocks, all on the in-distribution year:
      lambda      threshold sweep -- now WITH per-point dispersion and violations, and
                  extended past the point where the boiler coefficient hits exactly zero
                  (the old grid stopped there, and its last point contradicted the claim).
      knock       change ONE coefficient (uBoil->t_in) and nothing else: knock-out from a
                  model that has it, knock-in from a model that lacks it. This, not the
                  lambda sweep, is what licenses a causal claim.
      cross       the same on the `physics` library, separating uBoil from the bilinear
                  t_in*uBoil term, which the 2026-07 run showed carries part of the effect.
    """
    rows, path = [], out / f"mechanism_{args.tag}.csv"
    year = C.IN_DIST_YEAR
    blocks = _split(args.blocks) or ["lambda", "knock", "cross"]

    for s in seeds:
        train_s = C.build_train_dataset(pc, seed=s, fast=args.fast)

        if "lambda" in blocks:
            base = dict(C.load_recipe("lowthr"))
            for lam in (C.LAMBDA_GRID[:3] if args.fast else C.LAMBDA_GRID):
                rec = {**base, "optimizer": "stlsq", "threshold": float(lam)}
                try:
                    b = fit_sindy_seeded(train_s, pc, seed=s, label=f"lam{lam:g}", recipe=rec)
                    df = rollout("sindy_mpc_dense", b, pc, year, s, args.fast)
                    m = score(df, econ, pc)
                    m.update({"block": "lambda", "condition": f"lam={lam:g}", "lam": float(lam),
                              "seed": s, "test_year": year, "xi_uboil": _uboil(b),
                              "rng_seed": _rng_of(b),
                              "nonzero": int(np.count_nonzero(b.model.coefficients())),
                              "rollout_rmse": _rollout_rmse(b, train_s), **C.stamp()})
                    rows.append(m); _write(rows, path)
                    _log(f"seed {s} lambda={lam:g} EPI={m.get('epi', float('nan')):.3f} "
                         f"xi={m['xi_uboil']:.5f}")
                except Exception as exc:  # noqa: BLE001
                    _log(f"seed {s} lambda={lam:g} FAILED {type(exc).__name__}: {str(exc)[:140]}")

        if "knock" in blocks:
            try:
                # NOTE the RNG pin: without it the confirmatory fit's boiler term is decided
                # by ambient global-RNG state, so `baseline` here and the `sindy_mpc_conf`
                # row of the main table would silently be different models (D7).
                conf = fit_sindy_seeded(train_s, pc, seed=s, label="sindy_mpc_conf",
                                        recipe=C.load_recipe("confirmatory"))
                donor = fit_sindy_seeded(train_s, pc, seed=s, label="sindy_mpc_lowthr",
                                         recipe=C.load_recipe("lowthr"))
                donor_xi = _uboil(donor)
                for cond, val in (("baseline", None), ("knockout", 0.0), ("knockin", donor_xi)):
                    b = conf if val is None else _with_uboil(conf, val, label=cond)
                    df = rollout("sindy_mpc_conf", b, pc, year, s, args.fast)
                    m = score(df, econ, pc)
                    m.update({"block": "knock", "condition": cond, "seed": s,
                              "test_year": year, "xi_uboil": _uboil(b),
                              "rng_seed": _rng_of(conf),
                              "xi_donor": donor_xi, **C.stamp()})
                    rows.append(m); _write(rows, path)
                    _log(f"seed {s} knock/{cond} EPI={m.get('epi', float('nan')):.3f}")
            except Exception as exc:  # noqa: BLE001
                _log(f"seed {s} knock FAILED {type(exc).__name__}: {str(exc)[:140]}")

        if "cross" in blocks:
            try:
                b0 = fit_sindy_seeded(train_s, pc, seed=s, label="cross",
                                      recipe=C.load_recipe("cross"))
                for cond in ("baseline", "ko_uboil", "ko_cross", "ko_both"):
                    b = b0 if cond == "baseline" else _with_uboil(
                        b0,
                        0.0 if cond in ("ko_uboil", "ko_both") else None,
                        cross=0.0 if cond in ("ko_cross", "ko_both") else None,
                        label=cond)
                    df = rollout("sindy_mpc_conf", b, pc, year, s, args.fast)
                    m = score(df, econ, pc)
                    m.update({"block": "cross", "condition": cond, "seed": s,
                              "test_year": year, "xi_uboil": _uboil(b), **C.stamp()})
                    rows.append(m); _write(rows, path)
                    _log(f"seed {s} cross/{cond} EPI={m.get('epi', float('nan')):.3f}")
            except Exception as exc:  # noqa: BLE001
                _log(f"seed {s} cross FAILED {type(exc).__name__}: {str(exc)[:140]}")

    _write(rows, path)
    return 0


def exp_parity(args, seeds, pc, econ, out: Path) -> int:
    """Is the oracle's shortfall model error, optimiser error, or horizon?

    horizon  the SAME oracle at several horizons, so "short-horizon greed" is measured.
    replay   one-step vs free-run surrogate error on the oracle's own action sequence,
             which separates model error from optimiser error (reviewer item #6).
    """
    rows, path = [], out / f"parity_{args.tag}.csv"
    year = C.IN_DIST_YEAR
    blocks = _split(args.blocks) or ["horizon", "replay"]

    for s in seeds:
        # The horizon sweep is a sensitivity analysis and costs ~18 h/seed at full scale
        # (see ORACLE_SWEEP_SEEDS), so it runs on a subset. Parity at h=20 is still covered
        # on every seed by the main table's oracle rows.
        if "horizon" in blocks and (args.fast or s in C.ORACLE_SWEEP_SEEDS):
            hs = (C.ORACLE_HORIZON_SWEEP[:2] if args.fast else C.ORACLE_HORIZON_SWEEP)
            for h in hs:
                t0 = time.time()
                try:
                    df = rollout("oracle_mpc", None, pc, year, s, args.fast, horizon=h)
                    m = score(df, econ, pc)
                    m.update({"block": "horizon", "condition": f"h={h}", "oracle_horizon": int(h),
                              "seed": s, "test_year": year,
                              "secs": round(time.time() - t0, 1), **C.stamp()})
                    rows.append(m); _write(rows, path)
                    _log(f"seed {s} oracle h={h} EPI={m.get('epi', float('nan')):.3f} "
                         f"frac={m['season_fraction']}")
                except Exception as exc:  # noqa: BLE001
                    _log(f"seed {s} oracle h={h} FAILED {type(exc).__name__}: {str(exc)[:140]}")

        if "replay" in blocks:
            # Action replay proper: evaluate the surrogate along the trajectory the ORACLE
            # actually visited, not along a rule-based one. That is what separates model
            # error (the surrogate mispredicts the states the oracle drives the plant
            # through) from optimiser error (the oracle's own CEM search is weak). Reported
            # for both surrogates so "the confirmatory model is too inaccurate" can be
            # accepted or rejected on evidence.
            try:
                train_s = C.build_train_dataset(pc, seed=s, fast=args.fast)
                sc = C.test_scenario(pc, year)
                cfg = pc.cfg_for(sc, seed=s)
                orc = rollout("oracle_mpc", None, pc, year, s, args.fast, horizon=C.HORIZON)
                traj = U.trajectory_from_frame(orc, cfg, source="oracle")
                for rec_name, label in (("confirmatory", "sindy_mpc_conf"),
                                        ("lowthr", "sindy_mpc_lowthr")):
                    b = fit_sindy_seeded(train_s, pc, seed=s, label=label,
                                         recipe=C.load_recipe(rec_name))
                    ev = U.evaluate_sindy(b, traj)
                    for _, r in ev.iterrows():
                        m = dict(r)
                        m.update({"block": "replay", "condition": f"replay_{rec_name}",
                                  "recipe": rec_name, "seed": s, "test_year": year,
                                  "xi_uboil": _uboil(b), "rng_seed": _rng_of(b),
                                  "traj_steps": int(len(orc)), **C.stamp()})
                        rows.append(m)
                _write(rows, path)
                _log(f"seed {s} replay ok over {len(orc)} oracle steps")
            except Exception as exc:  # noqa: BLE001
                _log(f"seed {s} replay FAILED {type(exc).__name__}: {str(exc)[:140]}")

    _write(rows, path)
    return 0


# ── coefficient surgery ──────────────────────────────────────────────────────

CROSS_TERM = "t_uBoil"   # the library's name for the t_in x uBoil bilinear term


def _with_uboil(bundle, uboil: float | None, cross: float | None = None, label: str = "edit"):
    """`bundle` with ONLY the uBoil->t_in (and optionally t_uBoil->t_in) coefficient set.

    Everything else -- library, scalers, other terms, MPC construction -- is untouched. That
    single-factor property is what licenses a causal reading, and is exactly what the lambda
    sweep lacks (there the surviving-term count moves 54 -> 20 at the same time).

    Passing None leaves a term alone, so ko_uboil / ko_cross / ko_both are all expressible.
    """
    edits: dict[tuple[int, int], float] = {}
    for term, val in (("uBoil", uboil), (CROSS_TERM, cross)):
        if val is None:
            continue
        edits[K._term_index(bundle, "t_in", term)] = float(val)   # raises if term absent
    if not edits:
        return bundle
    return K._variant_bundle(bundle, edits, label)


def _rollout_rmse(bundle, data, horizon: int = 96) -> float:
    """Open-loop multi-step rollout RMSE on t_in -- the criterion pre-registration froze on.

    `evaluate_sindy` emits one row per (metric_scope, horizon, state); the pre-registration
    used the multi-step rollout, not the one-step fit, so filter on metric_scope='rollout'.
    Falls back to the longest available horizon if the requested one was not evaluated.
    """
    try:
        ev = U.evaluate_sindy(bundle, data)
        r = ev[(ev.metric_scope == "rollout") & (ev.state == "t_in")]
        if not len(r):
            return float("nan")
        exact = r[r.horizon == horizon]
        row = exact.iloc[0] if len(exact) else r.sort_values("horizon").iloc[-1]
        return float(row.rmse)
    except Exception:
        return float("nan")


# ── merge ────────────────────────────────────────────────────────────────────

def merge(out: Path) -> int:
    """Build EVERY derived table from the merged raw files, so there is one lineage."""
    n = 0
    for kind, keys in (("main", ["method", "seed", "test_year"]),
                       ("mechanism", ["block", "condition", "seed", "test_year"]),
                       ("parity", ["block", "condition", "seed", "test_year"]),
                       ("ladder", ["condition", "seed"]),
                       ("adapt", ["block", "condition", "seed", "test_year"]),
                       ("guard", ["block", "condition", "seed", "test_year"]),
                       ("faults", ["block", "condition", "seed", "test_year"]),
                       ("design", ["block", "condition", "seed", "test_year"])):
        parts = [p for p in sorted(glob.glob(str(out / f"{kind}_*.csv")))
                 if os.path.basename(p) != f"{kind}.csv" and os.path.getsize(p) > 0]
        if not parts:
            _log(f"no {kind} partials in {out}")
            continue
        d = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
        keys = [k for k in keys if k in d.columns]
        d = d.drop_duplicates(keys, keep="last")
        d.to_csv(out / f"{kind}.csv", index=False)
        _log(f"{kind}: {len(parts)} partials -> {len(d)} rows")
        n += 1

    mainp = out / "main.csv"
    if mainp.exists():
        d = pd.read_csv(mainp)
        # A truncated season is dropped, not averaged in: an aborted run forgoes both
        # revenue and cost, so its EPI is measured over a shorter horizon than the rest.
        valid = d[~d["truncated"].astype(bool)] if "truncated" in d.columns else d
        by_year = (valid.groupby(["test_year", "method"])
                   .agg(epi_mean=("epi", "mean"), epi_std=("epi", "std"),
                        epi_median=("epi", "median"),
                        viol_mean=("violation_steps_total", "mean"),
                        n=("epi", "size"))
                   .reset_index()
                   .sort_values(["test_year", "epi_mean"], ascending=[True, False]))
        by_year.to_csv(out / "table_main_by_year.csv", index=False)
        pooled = (by_year.groupby("method")
                  .agg(epi_mean_over_years=("epi_mean", "mean"),
                       worst_year=("epi_mean", "min"), years=("epi_mean", "size"))
                  .reset_index().sort_values("epi_mean_over_years", ascending=False))
        pooled.to_csv(out / "table_main_pooled.csv", index=False)
        _log(f"tables: {len(by_year)} (year,method) rows; "
             f"dropped {len(d) - len(valid)} truncated runs")
    return 0 if n else 1


# ── plumbing ─────────────────────────────────────────────────────────────────

def _split(s: str | None) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _log(msg: str) -> None:
    print(f"[regen] {msg}", flush=True)


def _write(rows: list[dict], path: Path) -> None:
    if rows:
        pd.DataFrame(rows).to_csv(path, index=False)


def _seeds(args) -> list[int]:
    if args.seeds:
        return [int(s) for s in _split(args.seeds)]
    if args.shard_index is not None and args.num_shards:
        alls = [int(s) for s in _split(args.seeds_all)] or list(C.SEEDS)
        return alls[args.shard_index::args.num_shards]
    raise SystemExit("need --seeds, or --shard-index/--num-shards, or --merge")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default="main", choices=[
        "main",         # E3  10 controllers x 4 seasons x 20 seeds -- the headline table
        "mechanism",    # E3b lambda sweep + single-coefficient knock-out/in + cross block
        "parity",       # oracle horizon sweep + optimiser budget + action replay
        "ladder",       # E2  identification-configuration sweep (the pre-registration)
        "adapt",        # E4  static vs aggregation vs EKF under season shift
        "guard",        # E5  shift detection + OOD guard
        "faults",       # E7  six fault modes x supervisor
        "design",       # E6  horizon / threshold / coefficient perturbation
    ])
    ap.add_argument("--blocks", default="", help="mechanism/parity sub-blocks (default: all)")
    ap.add_argument("--seeds")
    ap.add_argument("--shard-index", type=int, default=None)
    ap.add_argument("--num-shards", type=int, default=None)
    ap.add_argument("--seeds-all", default=",".join(str(s) for s in C.SEEDS))
    ap.add_argument("--controllers", default="")
    ap.add_argument("--test-years", default="")
    ap.add_argument("--tag", default="local")
    ap.add_argument("--out", default="")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--fast", action="store_true", help="minutes-long smoke, NOT publishable")
    args = ap.parse_args()

    out = Path(args.out) if args.out else (HERE / "results")
    out.mkdir(parents=True, exist_ok=True)

    if args.merge:
        return merge(out)

    try:
        import torch
        torch.set_num_threads(1)
    except Exception:
        pass

    pc = C.protocol(args.fast)
    econ = P_read_econ()
    seeds = _seeds(args)
    C.write_manifest(out)
    _log(f"{args.experiment} tag={args.tag} seeds={seeds} fast={args.fast} "
         f"cfg={C.config_hash()} git={C.git_sha()} out={out}")

    import experiments_support as X
    fn = {"main": exp_main, "mechanism": exp_mechanism, "parity": exp_parity,
          "ladder": X.exp_ladder, "adapt": X.exp_adapt, "guard": X.exp_guard,
          "faults": X.exp_faults, "design": X.exp_design}[args.experiment]
    rc = fn(args, seeds, pc, econ, out)
    _log(f"{args.experiment} tag={args.tag} DONE")
    return rc


def P_read_econ():
    import protocol_config as P
    return P.read_env_economics(C.LOCATION)


if __name__ == "__main__":
    raise SystemExit(main())
