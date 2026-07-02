"""Merge distributed E3 partials (e3_seeded_*.csv) into the main artifacts.

Combines all partial CSVs, dedups on (method, seed), and writes:
  tables/e3_seeded.csv, tables/e3_main_table.csv, tables/e3_stats_vs_rulebased.csv,
  figures/e3_pareto_epi_violations.png
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np  # noqa: F401
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402


def main() -> int:
    RES = U.results_dir()
    parts = sorted(glob.glob(str(RES / "tables" / "e3_seeded_*.csv")))
    frames = []
    for p in parts:
        try:
            if os.path.getsize(p) > 0:
                frames.append(pd.read_csv(p))
        except Exception as exc:  # noqa: BLE001 (empty/partial file)
            print("skip unreadable partial:", os.path.basename(p), "->", exc)
    if not frames:
        print("no partials found")
        return 1
    seeded = pd.concat(frames, ignore_index=True).drop_duplicates(["method", "seed"], keep="last")
    seeded.to_csv(RES / "tables" / "e3_seeded.csv", index=False)

    agg = (seeded.groupby("method")
           .agg(epi_mean=("epi", "mean"), epi_std=("epi", "std"),
                viol_mean=("violation_steps_total", "mean"),
                Tcorr=("t_in_in_corridor_pct", "mean"), n=("epi", "size"))
           .reset_index().sort_values("epi_mean", ascending=False))
    if "oracle_mpc" in seeded.method.values:
        agg["gap_to_oracle"] = seeded[seeded.method == "oracle_mpc"]["epi"].mean() - agg["epi_mean"]
    agg.to_csv(RES / "tables" / "e3_main_table.csv", index=False)

    if "rule_based" in seeded.method.values:
        stats = U.paired_stats(seeded, "epi", baseline="rule_based")
        stats.to_csv(RES / "tables" / "e3_stats_vs_rulebased.csv", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 5))
    for meth, g in seeded.groupby("method"):
        x, y = g["violation_steps_total"].mean(), g["epi"].mean()
        ax.scatter(x, y, s=70)
        ax.annotate(meth, (x, y), fontsize=9, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("constraint violation steps")
    ax.set_ylabel("EPI, EUR/m2")
    ax.set_title("E3 Pareto: EPI vs violations")
    ax.grid(alpha=0.3)
    U.save_figure(fig, RES / "figures" / "e3_pareto_epi_violations.png")

    print(f"merged {len(parts)} partials -> {len(seeded)} rows, {seeded.method.nunique()} methods")
    print(agg.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
