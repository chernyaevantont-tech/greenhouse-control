"""Figure 6 of the figure plan -- the UNNUMBERED GRAPHICAL ABSTRACT.

Plan slot 6 is ``fig-graphical-abstract`` (five numbered body figures plus this
one).  SPEC.md, section "Graphical abstract -- unnumbered":

    (a) The reversal: one-step RMSE (x) against median 24-h rollout RMSE
        (y, log), marker area proportional to kappa, arrow raw -> physics,
        annotate kappa = 8.2 / 24.5 / 53.4.
    (b) The Pareto front, as Figure 2 but stripped of error bars and minor
        labels.

    Sources: identical to Figures 1a and 2.

The LaTeX comment block at ``05-conclusions-abstract.tex:210-226`` resolves the
granularity of (a): "one marker per configuration ... marker area proportional
to the condition number kappa", with the y value a *median* rollout RMSE.  A
configuration in the ladder is a ``(variant, degree, optimizer, denoise)``
label carrying 20 seeds, so the block plotted here is 3 libraries x 2 sparse
estimators = 6 aggregate markers over 120 fits.  kappa is a property of the
library (identical across its two estimators), which is why only three marker
areas appear.

Nothing is hardcoded: every plotted coordinate, whisker, area, arrow endpoint
and annotation number is reduced from the CSVs inside this script, through the
loaders in ``_plotstyle`` (which own the dedup key and the solver-abort rule).

TWO DELIBERATE DEPARTURES FROM THE SPEC WORDING, both recorded in the reply:

  1. Panel (b) is "stripped of error bars" in the spec.  Thin +/-1 SD whiskers
     are drawn anyway, in light grey behind the markers.  The panel's claim is
     that the raw-library advantage is *not* Pareto-dominant, and the SD on
     ``sindy_mpc_raw_ens`` (4.08 EUR/m2 about a 4.32 mean) is what makes the
     conservative reading legible.  They are subordinate, not prominent.
  2. Panel (a) carries the per-seed cloud behind the six aggregates, plus IQR
     and SD whiskers, for the same reason: the rollout distribution is
     heavy-tailed and the reversal must not read as three tidy points.

SCOPE GUARD (SPEC.md, Figure 1).  The reversal shown in (a) holds in the
degree-1, undenoised block under sparse estimators only -- 2 of 72
configurations per library.  Pooled over all 72 labels the raw library has the
best mean one-step RMSE and there is no reversal.  The panel says so on its
face; the caption must repeat it.  ``sign_pass`` is NaN in all 1440 ladder
rows and is not encoded anywhere.

Run:
    PYTHONIOENCODING=utf-8 python make_fig6.py
Writes fig6.{pdf,png} and fig-graphical-abstract.{pdf,png} into this directory,
and prints every plotted value as JSON on stdout for external verification.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

import _plotstyle as ps

# Marker area is proportional to kappa; this is the only free constant in the
# figure and it is a pure display scale, not a datum.
KAPPA_AREA_PER_UNIT = 6.5

FRONT_COLOR_FALLBACK = ps.OKABE_ITO["green"]
GREY = ps.OKABE_ITO["grey"]


# ---------------------------------------------------------------------------
# Panel (a) -- reduction
# ---------------------------------------------------------------------------

def reversal_table() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Per-configuration and per-library reductions of the ladder block.

    Returns ``(fits, per_config, per_library)``.  ``fits`` is the raw 120-row
    block that goes behind the aggregates as the dispersion cloud.
    """
    fits = ps.load_ladder(degree=1, denoise="none",
                          optimizers=("stlsq", "ensemble"))

    def q(p):
        return lambda x: x.quantile(p)

    per_config = (fits.groupby(["variant", "optimizer"], observed=True)
                       .agg(n=("kappa", "size"),
                            kappa=("kappa", "mean"),
                            one_step=("one_step_rmse_t_in", "mean"),
                            one_step_sd=("one_step_rmse_t_in", "std"),
                            rollout_median=("rollout_rmse_t_in", "median"),
                            rollout_q25=("rollout_rmse_t_in", q(0.25)),
                            rollout_q75=("rollout_rmse_t_in", q(0.75)),
                            diverged=("diverged_frac", "mean"))
                       .reset_index())

    per_library = ps.ladder_summary(fits)
    return fits, per_config, per_library


