"""Merge oracle horizon-probe partials into one table + the hero figure.

Reads every results_scenarios/tables/oracle_horizon_probe_*.csv (one per horizon
process), builds the EPI-vs-horizon curve with the rule_based reference line, and
saves:
  tables/oracle_horizon_sweep.csv   (tidy: horizon_h, oracle EPI, violations, ...)
  figures/oracle_horizon_sweep.png  (EPI vs horizon, rule_based dashed reference)

Robust to partial completion -- run it any time; it uses whatever partials exist.
Excludes the smoke tag (window_days==1) by default since a 1-day window is shorter
than the horizon and cannot show multi-day payoff (documented artifact).
"""
from __future__ import annotations

import os
import sys
import glob

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402

RES = U.results_dir()
TAB = RES / "tables"
FIG = RES / "figures"


def main() -> int:
    paths = sorted(glob.glob(str(TAB / "oracle_horizon_probe_*.csv")))
    paths = [p for p in paths if "smoke" not in os.path.basename(p)
             and "strong" not in os.path.basename(p)]  # strong-CEM files analysed separately
    if not paths:
        print("no oracle_horizon_probe_*.csv partials yet")
        return 0
    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    df = df[df["window_days"] > 1]  # drop any 1-day smoke rows
    # de-dup identical (method, seed, horizon) rows that appear in both local and
    # server partials (runs are deterministic, so duplicates are byte-identical)
    df = df.drop_duplicates(subset=["method", "seed", "horizon_h"], keep="last")
    if df.empty:
        print("only smoke rows present; run the 14-day sweep first")
        return 0

    win = int(df["window_days"].max())
    rb = df[df["method"] == "rule_based"]
    orc = df[df["method"] == "oracle_mpc"].copy()
    rb_epi = float(rb["epi"].mean()) if not rb.empty else np.nan

    # average across seeds per horizon (probe is usually 1 seed)
    g = (orc.groupby("horizon_h")
            .agg(epi=("epi", "mean"), epi_sd=("epi", "std"),
                 viol=("violation_steps_total", "mean"),
                 tcorr=("t_in_in_corridor_pct", "mean"),
                 secs=("secs", "mean"), n=("epi", "size"))
            .reset_index().sort_values("horizon_h"))
    g["rule_based_epi"] = rb_epi
    g["gap_to_rule_based"] = g["epi"] - rb_epi
    out_csv = TAB / "oracle_horizon_sweep.csv"
    g.to_csv(out_csv, index=False)

    print(f"\n=== Oracle horizon sweep (window={win}d, seeds={int(orc['seed'].nunique())}) ===")
    print(f"rule_based reference EPI = {rb_epi:+.3f} EUR/m2 over {win}d\n")
    with pd.option_context("display.float_format", lambda v: f"{v:.3f}"):
        print(g[["horizon_h", "epi", "gap_to_rule_based", "viol", "tcorr", "secs", "n"]]
              .to_string(index=False))

    crosses = g[g["epi"] >= rb_epi]
    if not crosses.empty:
        h0 = float(crosses["horizon_h"].min())
        print(f"\n>>> oracle EPI reaches/exceeds rule_based at horizon >= {h0:.0f} h "
              f"-> misalignment is HORIZON-driven (Path B justified / Path A hero result).")
    else:
        best = g.loc[g["epi"].idxmax()]
        print(f"\n>>> oracle EPI still < rule_based up to {g['horizon_h'].max():.0f} h "
              f"(best {best['epi']:+.3f} at {best['horizon_h']:.0f} h). "
              f"Trend slope tells whether longer horizon would close it.")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        ax.axhline(rb_epi, ls="--", color="tab:green", lw=1.8,
                   label=f"rule_based ({rb_epi:+.2f})")
        ax.plot(g["horizon_h"], g["epi"], "o-", color="tab:blue", lw=2,
                label="oracle-MPC (true model)")
        for _, r in g.iterrows():
            ax.annotate(f"{r['epi']:+.2f}", (r["horizon_h"], r["epi"]),
                        textcoords="offset points", xytext=(0, 8), fontsize=8, ha="center")
        ax.set_xlabel("MPC shooting horizon [hours]")
        ax.set_ylabel(f"EPI [EUR/m2 over {win} d]")
        ax.set_title("Oracle EPI vs planning horizon\n(economic objective, true model, Rostov 2020)")
        ax.legend(loc="best", fontsize=9)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        out_png = FIG / "oracle_horizon_sweep.png"
        fig.savefig(out_png, dpi=180)
        print(f"\nwrote {out_csv}\nwrote {out_png}")
    except Exception as exc:  # noqa: BLE001
        print(f"[plot skipped] {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
