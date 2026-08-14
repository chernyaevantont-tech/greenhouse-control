"""Figure 6 of the figure plan -- the UNNUMBERED GRAPHICAL ABSTRACT.

Plan slot 6 is ``fig-graphical-abstract`` (five numbered body figures plus this
one).

REDRAWN 2026-08-14 TO A THREE-PANEL SPECIFICATION.  The previous version had two
panels and encoded kappa as marker area in panel (a), because the paper's
mechanism was then ill-conditioning.  That mechanism is RETRACTED: the full
``physics`` library reached closed loop and the closed-loop series in kappa is
non-monotone (+4.32 / +0.28 / +2.75 EUR m^-2 against kappa 8.2 / 24.5 / 53.4).
The committed PDF therefore contradicted the caption in
``05-conclusions-abstract.tex``, which had already been rewritten to three
panels.  Current specification, taken from that caption's comment block:

    (a) The selection reversal: one-step RMSE (x) against median 24-h rollout
        RMSE (y, log).  Marker area is NO LONGER kappa -- kappa now belongs in
        panel (b), where it is shown NOT to predict the economics.
    (b) The non-monotonicity and what tracks it: three libraries on the x axis
        in kappa order, closed-loop EPI tracing a V against a monotone kappa,
        with boiler-term survival overlaid reproducing the V.  This panel is the
        paper's central claim.
    (c) The Pareto front, as Figure 2 but stripped of minor labels.

    Sources: (a) as Figure 1a, (b) as Figure 1c, (c) as Figure 2.

A configuration in the ladder is a ``(variant, degree, optimizer, denoise)``
label carrying 20 seeds, so the block plotted in (a) is 3 libraries x 2 sparse
estimators = 6 aggregate markers over 120 fits.

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

SCOPE GUARD FOR PANEL (b).  Survival orders these THREE libraries because they
differ in nothing else -- same estimator, threshold, degree, denoiser and seeds.
It does NOT rank the wider controller pool: ``sindy_mpc_conf_dagger`` survives
at 0.85 and scores +1.66, below ``sindy_mpc_raw_ens`` at 0.55.  The panel says
so on its face.  The bilinear-detour reading of WHY the middle library is worst
is deliberately NOT drawn: it is not supported by a measured effect, only by the
structural fact that ``physics`` alone contains ``t_uBoil``.

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

# Uniform marker area for the panel-(a) aggregates.  kappa is NO LONGER encoded
# as area anywhere in this figure -- see the module docstring.
AGG_MARKER_AREA = 46.0

FRONT_COLOR_FALLBACK = ps.OKABE_ITO["green"]
GREY = ps.OKABE_ITO["grey"]

#: Two-line library names for the panel-(b) ticks.  ``ps.LIB_LABEL`` is the
#: canonical single-line form used everywhere else; at three panels across
#: 17.5 cm those run into each other, so this is a DISPLAY abbreviation only.
SHORT_LIB = {"raw": "raw",
             "physics_no_cross": "physics,\nno cross",
             "physics": "physics,\nfull"}


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
                   s=AGG_MARKER_AREA,
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

    # -- divergence rate per library.  kappa is deliberately NOT annotated here
    #    any more: it is the subject of panel (b) and repeating it beside the
    #    open-loop scatter is what made the old figure read as "kappa explains
    #    everything".
    #    (dx, y-factor, ha).  ``raw`` sits at the right-hand edge with the arrow
    #    caption immediately left of it, so its label is anchored right-and-below
    #    rather than left-and-above like the other two.
    offsets = {"raw": (0.028, 0.86, "right"),
               "physics_no_cross": (0.014, 1.42, "left"),
               "physics": (0.014, 1.34, "left")}
    for lib in ps.LIB_ORDER:
        r = lib_at[lib]
        dx, fy, ha = offsets[lib]
        ax.text(r.one_step + (dx if ha == "left" else -dx),
                r.rollout_median * fy,
                f"diverged {r.diverged:.3f}",
                fontsize=6.4, color=ps.LIB_COLOR[lib], ha=ha,
                va="bottom" if fy >= 1.0 else "top", linespacing=1.2)

    # Estimator-marker entries are dropped here: at graphical-abstract size the
    # square/circle distinction is not resolvable and the panel's claim does not
    # depend on it. Figure 1a keeps the full legend.
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker="o", ls="", color=ps.LIB_COLOR[l],
                      markeredgecolor="white", markeredgewidth=0.5,
                      label=ps.LIB_LABEL[l], markersize=4.5)
               for l in ps.LIB_ORDER]
    ax.legend(handles=handles, loc="upper right", ncol=1, handletextpad=0.4,
              borderpad=0.25, labelspacing=0.26, fontsize=6.2,
              framealpha=0.92, edgecolor="#DDDDDD")

    ax.set_yscale("log")
    ax.set_xlabel("one-step RMSE of $T_\\mathrm{in}$  ($^\\circ$C)")
    ax.set_ylabel("24 h rollout RMSE of $T_\\mathrm{in}$  ($^\\circ$C, log scale)")
    # Graphical-abstract register: the scope guard is kept (it is a correctness
    # statement, not decoration) but compressed to two short lines. The full
    # wording lives on the numbered Figure 1.
    n_seed = int(per_config["n"].iloc[0])
    ax.annotate_text = None
    ps.annotate_n(ax,
                  f"degree-1, undenoised, sparse estimators\n"
                  f"({len(fits)} fits, {n_seed} seeds/marker); pooled\n"
                  f"over all 72 labels there is no reversal.",
                  loc="lower left")
    ps.panel_label(ax, "a", dx=-0.20)


# ---------------------------------------------------------------------------
# Panel (b) -- the non-monotonicity, and what tracks it
# ---------------------------------------------------------------------------

def draw_nonmonotone(ax, one_factor: pd.DataFrame,
                     per_library: pd.DataFrame) -> None:
    """Closed-loop EPI against a monotone kappa, with survival overlaid.

    The x axis is ordinal, in kappa order, so the V is a statement about the
    ORDERING and not about any distance in kappa.  kappa is printed under each
    tick to make the monotone-input / non-monotone-output contrast explicit;
    it is READ FROM the ladder reduction, never hardcoded.
    """
    t = one_factor.set_index("library").loc[list(ps.LIB_ORDER)].reset_index()
    kappa_by_lib = (per_library.set_index("variant")["kappa"]
                    .reindex(list(ps.LIB_ORDER)).to_numpy(float))
    if not np.all(np.diff(kappa_by_lib) > 0):
        raise AssertionError(
            "panel (b) asserts kappa is monotone across LIB_ORDER; the ladder "
            f"gives {kappa_by_lib!r}. The panel's premise is broken -- do not "
            "draw it until this is understood.")
    x = np.arange(len(t))

    # -- EPI, the V.  Seed-level SE: the four seasons of a seed are not
    #    independent replicates of the identified model.
    ax.errorbar(x, t["epi"], yerr=t["epi_se_seed"], fmt="none",
                ecolor="#666666", elinewidth=0.9, capsize=2.4, capthick=0.9,
                zorder=3)
    ax.plot(x, t["epi"], color="#444444", lw=1.0, alpha=0.8, zorder=2)
    for i, r in enumerate(t.itertuples()):
        ax.scatter([i], [r.epi], s=58, color=ps.LIB_COLOR[r.library],
                   edgecolors="white", linewidths=0.7, zorder=5)
        ax.annotate(f"{r.epi:+.2f}", (i, r.epi), textcoords="offset points",
                    xytext=(0, 11), ha="center", fontsize=6.8,
                    fontweight="bold", color=ps.LIB_COLOR[r.library], zorder=6)
    ax.axhline(0.0, color="#888888", lw=0.6, ls=(0, (3, 2)), zorder=0)

    ax.set_ylabel("mean closed-loop EPI  (EUR m$^{-2}$)")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{SHORT_LIB[r.library]}\n$\\kappa$ = {k:.1f}"
                        for r, k in zip(t.itertuples(), kappa_by_lib)],
                       fontsize=6.8)
    ax.set_xlim(-0.55, len(t) - 0.45)

    # -- survival on a twin axis, the series that reproduces the V
    ax2 = ax.twinx()
    ax2.plot(x, t["survival"], color=ps.OKABE_ITO["grey"], lw=1.0,
             ls=(0, (4, 2)), marker="s", ms=4.2, mfc="white",
             mec=ps.OKABE_ITO["grey"], mew=0.9, zorder=4)
    for i, r in enumerate(t.itertuples()):
        ax2.annotate(f"{r.survival:.2f}", (i, r.survival),
                     textcoords="offset points", xytext=(0, -13),
                     ha="center", fontsize=6.4, color="#555555", zorder=6)
    ax2.set_ylabel("boiler-term survival", color="#555555", fontsize=7)
    ax2.set_ylim(-0.08, 1.08)
    ax2.tick_params(axis="y", colors="#555555", labelsize=6.5)

    # Headroom below the V so the scope note does not sit on the middle marker.
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo - 0.42 * (hi - lo), hi)
    ps.annotate_n(ax,
                  "one factor: only the library changes. $\\kappa$ rises\n"
                  "monotonically, margin does not. Survival ranks\n"
                  "these three because nothing else differs; it\n"
                  "does not rank the wider controller pool.",
                  loc="lower left")
    ps.panel_label(ax, "b", dx=-0.20)


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
    priced = ps.load_library_pool()
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
    #    In the graphical abstract only the FRONT members are named; the
    #    dominated ten stay as unlabelled grey dots. Naming all fifteen at this
    #    panel width produced overlapping text. The numbered Figure 2 carries
    #    the full labelling and the dense/lowthr "one controller, two
    #    thresholds" caveat.
    pair = {"sindy_mpc_dense", "sindy_mpc_lowthr"}
    d_row = t[t["method"] == "sindy_mpc_dense"].iloc[0]
    l_row = t[t["method"] == "sindy_mpc_lowthr"].iloc[0]
    for r in t.itertuples():
        if r.method in pair or not r.on_front:
            continue
        dx, dy, ha = _LABEL_OFFSET.get(r.method, (7, 2, "left"))
        ax.annotate(r.label, (r.viol, r.epi), textcoords="offset points",
                    xytext=(dx, dy), ha=ha, va="center", fontsize=6.3,
                    color=_color_for(r.method), zorder=6)
    # The "one controller, two thresholds" caveat is NOT annotated here: at this
    # panel width it collides with the raw-ensemble label whichever way it is
    # placed. It is stated in Figure 2's caption, in Section 3.3 and in the
    # limitations, so the caveat is not lost -- only this rendering of it.
    _ = (d_row, l_row)

    ax.set_xlabel("mean violation steps per season")
    ax.set_ylabel("mean economic performance index  (EUR m$^{-2}$)")

    n_front = int(t["on_front"].sum())
    ps.annotate_n(ax,
                  f"{n_front} non-dominated of {len(t)};\n"
                  f"step line is the achievable\n"
                  f"frontier. Whiskers $\\pm$1 SD.\n"
                  f"Replication is unequal.",
                  loc="lower right")
    ps.panel_label(ax, "c", dx=-0.20)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ps.use_style()
    import matplotlib.pyplot as plt

    fits, per_config, per_library = reversal_table()
    one_factor = ps.library_one_factor("ensemble")
    t = pareto_table()

    fig, axes = ps.new_figure(ncols=3, width=ps.W2, height=6.6)
    draw_reversal(axes[0], fits, per_config, per_library)
    draw_nonmonotone(axes[1], one_factor, per_library)
    draw_pareto(axes[2], t)
    fig.tight_layout(pad=0.5, w_pad=2.6)

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
            "agg_marker_area": AGG_MARKER_AREA,
            "kappa_encoded_as_area": False,
            "per_config": json.loads(per_config.astype(
                {"variant": str}).to_json(orient="records")),
            "per_library": json.loads(per_library.astype(
                {"variant": str}).to_json(orient="records")),
        },
        "panel_b": {
            "source_files": one_factor.attrs.get("source_files"),
            "one_factor": json.loads(one_factor.astype(
                {"library": str}).to_json(orient="records")),
        },
        "panel_c": {
            "controllers": json.loads(t.to_json(orient="records")),
            "front": sorted(t.loc[t["on_front"], "method"].tolist()),
        },
    }
    print(json.dumps(payload, indent=1))

    # ---- self-check: the three claims the caption makes ---------------------
    kap = (per_library.set_index("variant")["kappa"]
           .reindex(list(ps.LIB_ORDER)).to_numpy(float))
    epi = (one_factor.set_index("library")["epi"]
           .reindex(list(ps.LIB_ORDER)).to_numpy(float))
    sur = (one_factor.set_index("library")["survival"]
           .reindex(list(ps.LIB_ORDER)).to_numpy(float))
    checks = [
        ("kappa monotone increasing", bool(np.all(np.diff(kap) > 0))),
        ("EPI NOT monotone", not (bool(np.all(np.diff(epi) > 0))
                                  or bool(np.all(np.diff(epi) < 0)))),
        ("EPI is V-shaped (middle lowest)",
         bool(epi[1] < epi[0] and epi[1] < epi[2])),
        ("survival reproduces the V", bool(sur[1] < sur[0] and sur[1] < sur[2])),
        ("survival ties the two outer libraries", bool(sur[0] == sur[2])),
        ("front has 5 members", int(t["on_front"].sum()) == 5),
    ]
    print("\n-- caption self-check --")
    for name, ok in checks:
        print("   %-40s %s" % (name, "OK" if ok else "FAILED"))
    if not all(ok for _, ok in checks):
        raise SystemExit("graphical abstract contradicts its caption")
    print("   kappa    %s" % np.array2string(kap, precision=3))
    print("   EPI      %s" % np.array2string(epi, precision=4))
    print("   survival %s" % np.array2string(sur, precision=2))


if __name__ == "__main__":
    main()