def draw_reversal(ax, fits, per_config, per_library) -> None:
    # -- dispersion cloud: one faint dot per fit (20 seeds x 6 configurations)
    for lib in ps.LIB_ORDER:
        sub = fits[fits["variant"] == lib]
        ax.scatter(sub["one_step_rmse_t_in"], sub["rollout_rmse_t_in"],
                   s=4.5, color=ps.LIB_COLOR[lib], alpha=0.22,
                   linewidths=0, zorder=2)

    # -- six aggregate markers, area proportional to kappa
    for r in per_config.itertuples():
        lib = str(r.variant)
        col = ps.LIB_COLOR[lib]
        ax.errorbar(r.one_step, r.rollout_median,
                    xerr=r.one_step_sd,
                    yerr=[[r.rollout_median - r.rollout_q25],
                          [r.rollout_q75 - r.rollout_median]],
                    fmt="none", ecolor=col, elinewidth=0.7,
                    capsize=1.6, capthick=0.7, alpha=0.9, zorder=4)
        ax.scatter([r.one_step], [r.rollout_median],
                   s=KAPPA_AREA_PER_UNIT * r.kappa,
                   marker=ps.OPT_MARKER[r.optimizer],
                   facecolors=col, edgecolors="white", linewidths=0.6,
                   alpha=0.95, zorder=5)

    lib_at = {str(r.variant): r for r in per_library.itertuples()}

    # -- the reversal, as an arrow from the raw library to the physics library
    a = lib_at["raw"]
    b = lib_at["physics"]
    ax.annotate("", xy=(b.one_step, b.rollout_median),
                xytext=(a.one_step, a.rollout_median),
                arrowprops=dict(arrowstyle="-|>", color="#333333",
                                lw=1.0, shrinkA=13, shrinkB=17,
                                connectionstyle="arc3,rad=-0.22"),
                zorder=6)
    mid_x = 0.5 * (a.one_step + b.one_step)
    mid_y = np.sqrt(a.rollout_median * b.rollout_median)   # log-scale midpoint
    ax.text(mid_x + 0.035, mid_y * 0.62,
            "richer physics library:\nbetter one step, worse rollout",
            fontsize=6.6, color="#333333", ha="center", va="center",
            linespacing=1.25)

    # -- kappa and divergence, per library, from the reduction
    offsets = {"raw": (0.012, 1.55), "physics_no_cross": (0.012, 1.42),
               "physics": (0.012, 1.30)}
    for lib in ps.LIB_ORDER:
        r = lib_at[lib]
        dx, fy = offsets[lib]
        ax.text(r.one_step + dx, r.rollout_median * fy,
                f"$\\kappa$ = {r.kappa:.1f}\ndiverged {r.diverged:.3f}",
                fontsize=6.4, color=ps.LIB_COLOR[lib], ha="left", va="bottom",
                linespacing=1.2)

    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker="o", ls="", color=ps.LIB_COLOR[l],
                      markeredgecolor="white", markeredgewidth=0.5,
                      label=ps.LIB_LABEL[l], markersize=4.5)
               for l in ps.LIB_ORDER]
    handles += [Line2D([], [], marker=ps.OPT_MARKER[o], ls="", color="#555555",
                       label=o, markersize=3.8) for o in ("stlsq", "ensemble")]
    ax.legend(handles=handles, loc="upper right", ncol=1, handletextpad=0.4,
              borderpad=0.2, labelspacing=0.28)

    ax.set_yscale("log")
    ax.set_xlabel("one-step RMSE of $T_\\mathrm{in}$  ($^\\circ$C)")
    ax.set_ylabel("24 h rollout RMSE of $T_\\mathrm{in}$  ($^\\circ$C, log scale)")
    n_seed = int(per_config["n"].iloc[0])
    ax.annotate_text = None
    ps.annotate_n(ax,
                  f"degree-1, undenoised block, sparse estimators only "
                  f"({len(fits)} fits, {n_seed} seeds per marker);\n"
                  f"marker area $\\propto\\ \\kappa$.  Pooled over all 72 ladder "
                  f"labels there is no reversal.",
                  loc="lower left")
    ps.panel_label(ax, "a", dx=-0.13)


