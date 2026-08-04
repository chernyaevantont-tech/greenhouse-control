"""E3 oracle solver-parity + action-replay (reviewer item #6).

The article's oracle uses a CEM shooting search over the true simulator, while the
surrogate MPC uses IPOPT/do-mpc. That confounds TWO differences when comparing them:
the MODEL (true 28-state GreenLight vs the 3-state SINDy surrogate) and the OPTIMIZER
(CEM vs IPOPT). This runner decomposes that gap:

  mode = action_replay  (IMPLEMENTED, runnable)
      Apply ONE fixed action sequence (the rule-based deployment policy on the test
      season) to BOTH the true model and the surrogate, open-loop. The surrogate's
      divergence from the true trajectory under identical inputs is pure MODEL error
      (no optimizer involved). Reported per state as one-step and free-running RMSE.

  mode = solver_parity  (SCAFFOLD, see TODO)
      Re-run the oracle with the SAME IPOPT/do-mpc solver as the surrogate MPC (not CEM),
      over the TRUE model. Holding the optimizer fixed isolates the optimizer's share of
      the gap. Requires embedding the true CasADi dynamics env.unwrapped.F into a do-mpc
      model -- the one piece that must be wired by hand (marked TODO below).

Together: (model error from action_replay) + (optimizer error from solver_parity vs CEM)
should account for the oracle-vs-surrogate EPI gap.

Distributed/sharded exactly like run_knockout_ablation.py.

Examples
  python run_oracle_parity.py --mode action_replay --seeds 0,1 --tag s01
  python run_oracle_parity.py --mode action_replay --shard-index 0 --num-shards 20 \
      --seeds-all 0,1,2,3,4,5,6,7,8,9 --tag shard0 --out /results
  python run_oracle_parity.py --merge --out /results
"""
from __future__ import annotations

import argparse
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


# ── mode A: action replay (model error under a fixed action sequence) ────────

def action_replay_seed(seed: int, pc, recipe, train_sc, test_scen, CORR, PRICES) -> list[dict]:
    """Fit the frozen surrogate, then replay the rule-based action sequence through both
    the true simulator (via collect_rule_based_dataset, which steps env.step) and the
    surrogate (open-loop predict_next_raw). RMSE(true, surrogate) = model error."""
    TEST_START = test_scen["start_date"]
    N = pc.n_days_test
    train_s = U.collect_rule_based_dataset(
        pc.cfg_for(train_sc, seed=seed), n_days=pc.n_days_train, prbs_scale=0.3)
    b = U.fit_sindy(train_s, period=float(pc.period), metadata={"label": "sindy_mpc"}, **recipe)

    # The single fixed action sequence + the TRUE trajectory it produces on the test season.
    cfg_te = pc.cfg_for(test_scen, seed=seed)
    true = U.collect_rule_based_dataset(cfg_te, n_days=N, start_date=TEST_START, prbs_scale=0.0)
    X = np.asarray(true.states, dtype=float)        # (n, 3) TRUE states
    W = np.asarray(true.weather, dtype=float)
    TE = np.asarray(true.time_enc, dtype=float)
    A = np.asarray(true.actions, dtype=float)
    n = len(X)

    # one-step (teacher-forced): xhat_{k+1} = f_surrogate(x_true_k, u_k)
    onestep = np.array([U.predict_next_raw(b, X[k], W[k], TE[k], A[k]) for k in range(n - 1)])
    # free-running: surrogate integrates its OWN state forward under the same actions/weather
    free = np.zeros((n, 3)); free[0] = X[0]
    for k in range(n - 1):
        free[k + 1] = U.predict_next_raw(b, free[k], W[k], TE[k], A[k])

    rows = []
    for i, st in enumerate(U.STATE_NAMES):
        rmse_1 = float(np.sqrt(np.mean((onestep[:, i] - X[1:, i]) ** 2)))
        rmse_free = float(np.sqrt(np.mean((free[1:, i] - X[1:, i]) ** 2)))
        rows.append({"mode": "action_replay", "seed": seed, "state": st,
                     "rmse_onestep_model": rmse_1, "rmse_freerun_model": rmse_free,
                     "true_std": float(np.std(X[:, i])), "n_steps": n})
    print(f"[parity] seed {seed} action_replay model-RMSE(free) "
          + " ".join(f"{r['state']}={r['rmse_freerun_model']:.3f}" for r in rows), flush=True)
    return rows


# ── mode B: solver parity (true-model IPOPT oracle) — SCAFFOLD ───────────────

