"""E3 ablation: sparsity threshold lambda <-> boiler term <-> closed-loop EPI.

Sweeps the STLSQ sparsity threshold lambda on the physics_no_cross / degree-1
surrogate and, per lambda, records:
  - nonzero            : number of surviving coefficients (parsimony)
  - uBoil              : signed uBoil->t_in coefficient (control-critical actuator)
  - rmse               : OPEN-LOOP rollout-RMSE of t_in (h=20) on the test season
  - epi, viol          : CLOSED-LOOP EPI and constraint violations (rollout_mpc)

The headline methodological finding (EXPERIMENT_PROTOCOL E3): as lambda grows the
boiler term uBoil->t_in is zeroed (~lambda 0.05) and closed-loop EPI collapses,
WHILE open-loop rollout-RMSE stays almost flat -> the pre-registered open-loop
selection is BLIND to the closed-loop failure (the argument against `sparsity`
as an E2 recipe-selection objective).

Distributed like run_e3_seeds.py: workers shard by seed and write
e3_lambda_seed_<tag>.csv; `--merge` aggregates all seeds into the article
artifacts tables/e3_lambda_sweep_table.csv + figures/e3_lambda_sweep_ablation.png.

Examples
  python e3_lambda_sweep.py --seeds 0 --tag s0      # worker (one seed)
  python e3_lambda_sweep.py --merge                 # aggregate + figure
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

LAMBDAS = [1e-6, 1e-3, 0.01, 0.02, 0.03, 0.04, 0.05, 0.1]
DENSE_BASE = dict(feature_variant="physics_no_cross", library_degree=1, optimizer="stlsq", denoise="none")


def uboil_coef(bundle) -> float:
    ct = U.coefficient_table(bundle)
    r = ct[(ct.equation == "t_in") & (ct.term == "uBoil")]
    return float(r.coefficient.iloc[0]) if len(r) else float("nan")


def worker(seeds, tag, fast) -> int:
    pc = P.DEFAULT.resolved(bool(fast))
    RES = U.results_dir()
    econ = P.read_env_economics(pc.location)
    CORR, PRICES = econ["corridors"], econ["prices"]
    test_scen = pc.test_scenario()
    TEST_START = test_scen["start_date"]
    N = pc.n_days_test
    train_sc = pc.train_scenarios()[0]
    lams = [1e-6, 0.03, 0.1] if fast else LAMBDAS
    print(f"[lam {tag}] seeds={seeds} N_TEST={N} lambdas={lams}", flush=True)

    out = RES / "tables" / f"e3_lambda_seed_{tag}.csv"
    rows = []

    def flush():
        pd.DataFrame(rows).to_csv(out, index=False)

    for s in seeds:
        cfg_te = pc.cfg_for(test_scen, seed=s)
        cfg_tr = pc.cfg_for(train_sc, seed=s)
        train = U.collect_rule_based_dataset(cfg_tr, n_days=pc.n_days_train, prbs_scale=0.3)
        # Open-loop RMSE is measured on the deployment (test) season -- the honest
        # open-loop generalization metric that the pre-registration relies on.
        evald = U.collect_rule_based_dataset(cfg_te, n_days=N, start_date=TEST_START, prbs_scale=0.0)
        for lam in lams:
            t0 = time.time()
            try:
                b = U.fit_sindy(train, period=float(pc.period), threshold=lam,
                                metadata={"label": f"lam_{lam}"}, **DENSE_BASE)
                nz = int(np.count_nonzero(b.model.coefficients()))
                ub = uboil_coef(b)
                ev = U.evaluate_sindy(b, evald, rollout_horizons=(20,))
                sub = ev[(ev.metric_scope == "rollout") & (ev.state == "t_in")]["rmse"]
                rmse = float(sub.iloc[0]) if len(sub) else float("nan")
                df = U.rollout_mpc(b, cfg_te, n_days=N, start_date=TEST_START)
                m = U.epi_metrics(df, corridors=CORR, prices=PRICES)
                rows.append({"lam": lam, "seed": s, "nonzero": nz, "uBoil": ub, "rmse": rmse,
                             "epi": m["epi"], "viol": m["violation_steps_total"],
                             "secs": round(time.time() - t0, 1)})
                flush()
                print(f"[lam {tag}] s{s} lam={lam:g} nz={nz} uBoil={ub:.4f} rmse={rmse:.2f} "
                      f"EPI={m['epi']:.3f} viol={m['violation_steps_total']}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[lam {tag}] s{s} lam={lam:g} FAILED {type(exc).__name__}: {str(exc)[:110]}", flush=True)
    flush()
    print(f"[lam {tag}] DONE wrote {out} ({len(rows)} rows)", flush=True)
    return 0


def merge() -> int:
    RES = U.results_dir()
    parts = sorted(glob.glob(str(RES / "tables" / "e3_lambda_seed_*.csv")))
    frames = [pd.read_csv(p) for p in parts if os.path.getsize(p) > 0]
    if not frames:
        print("no lambda partials found")
        return 1
    d = pd.concat(frames, ignore_index=True)
    agg = (d.groupby("lam")
           .agg(nonzero=("nonzero", "mean"), uBoil=("uBoil", "mean"), rmse=("rmse", "mean"),
                epi=("epi", "mean"), epi_std=("epi", "std"), viol=("viol", "mean"), n=("epi", "size"))
           .reset_index().sort_values("lam"))
    agg.to_csv(RES / "tables" / "e3_lambda_sweep_table.csv", index=False)
    print(f"merged {len(parts)} lambda partials -> {len(d)} rows")
    print(agg.round(4).to_string(index=False))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axL = plt.subplots(figsize=(7.5, 5))
        x = agg["lam"].to_numpy()
        axL.set_xscale("log")
        l1 = axL.plot(x, agg["epi"], "o-", color="tab:blue", label="closed-loop EPI")[0]
        axL.set_xlabel("STLSQ sparsity threshold  λ")
        axL.set_ylabel("closed-loop EPI, EUR/m²", color="tab:blue")
        axL.axhline(0, color="grey", lw=0.6, ls=":")
        axR = axL.twinx()
        l2 = axR.plot(x, agg["rmse"], "s--", color="tab:red", label="open-loop rollout-RMSE (t_in)")[0]
        l3 = axR.plot(x, agg["uBoil"] * 50.0, "^:", color="tab:green", label="uBoil→t_in coef ×50")[0]
        axR.set_ylabel("open-loop RMSE  /  uBoil×50", color="tab:red")
        axL.set_title("E3: open-loop selection is blind to closed-loop boiler collapse")
        axL.legend(handles=[l1, l2, l3], loc="lower left", fontsize=9)
        axL.grid(alpha=0.3)
        U.save_figure(fig, RES / "figures" / "e3_lambda_sweep_ablation.png")
    except Exception as exc:  # noqa: BLE001
        print("figure skipped:", type(exc).__name__, str(exc)[:100])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", help="comma-separated seeds (worker mode)")
    ap.add_argument("--tag", help="output tag (worker mode)")
    ap.add_argument("--fast", type=int, default=0)
    ap.add_argument("--merge", action="store_true", help="aggregate partials into table+figure")
    a = ap.parse_args()
    if a.merge:
        return merge()
    if not a.seeds or not a.tag:
        ap.error("worker mode needs --seeds and --tag (or use --merge)")
    seeds = [int(s) for s in a.seeds.split(",") if s.strip() != ""]
    return worker(seeds, a.tag, a.fast)


if __name__ == "__main__":
    raise SystemExit(main())
