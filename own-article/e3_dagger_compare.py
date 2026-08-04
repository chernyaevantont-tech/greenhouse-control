"""E3 counter-experiment: boiler term <-> controllability (dagger/dense variants).

Reproduces the sindy_mpc_{confirmatory,conf_dagger,dense,dense_dagger} rows of the
E3 headline PLUS the uBoil->t_in coefficient per variant -- the causal diagnostic
that closed-loop EPI tracks whether the control-critical boiler term survived
sparsification (methodological finding, EXPERIMENT_PROTOCOL 1.4.1 / E3 ablation).

Variants (all physics_no_cross, degree 1):
  sindy_mpc_confirmatory   ensemble (frozen recipe, threshold ~0.05) -> uBoil often ~0
  sindy_mpc_dense          stlsq / threshold 1e-3                    -> keeps the boiler
  sindy_mpc_conf_dagger    DAgger on the confirmatory (sparse) recipe
  sindy_mpc_dense_dagger   DAgger on the dense recipe

Distributed like run_e3_seeds.py: each invocation handles --seeds and writes a
partial e3_seeded_dagger_<tag>.csv; merge_e3.py folds it into the E3 main table
(dedup on method,seed). Method names are disjoint from run_e3_seeds output.

Examples
  python e3_dagger_compare.py --seeds 0 --tag s0
  python e3_dagger_compare.py --seeds 0,1,2 --tag g0
"""
from __future__ import annotations

import argparse
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

# Confirmatory (frozen, pre-registered) vs dense (boiler-preserving) recipes.
CONF = dict(feature_variant="physics_no_cross", library_degree=1, optimizer="ensemble", denoise="none")
DENSE = dict(feature_variant="physics_no_cross", library_degree=1, optimizer="stlsq", threshold=1e-3)


def uboil_coef(bundle) -> float:
    """Signed uBoil->t_in coefficient (0 == boiler dropped by sparsification)."""
    ct = U.coefficient_table(bundle)
    r = ct[(ct.equation == "t_in") & (ct.term == "uBoil")]
    return float(r.coefficient.iloc[0]) if len(r) else float("nan")


def dagger_final(initial_data, cfg_train, recipe, iterations=3, episode_days=5):
    """DAgger loop (mirrors run_dagger) with a CONFIGURABLE identification recipe;
    returns the final refined surrogate. Episodes roll the current MPC policy on the
    train scenario and aggregate, then refit under `recipe`."""
    datasets = [initial_data]
    bundle = None
    for it in range(iterations + 1):
        agg = U.aggregate_trajectories(datasets, cfg_train)
        bundle = U.fit_sindy(agg, period=float(cfg_train.period),
                             metadata={"label": f"dagger_{it}"}, **recipe)
        if it < iterations:
            roll = U.rollout_mpc(bundle, cfg_train, n_days=episode_days, objective="full")
            datasets.append(U.trajectory_from_frame(roll, cfg_train, source=f"mpc_dagger_{it}"))
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="comma-separated seeds, e.g. 0,1,2")
    ap.add_argument("--tag", required=True, help="unique output tag (partial CSV suffix)")
    ap.add_argument("--dagger-iters", type=int, default=3)
    ap.add_argument("--fast", type=int, default=0)
    a = ap.parse_args()

    try:
        import torch
        torch.set_num_threads(1)
    except Exception:
        pass

    seeds = [int(s) for s in a.seeds.split(",") if s.strip() != ""]
    pc = P.DEFAULT.resolved(bool(a.fast))
    RES = U.results_dir()
    econ = P.read_env_economics(pc.location)
    CORR, PRICES = econ["corridors"], econ["prices"]
    test_scen = pc.test_scenario()
    TEST_START = test_scen["start_date"]
    N = pc.n_days_test
    train_sc = pc.train_scenarios()[0]
    iters = 1 if a.fast else a.dagger_iters
    print(f"[{a.tag}] seeds={seeds} N_TEST={N} dagger_iters={iters} fast={a.fast}", flush=True)

    out = RES / "tables" / f"e3_seeded_dagger_{a.tag}.csv"
    rows = []

    def flush():
        pd.DataFrame(rows).to_csv(out, index=False)

    for s in seeds:
        cfg_te = pc.cfg_for(test_scen, seed=s)
        cfg_tr = pc.cfg_for(train_sc, seed=s)
        # Same identification data budget/excitation as run_e3_seeds (rule_based + PRBS 0.3).
        train = U.collect_rule_based_dataset(cfg_tr, n_days=pc.n_days_train, prbs_scale=0.3)

        variants = [
            ("sindy_mpc_confirmatory", lambda tr=train: U.fit_sindy(tr, period=float(pc.period), metadata={"label": "conf"}, **CONF)),
            ("sindy_mpc_dense",        lambda tr=train: U.fit_sindy(tr, period=float(pc.period), metadata={"label": "dense"}, **DENSE)),
            ("sindy_mpc_conf_dagger",  lambda tr=train, c=cfg_tr: dagger_final(tr, c, CONF, iters)),
            ("sindy_mpc_dense_dagger", lambda tr=train, c=cfg_tr: dagger_final(tr, c, DENSE, iters)),
        ]
        for name, fit in variants:
            t0 = time.time()
            try:
                bundle = fit()
                df = U.rollout_mpc(bundle, cfg_te, n_days=N, start_date=TEST_START)
                m = U.epi_metrics(df, corridors=CORR, prices=PRICES)
                m.update({"method": name, "seed": s, "secs": round(time.time() - t0, 1),
                          "uBoil_t_in": uboil_coef(bundle)})
                rows.append(m)
                flush()
                print(f"[{a.tag}] s{s} {name} EPI={m.get('epi', float('nan')):.3f} "
                      f"viol={m.get('violation_steps_total', -1)} uBoil={m['uBoil_t_in']:.4f} ({m['secs']}s)", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[{a.tag}] s{s} {name} FAILED {type(exc).__name__}: {str(exc)[:120]}", flush=True)

    flush()
    print(f"[{a.tag}] DONE wrote {out} ({len(rows)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
