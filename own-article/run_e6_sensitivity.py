"""E6 — sensitivity of EPI to design choices (robustness of conclusions). Worker.

Re-simulation factors on the SINDy-MPC (physics_no_cross/STLSQ, trained on in-dist
2018+2019, evaluated on the 2020 test season):
  - MPC horizon  - STLSQ sparsity threshold  - surrogate-coefficient uncertainty (+/-%)
(Price sensitivity is computed post-hoc from E3 in the notebook -- no re-sim needed.)
Writes results_scenarios/tables/e6_sensitivity_<tag>.csv (incremental).
"""
from __future__ import annotations
import argparse, copy, os, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402
import protocol_config as P  # noqa: E402

RECIPE = dict(feature_variant="physics_no_cross", library_degree=1, optimizer="stlsq", denoise="none")


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
    test = pc.test_scenario(); SS = test["start_date"]
    out = RES / "tables" / f"e6_sensitivity_{a.tag}.csv"
    rows = []
    def add(factor, value, epi, **k):
        rows.append({"factor": factor, "value": value, "epi": epi, "seed": a.seed, **k})
        pd.DataFrame(rows).to_csv(out, index=False)

    s = a.seed
    parts = [U.collect_rule_based_dataset(pc.cfg_for({"year": y, "start_date": f"{y}-03-01", "n_days": n_train}, seed=s), n_days=n_train, prbs_scale=0.3) for y in (2018, 2019)]
    train = U.aggregate_trajectories(parts, pc.base_cfg(n_train))
    cfg0 = pc.cfg_for(test, seed=s)

    def epi_of(df):
        return U.epi_metrics(df, corridors=CORR, prices=PRICES)["epi"]

    # baseline + horizon sweep
    horizons = [8, 20] if a.fast else [8, 12, 20, 30]
    b0 = U.fit_sindy(train, threshold=0.05, period=float(pc.period), **RECIPE)
    for h in horizons:
        cfg_h = U.ExperimentConfig(**{**vars(cfg0), "horizon": h})
        e = epi_of(U.rollout_mpc(b0, cfg_h, N, start_date=SS))
        add("mpc_horizon", h, e); print(f"[{a.tag}] horizon {h} EPI={e:.3f}", flush=True)
    # STLSQ threshold sweep
    thrs = [0.05, 0.1] if a.fast else [0.01, 0.05, 0.1, 0.2]
    for thr in thrs:
        bt = U.fit_sindy(train, threshold=thr, period=float(pc.period), **RECIPE)
        e = epi_of(U.rollout_mpc(bt, cfg0, N, start_date=SS))
        nz = int(np.count_nonzero(bt.model.coefficients()))
        add("stlsq_threshold", thr, e, nonzero=nz); print(f"[{a.tag}] threshold {thr} EPI={e:.3f} nz={nz}", flush=True)
    # surrogate-coefficient uncertainty (model mismatch)
    perts = [0.1] if a.fast else [0.1, 0.2, 0.3]
    reps = 1 if a.fast else 2
    Xi0 = np.asarray(b0.model.coefficients())
    for pert in perts:
        for rep in range(reps):
            bp = copy.deepcopy(b0)
            rng = np.random.default_rng(1000 * s + int(pert * 100) + rep)
            bp.model.optimizer.coef_ = Xi0 * (1.0 + pert * rng.standard_normal(Xi0.shape))
            e = epi_of(U.rollout_mpc(bp, cfg0, N, start_date=SS))
            add("coef_uncertainty", pert, e, rep=rep); print(f"[{a.tag}] coef_unc {pert} rep{rep} EPI={e:.3f}", flush=True)

    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"[{a.tag}] DONE wrote {out} ({len(rows)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