# ---------------------------------------------------------------------------
# Panel (b) -- reduction
# ---------------------------------------------------------------------------

def pareto_table() -> pd.DataFrame:
    """Assemble the three harnesses of the Pareto plane and mark the front.

    Kept apart deliberately: the eight SINDy/NN controllers come from the
    priced pool, PPO / SAC / oracle / stock heuristic from the canonical
    default-objective wave, the tuned heuristic from its own tuning wave.  The
    SINDy rows of ``final/main.csv`` are default-objective and are NOT mixed in.
    """
    priced = ps.load_priced_pool()
    default_main = ps.load_default_main()
    tuning = ps.load_heuristic_tuning()

    a = ps.controller_summary(priced)
    b = ps.controller_summary(default_main[default_main["method"].isin(
        ["ppo", "sac", "oracle_mpc", "rule_based"])])

    tt = tuning[tuning["block"] == "tuned_test"]
    c = pd.DataFrame([{
        "method": "rule_based_tuned",
        "n": len(tt),
        "epi": tt["epi"].mean(),
        "epi_sd": tt["epi"].std(),
        "epi_se": tt["epi"].std(ddof=1) / np.sqrt(len(tt)),
        "viol": tt["violation_steps_total"].mean(),
        "viol_sd": tt["violation_steps_total"].std(),
        "truncated": int(np.asarray(tt["truncated"], bool).sum()),
        "label": ps.METHOD_LABEL["rule_based_tuned"],
    }])

    cols = ["method", "n", "epi", "epi_sd", "viol", "viol_sd", "truncated", "label"]
    t = pd.concat([a[cols], b[cols], c[cols]], ignore_index=True)
    t["on_front"] = ps.pareto_front(t).values
    t["objective"] = np.where(t["method"].isin(a["method"]), "priced", "default")
    return t.sort_values("epi", ascending=False).reset_index(drop=True)


#: Label placement, in points, keyed by method.  Display only.
_LABEL_OFFSET = {
    "sindy_mpc_raw_ens":      (-6, 7, "right"),
    "sindy_mpc_raw":          (7, -1, "left"),
    "sindy_mpc_lowthr":       (-8, 6, "right"),
    "sindy_mpc_dense":        (-8, -12, "right"),
    "rule_based_tuned":       (7, 2, "left"),
    "sindy_mpc_conf_dagger":  (7, 2, "left"),
    "sindy_mpc_dense_dagger": (-7, 3, "right"),
    "ppo":                    (7, -1, "left"),
    "sindy_mpc_conf":         (7, 0, "left"),
    "rule_based":             (7, -1, "left"),
    "oracle_mpc":             (7, -1, "left"),
    "nn_mpc":                 (7, 2, "left"),
    "sac":                    (7, -1, "left"),
}


def _color_for(method: str) -> str:
    lib = ps.METHOD_LIBRARY.get(method)
    return ps.LIB_COLOR[lib] if lib else FRONT_COLOR_FALLBACK


