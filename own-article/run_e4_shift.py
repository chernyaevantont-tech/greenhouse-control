"""E4 — online adaptation under weather shift (Г4а). Distributed worker.

Trains a degree-1 physics_no_cross/STLSQ surrogate offline on in-distribution weather
(spring 2018+2019), then deploys on an OOD shift season and compares:
  offline (static) | ekf_sindy (online RLS) | dagger (iterative refit) |
  rule_based (adaptation-free ref) | retrained_on_shift (adaptation ceiling).
Writes results_scenarios/tables/e4_seeded_<tag>.csv (incremental).

Example:
  python run_e4_shift.py --shift 2021:07-01 --seeds 0,1 --n-days 30 --dagger-iters 3 --tag s2021
"""
from __future__ import annotations

import argparse, os, sys, time, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402
import protocol_config as P  # noqa: E402

# Adaptive surrogate base = the CONFIRMATORY frozen recipe (consistent with E3/E5). The
# ensemble optimizer still exposes a single median coefficient set that EKF/DAgger update.
RECIPE = P.load_frozen_recipe()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shift", required=True, help="OOD season as YEAR:MM-DD, e.g. 2021:07-01")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--n-days", type=int, default=30)
    ap.add_argument("--dagger-iters", type=int, default=3)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--fast", type=int, default=0)
    a = ap.parse_args()

    pc = P.DEFAULT.resolved(bool(a.fast))
    RES = U.results_dir()
    econ = P.read_env_economics(pc.location); CORR, PRICES = econ["corridors"], econ["prices"]
    seeds = [int(s) for s in a.seeds.split(",") if s.strip() != ""]
    N = 5 if a.fast else a.n_days
    yr, md = a.shift.split(":"); shift = {"year": int(yr), "start_date": f"{yr}-{md}", "n_days": N}
    SS = shift["start_date"]
    n_train = 7 if a.fast else 30
    iters = 2 if a.fast else a.dagger_iters
    out = RES / "tables" / f"e4_seeded_{a.tag}.csv"
    print(f"[{a.tag}] shift={SS} N={N} seeds={seeds} dagger_iters={iters}", flush=True)

    rows = []
    def rec(method, seed, df, **kw):
        m = U.epi_metrics(df, corridors=CORR, prices=PRICES)
        m.update({"method": method, "seed": seed, "shift": SS, **kw})
        rows.append(m); pd.DataFrame(rows).to_csv(out, index=False)
        print(f"[{a.tag}] s{seed} {method}{kw} EPI={m.get('epi', float('nan')):.3f} viol={m.get('violation_steps_total',-1)}", flush=True)

    for s in seeds:
        cfg_s = pc.cfg_for(shift, seed=s)
        # in-distribution offline training (spring 2018 + 2019)
        parts = [U.collect_rule_based_dataset(pc.cfg_for({"year": y, "start_date": f"{y}-03-01", "n_days": n_train}, seed=s),
                                              n_days=n_train, prbs_scale=0.3) for y in (2018, 2019)]
        train_in = U.aggregate_trajectories(parts, pc.base_cfg(n_train))
        try:
            b_off = U.fit_sindy(train_in, period=float(pc.period), metadata={"label": "offline"}, **RECIPE)
            rec("rule_based", s, U.rollout_rule_based(cfg_s, N, start_date=SS, noise_scale=0.0, seed=s))
            rec("offline", s, U.rollout_mpc(b_off, cfg_s, N, start_date=SS))
            rec("ekf_sindy", s, U.rollout_mpc_ekf(b_off, cfg_s, N, start_date=SS, rebuild_every=96))
            # Retrained-on-shift ceiling = genuine upper bound on adaptation. FIX: match
            # the OFFLINE data budget (2*n_train days on the shift season), not just the
            # N-day eval window. Previously it trained on only N days -> less data than
            # offline (2*n_train) -> could fall BELOW offline, making gap_recovered
            # (metric-offline)/(ceiling-offline) invalid (negative denominator).
            n_ceil = 2 * n_train
            ceil_scen = {"year": int(yr), "start_date": SS, "n_days": n_ceil}
            tr_s = U.collect_rule_based_dataset(pc.cfg_for(ceil_scen, seed=s), n_days=n_ceil, prbs_scale=0.3)
            b_s = U.fit_sindy(tr_s, period=float(pc.period), metadata={"label": "retrained"}, **RECIPE)
            rec("retrained_ceiling", s, U.rollout_mpc(b_s, cfg_s, N, start_date=SS))
            # DAgger: iteratively deploy on the shift, aggregate, refit
            datasets = [train_in]
            for it in range(iters + 1):
                agg = U.aggregate_trajectories(datasets, pc.base_cfg(n_train))
                b_it = U.fit_sindy(agg, period=float(pc.period), metadata={"label": f"dagger{it}"}, **RECIPE)
                df_it = U.rollout_mpc(b_it, cfg_s, N, start_date=SS)
                rec("dagger", s, df_it, dagger_iter=it)
                datasets.append(U.trajectory_from_frame(df_it, cfg_s, source=f"dagger_{it}"))
        except Exception as exc:  # noqa: BLE001
            print(f"[{a.tag}] s{seed if False else s} FAILED {type(exc).__name__}: {str(exc)[:120]}", flush=True)

    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"[{a.tag}] DONE wrote {out} ({len(rows)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
