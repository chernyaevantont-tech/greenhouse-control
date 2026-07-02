"""Merge E7 (fault injection) -> degradation table + figure.

Outputs: tables/e7_degradation.csv, figures/e7_faults.png
"""
from __future__ import annotations
import glob, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402


def main() -> int:
    RES = U.results_dir()
    frames = [pd.read_csv(p) for p in sorted(glob.glob(str(RES / "tables" / "e7_faults_*.csv"))) if os.path.getsize(p) > 0]
    if not frames:
        print("no e7 partials"); return 1
    df = pd.concat(frames, ignore_index=True)
    base_epi = float(df[df.fault == "none"]["epi"].mean())
    base_viol = float(df[df.fault == "none"]["viol"].mean())

    faults = [f for f in df.fault.unique() if f != "none"]
    rows = []
    for f in faults:
        un = df[(df.fault == f) & (df.supervised == 0)]
        su = df[(df.fault == f) & (df.supervised == 1)]
        rows.append({
            "fault": f,
            "epi_unsup": un["epi"].mean(), "viol_unsup": un["viol"].mean(),
            "epi_sup": su["epi"].mean(), "viol_sup": su["viol"].mean(),
            "flag_frac": su["flag_frac"].mean(),
            "viol_reduced_by_sup": un["viol"].mean() - su["viol"].mean(),
        })
    tab = pd.DataFrame(rows).sort_values("viol_unsup", ascending=False)
    tab.insert(1, "baseline_viol", base_viol)
    tab.insert(1, "baseline_epi", base_epi)
    tab.to_csv(RES / "tables" / "e7_degradation.csv", index=False)

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(len(tab)); w = 0.38
    ax.bar(x - w / 2, tab["viol_unsup"], w, label="no supervisor")
    ax.bar(x + w / 2, tab["viol_sup"], w, label="with supervisor")
    ax.axhline(base_viol, color="k", ls="--", lw=1, label=f"fault-free ({base_viol:.0f})")
    ax.set_xticks(x, tab["fault"], rotation=25, ha="right"); ax.set_ylabel("corridor-violation steps")
    ax.set_title("E7 — fault degradation & supervisor mitigation"); ax.legend(fontsize=8)
    U.save_figure(fig, RES / "figures" / "e7_faults.png")

    print(f"fault-free baseline: EPI={base_epi:.3f}, viol={base_viol:.0f}")
    print(tab.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
