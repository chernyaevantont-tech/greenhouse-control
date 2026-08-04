"""E3 Pareto (EPI x violations) — annotated figure + table from the FRESH 20-seed
merge (e3_main_table.csv, 11 methods). Regenerates the paper artifact:
  figures/e3_pareto_annotated.png
  tables/e3_pareto_table.csv   (epi, viol, scaled_pen, on_frontier, dominated_by)

Two-axis criterion (EXPERIMENT_PROTOCOL 0/3): EPI is decoupled from violations, so
the primary E3 read is Pareto-dominance in (EPI up, violations down), not 1-D EPI.
The base run_e3_seeds "sindy_mpc" row (== confirmatory recipe) is dropped as a
duplicate of "sindy_mpc_confirmatory"; a paper-facing display name is applied.
"""
from __future__ import annotations
import os, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U

# max per-constraint violations used by gl_gym GreenhouseReward to scale penalties
MAXV = {"t_in": 15.0, "co2": 2500.0, "rh": 15.0}
DROP = {"sindy_mpc"}   # duplicate of sindy_mpc_confirmatory (same frozen recipe)
DISPLAY = {
    "rule_based": "Rule-based", "grey_box_mpc": "Grey-box MPC", "oracle_mpc": "Oracle (3h CEM)",
    "nn_mpc": "NN-MPC", "ppo": "PPO", "sac": "SAC",
    "sindy_mpc_confirmatory": "SINDy-MPC (confirmatory)", "sindy_mpc_dense": "SINDy-MPC (dense)",
    "sindy_mpc_conf_dagger": "SINDy-MPC (conf+DAgger)", "sindy_mpc_dense_dagger": "SINDy-MPC (dense+DAgger)",
}


def scaled_penalty(seeded: pd.DataFrame) -> pd.Series:
    """Dimensionally-consistent severity per method: mean_seeds sum_c(area_c / maxv_c)."""
    if seeded.empty:
        return pd.Series(dtype=float)
    s = sum(seeded[f"{c}_violation_area"] / MAXV[c] for c in MAXV)
    return seeded.assign(_sp=s).groupby("method")["_sp"].mean()


def main() -> int:
    RES = U.results_dir()
    m = pd.read_csv(RES / "tables" / "e3_main_table.csv")
    m = m[~m.method.isin(DROP)].copy()
    try:
        sp = scaled_penalty(pd.read_csv(RES / "tables" / "e3_seeded.csv"))
        m["scaled_pen"] = m.method.map(sp).round(1)
    except Exception:
        m["scaled_pen"] = np.nan
    m = m.rename(columns={"epi_mean": "epi", "viol_mean": "viol"})

    # Non-dominated set: maximize EPI, minimize violations.
    on_front, dominated_by = [], []
    for _, r in m.iterrows():
        dom = m[(m.epi >= r.epi) & (m.viol <= r.viol) & (m.method != r.method) &
                ((m.epi > r.epi) | (m.viol < r.viol))]
        on_front.append(dom.empty)
        dominated_by.append("" if dom.empty else dom.sort_values("epi", ascending=False).iloc[0].method)
    m["on_frontier"] = on_front
    m["dominated_by"] = dominated_by
    m["label"] = m.method.map(DISPLAY).fillna(m.method)
    m = m.sort_values("epi", ascending=False)
    cols = ["method", "label", "epi", "epi_std", "viol", "scaled_pen", "Tcorr", "n", "on_frontier", "dominated_by"]
    m[cols].to_csv(RES / "tables" / "e3_pareto_table.csv", index=False)

    # --- figure ---
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    fr = m[m.on_frontier]
    dm = m[~m.on_frontier]
    ax.scatter(dm.viol, dm.epi, s=70, c="lightgrey", edgecolor="grey", zorder=2, label="dominated")
    ax.scatter(fr.viol, fr.epi, s=110, c="tab:red", edgecolor="k", zorder=3, label="non-dominated (frontier)")
    frs = fr.sort_values("viol")
    ax.plot(frs.viol, frs.epi, "--", color="tab:red", lw=1.2, alpha=0.7, zorder=1)
    ax.axhline(0, color="grey", lw=0.6, ls=":")
    # per-label nudges: dense≈grey-box collide (a meaningful coincidence — the fix
    # collapses onto the physical grey-box model); separate them and flag it.
    OFFSET = {"grey_box_mpc": (8, -14), "sindy_mpc_dense": (8, 7), "nn_mpc": (-46, 4),
              "oracle_mpc": (8, -14), "sindy_mpc_confirmatory": (8, 6)}
    for _, r in m.iterrows():
        dx, dy = OFFSET.get(r.method, (6, 4))
        ax.annotate(r.label, (r.viol, r.epi), fontsize=8.5,
                    xytext=(dx, dy), textcoords="offset points",
                    fontweight=("bold" if r.on_frontier else "normal"))
    # annotate the dense≈grey-box coincidence explicitly
    gb = m[m.method == "grey_box_mpc"]
    if not gb.empty:
        ax.annotate("dense fix ≈ grey-box\n(parsimony ≠ interpretability)",
                    (gb.viol.iloc[0], gb.epi.iloc[0]), fontsize=7.5, color="dimgray",
                    xytext=(-140, 18), textcoords="offset points",
                    arrowprops=dict(arrowstyle="->", color="dimgray", lw=0.7))
    ax.set_xlabel("constraint-violation steps (season total, lower is better)")
    ax.set_ylabel("EPI, EUR/m²·season (higher is better)")
    ax.set_title("E3 Pareto (EPI × violations), 20 seeds — frontier: rule-based, SINDy-MPC(conf+DAgger), PPO")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)
    U.save_figure(fig, RES / "figures" / "e3_pareto_annotated.png")

    print("frontier:", list(fr.label))
    print(m[["label", "epi", "viol", "scaled_pen", "on_frontier", "dominated_by"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
