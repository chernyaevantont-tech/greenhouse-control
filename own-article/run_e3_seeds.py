"""Distributed E3 worker: run a subset of seeds x controllers, write a partial CSV.

Each invocation handles the given --seeds and --controllers and writes
results_scenarios/tables/e3_seeded_<tag>.csv. Many invocations run concurrently
(across cores and across server0/server1); merge_e3.py combines the partials.

Examples
  python run_e3_seeds.py --seeds 0,1,2,3,4 --controllers rule_based,sindy_mpc,grey_box_mpc,nn_mpc --tag s0cheap
  python run_e3_seeds.py --seeds 0,1,2 --controllers ppo,sac --tag s0rl
  python run_e3_seeds.py --seeds 0 --controllers oracle_mpc --tag s0orc
"""
from __future__ import annotations

import argparse
import json
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

ALL_CONTROLLERS = ["rule_based", "sindy_mpc", "grey_box_mpc", "nn_mpc", "ppo", "sac", "oracle_mpc"]
_NEEDS_TRAIN = {"sindy_mpc", "grey_box_mpc", "nn_mpc"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="comma-separated seeds, e.g. 0,1,2")
    ap.add_argument("--controllers", default=",".join(ALL_CONTROLLERS))
    ap.add_argument("--tag", required=True, help="unique output tag (partial CSV suffix)")
    ap.add_argument("--fast", type=int, default=0)
    args = ap.parse_args()

    # Pin torch to 1 thread: many seed-processes run concurrently, so multi-threaded
    # torch oversubscribes the cores (this made nn_mpc ~10x slower). One thread/proc
    # lets the OS spread processes across cores cleanly.
    try:
        import torch
        torch.set_num_threads(1)
    except Exception:
        pass

    seeds = [int(s) for s in args.seeds.split(",") if s.strip() != ""]
    ctrls = [c for c in args.controllers.split(",") if c.strip() != ""]
    pc = P.DEFAULT.resolved(bool(args.fast))
    RES = U.results_dir()
    econ = P.read_env_economics(pc.location)
    CORR, PRICES = econ["corridors"], econ["prices"]

    recipe_path = RES / "recipe_frozen.json"
    if recipe_path.exists():
        recipe = json.loads(recipe_path.read_text(encoding="utf-8"))["recipe"]
    else:
        recipe = {"feature_variant": "physics", "library_degree": 1, "optimizer": "stlsq", "denoise": "savgol"}

    test_scen = pc.test_scenario()
    TEST_START = test_scen["start_date"]
    N_TEST = pc.n_days_test
    train_sc = pc.train_scenarios()[0]
    print(f"[{args.tag}] seeds={seeds} controllers={ctrls} fast={args.fast} "
          f"N_TEST={N_TEST} recipe={recipe}", flush=True)

    out = RES / "tables" / f"e3_seeded_{args.tag}.csv"
    records = []
    def _flush():
        # Write incrementally so completed (controller, seed) results survive an
        # interruption -- they are saved as soon as each controller finishes.
        pd.DataFrame(records).to_csv(out, index=False)
    for s in seeds:
        cfg_s = pc.cfg_for(test_scen, seed=s)
        train_s = None
        if any(c in _NEEDS_TRAIN for c in ctrls):
            train_s = U.collect_rule_based_dataset(
                pc.cfg_for(train_sc, seed=s), n_days=pc.n_days_train, prbs_scale=0.3)
        for c in ctrls:
            t0 = time.time()
            try:
                if c == "rule_based":
                    df = U.rollout_rule_based(cfg_s, n_days=N_TEST, start_date=TEST_START, noise_scale=0.0, seed=s)
                elif c == "sindy_mpc":
                    b = U.fit_sindy(train_s, period=float(pc.period), metadata={"label": "sindy_mpc"}, **recipe)
                    df = U.rollout_mpc(b, cfg_s, n_days=N_TEST, start_date=TEST_START)
                elif c == "grey_box_mpc":
                    b = U.fit_sindy(train_s, feature_variant="physics_no_cross", library_degree=1,
                                    threshold=1e-6, period=float(pc.period), metadata={"label": "grey_box_mpc"})
                    df = U.rollout_mpc(b, cfg_s, n_days=N_TEST, start_date=TEST_START)
                elif c == "nn_mpc":
                    nn = U.fit_nn_surrogate(train_s, feature_variant="physics", hidden_sizes=[64, 64],
                                            epochs=(60 if args.fast else 300), period=float(pc.period),
                                            metadata={"label": "nn_mpc"})
                    df = U.rollout_mpc_nn(nn, cfg_s, n_days=N_TEST, start_date=TEST_START, horizon=pc.horizon)
                elif c in ("ppo", "sac"):
                    mdl = U.train_rl(c, pc.cfg_for(train_sc, seed=s), pc.rl_train_steps,
                                     train_start_date=train_sc["start_date"], seed=s)
                    df = U.rollout_rl(mdl, cfg_s, n_days=N_TEST, start_date=TEST_START, label=c)
                elif c == "oracle_mpc":
                    # CEM cost ~ n_samples*horizon*n_iters per control step; keep the
                    # article oracle tractable (~2h/seed) with a shorter shooting horizon.
                    df = U.rollout_oracle_mpc(cfg_s, n_days=N_TEST, start_date=TEST_START,
                                              horizon=(8 if args.fast else 12),
                                              n_samples=(32 if args.fast else 48),
                                              n_iters=2)
                else:
                    print(f"[{args.tag}] unknown controller {c}", flush=True)
                    continue
                m = U.epi_metrics(df, corridors=CORR, prices=PRICES)
                m.update({"method": c, "seed": s, "secs": round(time.time() - t0, 1)})
                records.append(m)
                _flush()
                print(f"[{args.tag}] seed {s} {c} EPI={m.get('epi', float('nan')):.3f} "
                      f"viol={m.get('violation_steps_total', -1)} ({m['secs']}s)", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[{args.tag}] seed {s} {c} FAILED {type(exc).__name__}: {str(exc)[:120]}", flush=True)

    _flush()
    print(f"[{args.tag}] DONE wrote {out} ({len(records)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