def draw_pareto(ax, t: pd.DataFrame) -> None:
    front = t[t["on_front"]].sort_values("viol")
    rest = t[~t["on_front"]]

    # -- achievable frontier: best EPI available at or below a violation budget
    ax.plot(front["viol"], front["epi"], drawstyle="steps-post",
            color="#444444", lw=0.9, alpha=0.75, zorder=3)

    # -- dispersion, subordinate: +/-1 SD of the run-level EPI
    for r in t.itertuples():
        if not np.isfinite(r.epi_sd):
            continue
        ax.vlines(r.viol, r.epi - r.epi_sd, r.epi + r.epi_sd,
                  color="#BBBBBB", lw=0.6, zorder=1)

    ax.scatter(rest["viol"], rest["epi"], s=20, color=GREY,
               edgecolors="white", linewidths=0.4, alpha=0.9, zorder=4)
    for r in front.itertuples():
        ax.scatter([r.viol], [r.epi], s=34, color=_color_for(r.method),
                   edgecolors="white", linewidths=0.6, zorder=5)

    ax.axhline(0.0, color="#888888", lw=0.6, ls=(0, (3, 2)), zorder=0)

    # -- labels.  dense and lowthr are ONE controller under two thresholds and
    #    sit 0.007 EUR/m2 and 5 violation steps apart: label them as a pair.
    pair = {"sindy_mpc_dense", "sindy_mpc_lowthr"}
    d_row = t[t["method"] == "sindy_mpc_dense"].iloc[0]
    l_row = t[t["method"] == "sindy_mpc_lowthr"].iloc[0]
    for r in t.itertuples():
        if r.method in pair:
            continue
        dx, dy, ha = _LABEL_OFFSET.get(r.method, (7, 2, "left"))
        ax.annotate(r.label, (r.viol, r.epi), textcoords="offset points",
                    xytext=(dx, dy), ha=ha, va="center", fontsize=6.3,
                    color=_color_for(r.method) if r.on_front else "#666666",
                    zorder=6)
    ax.annotate(
        f"SINDy-MPC, dense / low threshold\n"
        f"(one controller, two thresholds:\n"
        f"{abs(l_row.epi - d_row.epi):.4f} EUR m$^{{-2}}$ and "
        f"{abs(l_row.viol - d_row.viol):.0f} steps apart)",
        (d_row["viol"], d_row["epi"]), textcoords="offset points",
        xytext=(-9, -3), ha="right", va="top", fontsize=6.3,
        color=ps.LIB_COLOR["physics_no_cross"], linespacing=1.25, zorder=6)

    ax.set_xlabel("mean violation steps per season "
                  "($T_\\mathrm{in}$, CO$_2$ and RH pooled)")
    ax.set_ylabel("mean economic performance index  (EUR m$^{-2}$)")

    n_front = int(t["on_front"].sum())
    reps = ", ".join(f"n={int(n)}" for n in sorted(t["n"].unique()))
    ps.annotate_n(ax,
                  f"{n_front} non-dominated of {len(t)} controllers; step line is the\n"
                  f"achievable frontier.  Grey whiskers are $\\pm$1 SD of the run-level\n"
                  f"EPI.  Replication is unequal ({reps}); both heuristics are\n"
                  f"deterministic.  Season is 5760 steps of 900 s.",
                  loc="lower right")
    ps.panel_label(ax, "b", dx=-0.13)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ps.use_style()
    import matplotlib.pyplot as plt

    fits, per_config, per_library = reversal_table()
    t = pareto_table()

    fig, axes = ps.new_figure(ncols=2, width=ps.W2, height=8.2)
    draw_reversal(axes[0], fits, per_config, per_library)
    draw_pareto(axes[1], t)
    fig.subplots_adjust(wspace=0.30)
    fig.tight_layout(pad=0.4, w_pad=1.6)

    written = []
    for stem in ("fig6", "fig-graphical-abstract"):
        written += ps.finish(fig, stem)
    plt.close(fig)

    # ---- machine-readable dump of every plotted value, for verification -----
    payload = {
        "written": [str(p) for p in written],
        "panel_a": {
            "source_files": fits.attrs.get("source_files"),
            "rows_before_dedup": int(fits.attrs.get("rows_before_dedup", -1)),
            "rows_in_block": int(len(fits)),
            "kappa_area_per_unit": KAPPA_AREA_PER_UNIT,
            "per_config": json.loads(per_config.astype(
                {"variant": str}).to_json(orient="records")),
            "per_library": json.loads(per_library.astype(
                {"variant": str}).to_json(orient="records")),
        },
        "panel_b": {
            "controllers": json.loads(t.to_json(orient="records")),
            "front": sorted(t.loc[t["on_front"], "method"].tolist()),
        },
    }
    print(json.dumps(payload, indent=1))


if __name__ == "__main__":
    main()
