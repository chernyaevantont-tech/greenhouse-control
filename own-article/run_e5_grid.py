"""E5 — generalization + OOD (Г4б,в). Distributed worker.

For each TRAIN season builds a surrogate + OOD detectors (Mahalanobis on exogenous
inputs, Ensemble-SINDy variance) and a guard threshold (95th pct of train Mahalanobis).
For each TEST season records: rollout-RMSE, EPI, mean OOD signals, and violations with
and without the OOD guard. Also dumps per-step (ood, violation) for the detector ROC.

Outputs: tables/e5_grid_<tag>.csv  and  tables/e5_roc_<tag>.csv
"""
from __future__ import annotations
import argparse, os, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402
import protocol_config as P  # noqa: E402

RECIPE = P.load_frozen_recipe()   # CONFIRMATORY frozen recipe (consistent with E3/E4)
DEF_TRAIN = "2019:03-01,2019:07-01"
DEF_TEST = "2020:03-01,2021:07-01,2022:10-01,2023:01-01,2021:03-01"


def _scen(sh, n):
    yr, md = sh.split(":")
    return {"year": int(yr), "start_date": f"{yr}-{md}", "n_days": n}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=DEF_TRAIN)
    ap.add_argument("--test", default=DEF_TEST)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-days", type=int, default=14)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--fast", type=int, default=0)
    a = ap.parse_args()
    pc = P.DEFAULT.resolved(bool(a.fast))
    RES = U.results_dir()
    econ = P.read_env_economics(pc.location); CORR, PRICES = econ["corridors"], econ["prices"]
    N = 5 if a.fast else a.n_days
    n_train = 7 if a.fast else 21
    trains = [t for t in a.train.split(",") if t]
    testss = [t for t in a.test.split(",") if t]
    print(f"[{a.tag}] trains={trains} tests={testss} N={N}", flush=True)

    grid_out = RES / "tables" / f"e5_grid_{a.tag}.csv"
    roc_out = RES / "tables" / f"e5_roc_{a.tag}.csv"
    grid, roc = [], []

    def viol_steps(df):
        v = np.zeros(len(df), dtype=int)
        for key in ("t_in", "co2", "rh"):
            lo, hi = CORR[key]; x = df[key].to_numpy(float)
            v += ((x < lo) | (x > hi)).astype(int)
        return v

    for tr in trains:
        train = U.collect_rule_based_dataset(pc.cfg_for(_scen(tr, n_train), seed=a.seed), n_days=n_train, prbs_scale=0.3)
        b = U.fit_sindy(train, period=float(pc.period), **RECIPE)
        maha = U.fit_mahalanobis(train)
        ens = U.fit_ensemble_for_variance(train, period=float(pc.period))
        thr = float(np.percentile(U.mahalanobis_distances(maha, train.weather, train.time_enc), 95))
        for te in testss:
            scen = _scen(te, N); cfg_t = pc.cfg_for(scen, seed=a.seed); SS = scen["start_date"]
            td = U.collect_rule_based_dataset(cfg_t, n_days=N, prbs_scale=0.0)
            maha_m = float(np.mean(U.mahalanobis_distances(maha, td.weather, td.time_enc)))
            ens_m = float(np.nanmean(U.ensemble_pred_std(ens, td)))
            ev = U.evaluate_sindy(b, td, rollout_horizons=(20,))
            rr = float(ev[(ev.metric_scope == "rollout") & (ev.state == "t_in")]["rmse"].iloc[0])
            du = U.rollout_mpc(b, cfg_t, N, start_date=SS)
            dg = U.rollout_mpc_guarded(b, maha, thr, cfg_t, N, start_date=SS)
            mu = U.epi_metrics(du, corridors=CORR, prices=PRICES)
            mg = U.epi_metrics(dg, corridors=CORR, prices=PRICES)
            grid.append({"train": tr, "test": te, "seed": a.seed, "rollout_rmse": rr,
                         "maha": maha_m, "ens_std": ens_m, "epi_unguarded": mu["epi"],
                         "viol_unguarded": mu["violation_steps_total"], "epi_guarded": mg["epi"],
                         "viol_guarded": mg["violation_steps_total"], "guard_frac": float(dg["guarded"].mean())})
            pd.DataFrame(grid).to_csv(grid_out, index=False)
            # per-step ROC from the UNGUARDED rollout (no guard confound): does the OOD
            # signal flag the steps that actually violate corridors?
            ood_un = U.mahalanobis_distances(maha, du[U.WEATHER_NAMES].to_numpy(), du[U.TIME_NAMES].to_numpy())
            vv = viol_steps(du)
            for ood_val, isv in zip(ood_un, vv):
                roc.append({"ood": float(ood_val), "violation": int(isv > 0)})
            pd.DataFrame(roc).to_csv(roc_out, index=False)
            print(f"[{a.tag}] {tr}->{te} rmse={rr:.2f} maha={maha_m:.2f} viol {mu['violation_steps_total']}->"
                  f"{mg['violation_steps_total']} (guard {dg['guarded'].mean()*100:.0f}%)", flush=True)
    print(f"[{a.tag}] DONE grid={len(grid)} roc={len(roc)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
