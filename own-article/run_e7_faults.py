"""E7 — fault injection & safety (safety part of Г4). Distributed worker.

SINDy-MPC on the 2020 test season under sensor/actuator faults (onset mid-season),
with and without the residual-based safety supervisor. Writes the degradation table
results_scenarios/tables/e7_faults_<tag>.csv (incremental).
"""
from __future__ import annotations
import argparse, os, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402
import protocol_config as P  # noqa: E402

RECIPE = dict(feature_variant="physics_no_cross", library_degree=1, optimizer="stlsq", denoise="none")
FAULTS = [
    ("t_in_stuck", {"layer": "sensor", "target": "t_in", "type": "stuck", "value": 25.0}),
    ("t_in_offset", {"layer": "sensor", "target": "t_in", "type": "offset", "value": 4.0}),
    ("rh_offset", {"layer": "sensor", "target": "rh", "type": "offset", "value": -25.0}),
    ("uVent_dead", {"layer": "actuator", "target": "uVent", "type": "dead", "value": 0.0}),
    ("uBoil_stuck", {"layer": "actuator", "target": "uBoil", "type": "stuck", "value": 1.0}),
    ("uLamp_dead", {"layer": "actuator", "target": "uLamp", "type": "dead", "value": 0.0}),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-days", type=int, default=30)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--fast", type=int, default=0)
    a = ap.parse_args()
    pc = P.DEFAULT.resolved(bool(a.fast))
    RES = U.results_dir()
    econ = P.read_env_economics(pc.location); CORR, PRICES = econ["corridors"], econ["prices"]
    N = 5 if a.fast else a.n_days
    n_train = 7 if a.fast else 30
    onset = (N * int(86400 / pc.period)) // 3
    test = pc.test_scenario(); SS = test["start_date"]; s = a.seed
    cfg = pc.cfg_for(test, seed=s)
    out = RES / "tables" / f"e7_faults_{a.tag}.csv"
    rows = []
    def add(fault, supervised, df):
        m = U.epi_metrics(df, corridors=CORR, prices=PRICES)
        fl = float(df["flagged"].mean()) if "flagged" in df.columns else 0.0
        rows.append({"fault": fault, "supervised": int(supervised), "seed": s,
                     "epi": m["epi"], "viol": m["violation_steps_total"], "flag_frac": fl})
        pd.DataFrame(rows).to_csv(out, index=False)

    parts = [U.collect_rule_based_dataset(pc.cfg_for({"year": y, "start_date": f"{y}-03-01", "n_days": n_train}, seed=s), n_days=n_train, prbs_scale=0.3) for y in (2018, 2019)]
    b = U.fit_sindy(U.aggregate_trajectories(parts, pc.base_cfg(n_train)), period=float(pc.period), **RECIPE)
    add("none", 0, U.rollout_mpc(b, cfg, N, start_date=SS))
    print(f"[{a.tag}] baseline done", flush=True)
    for name, spec in FAULTS:
        f = {**spec, "start_step": onset}
        add(name, 0, U.rollout_mpc_faulty(b, cfg, N, f, start_date=SS, supervisor=False))
        add(name, 1, U.rollout_mpc_faulty(b, cfg, N, f, start_date=SS, supervisor=True, resid_threshold=3.0))
        print(f"[{a.tag}] {name} done", flush=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"[{a.tag}] DONE wrote {out} ({len(rows)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
