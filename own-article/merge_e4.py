"""Merge E4 (online adaptation) partials -> adaptation table + DAgger recovery curve.

Outputs: tables/e4_adaptation_table.csv, tables/e4_dagger_curve.csv,
         figures/e4_adaptation.png
"""
from __future__ import annotations
import glob, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402


def main() -> int:
    RES = U.results_dir()
    parts = sorted(glob.glob(str(RES / "tables" / "e4_seeded_*.csv")))
    frames = []
    for p in parts:
        try:
            if os.path.getsize(p) > 0:
                frames.append(pd.read_csv(p))
        except Exception as exc:  # noqa: BLE001
            print("skip", os.path.basename(p), exc)
    if not frames:
        print("no e4 partials"); return 1
    df = pd.concat(frames, ignore_index=True)

    # DAgger: keep the final iteration per (shift, seed) for the main table.
    dag = df[df.method == "dagger"].copy()
    nondag = df[df.method != "dagger"].copy()
    if not dag.empty:
        fin = dag.loc[dag.groupby(["shift", "seed"])["dagger_iter"].idxmax()].assign(method="dagger_final")
        main = pd.concat([nondag, fin], ignore_index=True)
    else:
        main = nondag
    agg = (main.groupby("method")
           .agg(epi_mean=("epi", "mean"), epi_std=("epi", "std"),
                viol_mean=("violation_steps_total", "mean"), n=("epi", "size"))
           .reset_index().sort_values("epi_mean", ascending=False))
    # Recovery metrics. NOTE: retrained_ceiling can fall BELOW offline here -- retraining
    # the surrogate on the shifted season yields a WORSE closed-loop controller (a genuine
    # finding, the surrogate-MPC exploits model error), which makes an offline->ceiling
    # ratio meaningless (negative denominator). So: (1) report the ceiling-referenced % only
    # when the ceiling is actually above offline; (2) also report recovery toward rule_based,
    # the strongest non-adaptive controller under shift and always a valid reference.
    piv = main.groupby("method")["epi"].mean()
    off = piv.get("offline", np.nan)
    ceil = piv.get("retrained_ceiling", np.nan)
    rb = piv.get("rule_based", np.nan)
    if np.isfinite(off) and np.isfinite(ceil) and (ceil - off) > 1e-9:
        agg["gap_recovered_pct"] = ((agg["epi_mean"] - off) / (ceil - off) * 100.0).round(1)
    else:
        agg["gap_recovered_pct"] = np.nan
        print(f"[WARN] retrained_ceiling ({ceil:.3f}) <= offline ({off:.3f}): ceiling-referenced "
              f"recovery is UNDEFINED (set NaN) -- retrain-on-shift underperforms offline (finding).")
    if np.isfinite(off) and np.isfinite(rb) and (rb - off) > 1e-9:
        agg["recovery_vs_rulebased_pct"] = ((agg["epi_mean"] - off) / (rb - off) * 100.0).round(1)
    agg.to_csv(RES / "tables" / "e4_adaptation_table.csv", index=False)

    curve = (df[df.method == "dagger"].groupby("dagger_iter")["epi"]
             .agg(["mean", "std", "size"]).reset_index()) if not dag.empty else pd.DataFrame()
    if not curve.empty:
        curve.to_csv(RES / "tables" / "e4_dagger_curve.csv", index=False)

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    order = ["offline", "ekf_sindy", "dagger_final", "retrained_ceiling", "rule_based"]
    a = agg.set_index("method").reindex([m for m in order if m in agg.method.values])
    ax[0].bar(a.index, a["epi_mean"], yerr=a["epi_std"].fillna(0))
    ax[0].axhline(0, color="k", lw=0.8); ax[0].set_ylabel("EPI EUR/m2"); ax[0].set_title("E4: EPI under OOD shift")
    ax[0].tick_params(axis="x", rotation=20)
    if not curve.empty:
        ax[1].errorbar(curve["dagger_iter"], curve["mean"], yerr=curve["std"].fillna(0), marker="o")
        ax[1].set_xlabel("DAgger iteration"); ax[1].set_ylabel("EPI EUR/m2"); ax[1].set_title("DAgger recovery curve"); ax[1].grid(alpha=.3)
    U.save_figure(fig, RES / "figures" / "e4_adaptation.png")

    print(agg.round(3).to_string(index=False))
    if not curve.empty:
        print("\nDAgger curve (EPI by iter):")
        print(curve.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