def build_true_model_mpc(cfg, weather_provider):
    """TODO(reviewer #6): build a do-mpc/IPOPT controller over the TRUE GreenLight model
    so the oracle uses the SAME solver as the surrogate MPC (build_mpc_controller), not CEM.

    Wiring required (mirror build_mpc_controller, but over the true dynamics):
      1. States: the full true state x in R^{nx} (nx = env.unwrapped.nx == 28), NOT the
         3-state SINDy reduction. do_mpc.model.Model("discrete"); set_variable per state.
      2. Dynamics: the true one-step map is the CasADi Function ``env.unwrapped.F``
         (x_{k+1} = F(x0=x, u=u, p=[weather_k, params])["xf"]). Embed it symbolically:
             x_next = F(x0=x_sym, u=u_sym, p=ca.vertcat(tvp_weather, ca.DM(params)))["xf"]
             for i in range(nx): model.set_rhs(state_i, x_next[i])
         F is already CasADi and differentiable, so IPOPT can use it directly.
      3. TVP: the time-varying part of p is the per-step weather row
         env.unwrapped.weather_data[step]; wire it through a WeatherForecastTVP-like
         provider that returns the true-model weather+params slice per horizon step.
      4. Objective: the SAME economic cost rollout_oracle_mpc maximizes, expressed on the
         true state: revenue = (x[25]_{k+1} - x[25]_k) * c_rev; costs = uBoil*c_heat +
         uLamp*c_elec + uCO2*c_co2 (constants c_rev/c_heat/c_elec/c_co2 already derived in
         rollout_oracle_mpc, lines ~2361-2364). Minimize sum(-(rev - cost)).
      5. Bounds: u in [0,1]^6 with uVent<=0.4 (as rollout_oracle_mpc); optional wide temp
         safety bounds. n_horizon = cfg.horizon; nlpsol_opts as in build_mpc_controller.

    Until wired, solver_parity is unavailable. The cleanest home for this is a new
    ``rollout_oracle_mpc_ipopt(cfg, ...)`` in article_experiment_utils.py next to
    rollout_oracle_mpc, reusing build_mpc_controller's do-mpc setup pattern.
    """
    raise NotImplementedError(
        "solver_parity: true-model IPOPT oracle not wired yet — see build_true_model_mpc "
        "TODO (embed env.unwrapped.F into a do-mpc model). Use --mode action_replay for the "
        "model-error decomposition, which is fully implemented.")


def solver_parity_seed(seed: int, pc, recipe, train_sc, test_scen, CORR, PRICES) -> list[dict]:
    # TODO(reviewer #6): once build_true_model_mpc is wired, run here:
    #   (a) surrogate MPC  (U.rollout_mpc with the frozen bundle)      -> EPI_surrogate
    #   (b) true-model IPOPT oracle (build_true_model_mpc + do-mpc loop) -> EPI_ipopt_oracle
    #   (c) CEM oracle     (U.rollout_oracle_mpc)                        -> EPI_cem_oracle
    # and record the pairwise EPI gaps so (b)-(a) = model share, (b)-(c) = optimizer share.
    raise NotImplementedError(
        "solver_parity_seed pending build_true_model_mpc (see TODO). Run --mode action_replay.")


# ── worker / shard / merge ───────────────────────────────────────────────────

def worker(args) -> int:
    seeds = _resolve_seeds(args)
    pc = P.DEFAULT.resolved(bool(args.fast))
    recipe = P.load_frozen_recipe()
    econ = P.read_env_economics(pc.location)
    CORR, PRICES = econ["corridors"], econ["prices"]
    test_scen = pc.test_scenario()
    train_sc = pc.train_scenarios()[0]
    out = _out_dir(args.out) / f"e3_oracle_parity_{args.tag}.csv"
    seed_fn = {"action_replay": action_replay_seed, "solver_parity": solver_parity_seed}[args.mode]
    print(f"[parity {args.tag}] mode={args.mode} seeds={seeds} out={out}", flush=True)

    records: list[dict] = []
    for s in seeds:
        t0 = time.time()
        try:
            records.extend(seed_fn(s, pc, recipe, train_sc, test_scen, CORR, PRICES))
            pd.DataFrame(records).to_csv(out, index=False)
            print(f"[parity {args.tag}] seed {s} done ({round(time.time() - t0, 1)}s)", flush=True)
        except NotImplementedError as exc:
            print(f"[parity {args.tag}] {exc}", flush=True)
            return 2
        except Exception as exc:  # noqa: BLE001
            print(f"[parity {args.tag}] seed {s} FAILED {type(exc).__name__}: "
                  f"{str(exc)[:160]}", flush=True)
    pd.DataFrame(records).to_csv(out, index=False)
    print(f"[parity {args.tag}] DONE wrote {out} ({len(records)} rows)", flush=True)
    return 0


def merge(args) -> int:
    outd = _out_dir(args.out)
    parts = sorted(glob.glob(str(outd / "e3_oracle_parity_*.csv")))
    parts = [p for p in parts if os.path.basename(p) != "e3_oracle_parity.csv"]
    frames = [pd.read_csv(p) for p in parts if os.path.getsize(p) > 0]
    if not frames:
        print("no oracle-parity partials found in", outd)
        return 1
    d = pd.concat(frames, ignore_index=True).drop_duplicates(["mode", "seed", "state"], keep="last")
    d.to_csv(outd / "e3_oracle_parity.csv", index=False)
    if "rmse_freerun_model" in d.columns:
        agg = (d.groupby(["mode", "state"])
               .agg(rmse_onestep=("rmse_onestep_model", "mean"),
                    rmse_freerun=("rmse_freerun_model", "mean"), n=("seed", "nunique"))
               .reset_index())
        print(agg.round(4).to_string(index=False))
    print(f"merged {len(parts)} partials -> {len(d)} rows -> {outd / 'e3_oracle_parity.csv'}")
    return 0


def _out_dir(out: str | None):
    from pathlib import Path
    if out:
        d = Path(out); d.mkdir(parents=True, exist_ok=True); return d
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
    ap.add_argument("--mode", choices=["action_replay", "solver_parity"], default="action_replay")
    ap.add_argument("--seeds", help="comma-separated seeds (explicit worker mode)")
    ap.add_argument("--shard-index", type=int, default=None, help="JOB_COMPLETION_INDEX")
    ap.add_argument("--num-shards", type=int, default=None, help="total shards (= completions)")
    ap.add_argument("--seeds-all", help="full seed list to shard, e.g. 0,1,...,19")
    ap.add_argument("--tag", default="local")
    ap.add_argument("--out", default=None)
    ap.add_argument("--fast", type=int, default=0)
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    if args.merge:
        return merge(args)
    return worker(args)


if __name__ == "__main__":
    raise SystemExit(main())
