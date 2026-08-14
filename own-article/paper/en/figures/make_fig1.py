"""Figure 1 -- Selection reversal and conditioning.

Spec: ``figures/SPEC.md``, section "Figure 1".  Label ``fig:kappa``, lives in
Section 3.1, 17.5 cm wide, three panels.

  (a)  One-step RMSE of ``t_in`` (linear x) against 24-h rollout RMSE (log y),
       one marker per fit.  Colour = feature library, marker = sparse
       estimator, OPEN FACE = fails the 0.05 divergence gate.  Median + IQR
       cross per library.  This is the reversal as raw data.
  (b)  kappa (log x) against one-step RMSE (left y, mean +- SD) and median
       24-h rollout RMSE (right y, log, median + IQR).  The twin axis is
       required by the spec: the point of the panel is that the two criteria
       move in opposite directions over the same three libraries.
  (c)  Four-season mean closed-loop EPI of the two libraries that reached
       closed loop, SD whiskers plus the run-level strip.  The ``physics``
       library was never run in closed loop; its slot is drawn empty and
       hatched.  NOTHING IS IMPUTED THERE.

Every number drawn is computed in this file from the CSVs under
``own-article/regen/results`` through ``_plotstyle``; none is written as a
literal.  After drawing, the script reads the values back out of the
matplotlib artists and writes them to ``fig1_values.json`` so an independent
script can check what was actually rendered rather than what was intended.

Run:
    PYTHONIOENCODING=utf-8 python make_fig1.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import _plotstyle as ps


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

#: The two controllers that reached closed loop, and the library each was
#: identified on (``_plotstyle.METHOD_LIBRARY``).  ``physics`` has no entry --
#: that is the point of the third slot in panel (c).
CLOSED_LOOP_METHODS = ("sindy_mpc_raw_ens", "sindy_mpc_lowthr")


def ladder_block() -> pd.DataFrame:
    """Degree-1, undenoised, sparse-estimator block: 120 rows, 40 per library.

    SCOPE.  The reversal is stated over this block only (2 of 72 labels per
    library).  Pooled over all 72 labels the raw library has the best mean
    one-step RMSE and there is no reversal -- see the loader docstring.
    """
    return ps.load_ladder(degree=1, denoise="none",
                          optimizers=("stlsq", "ensemble"))


def closed_loop_table() -> pd.DataFrame:
    """Per-controller four-season EPI from the priced pool, with dispersion.

    ``epi_sd_between_season`` is the SD of the four season means; comparing it
    with ``epi_sd`` shows how much of the spread is season rather than seed.
    """
    pool = ps.load_priced_pool()
    sub = pool[pool["method"].isin(CLOSED_LOOP_METHODS)]
    rows = []
    for m in CLOSED_LOOP_METHODS:
        g = sub[sub["method"] == m]
        season_means = g.groupby("test_year")["epi"].mean()
        rows.append({
            "method": m,
            "library": ps.METHOD_LIBRARY[m],
            "label": ps.METHOD_LABEL[m],
            "n": int(len(g)),
            "n_seeds": int(g["seed"].nunique()),
            "n_years": int(g["test_year"].nunique()),
            "epi": float(g["epi"].mean()),
            "epi_sd": float(g["epi"].std()),
            "epi_median": float(g["epi"].median()),
            "epi_min": float(g["epi"].min()),
            "epi_max": float(g["epi"].max()),
            "epi_sd_between_season": float(season_means.std()),
            "epi_values": g["epi"].to_numpy(float),
        })
    t = pd.DataFrame(rows)
    t.attrs["rows_before_dedup"] = pool.attrs["rows_before_dedup"]
    t.attrs["rows_after_dedup"] = pool.attrs["rows_after_dedup"]
    t.attrs["rows_usable"] = len(pool)
    return t


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

def panel_a(ax, lad: pd.DataFrame) -> dict:
    """Scatter of the two prediction criteria, one marker per fit."""
    ps.scatter_by_library(ax, lad, "one_step_rmse_t_in", "rollout_rmse_t_in",
                          legend=False)

    # Median + IQR cross per library, computed from the same 40 rows.
    crosses = {}
    for lib in ps.LIB_ORDER:
        s = lad[lad["variant"] == lib]
        if not len(s):
            continue
        x, y = s["one_step_rmse_t_in"], s["rollout_rmse_t_in"]
        mx, my = float(x.median()), float(y.median())
        xq = (float(x.quantile(0.25)), float(x.quantile(0.75)))
        yq = (float(y.quantile(0.25)), float(y.quantile(0.75)))
        c = ps.LIB_COLOR[lib]
        ax.hlines(my, xq[0], xq[1], color=c, lw=1.8, zorder=6)
        ax.vlines(mx, yq[0], yq[1], color=c, lw=1.8, zorder=6)
        ax.plot([mx], [my], marker="|", ms=0, color=c)
        crosses[lib] = {"n": int(len(s)), "median_one_step": mx,
                        "median_rollout": my, "one_step_iqr": xq,
                        "rollout_iqr": yq}

    ax.set_yscale("log")
    ax.set_xlabel(r"one-step RMSE of $T_{\mathrm{in}}$ ($^\circ$C)")
    ax.set_ylabel(r"24-h rollout RMSE of $T_{\mathrm{in}}$ ($^\circ$C, log)")

    from matplotlib.lines import Line2D
    lib_handles = [Line2D([], [], marker="o", ls="", color=ps.LIB_COLOR[l],
                          label=ps.LIB_LABEL[l], markersize=4)
                   for l in ps.LIB_ORDER]
    leg1 = ax.legend(handles=lib_handles, loc="upper left",
                     bbox_to_anchor=(-0.02, 1.02), handletextpad=0.4,
                     borderaxespad=0.0, labelspacing=0.25)
    ax.add_artist(leg1)

    grey = ps.OKABE_ITO["grey"]
    n_fail = int((~lad["passes_gate"].astype(bool)).sum())
    mark_handles = [
        Line2D([], [], marker="o", ls="", mfc=grey, mec=grey, ms=4,
               label="STLSQ"),
        Line2D([], [], marker="s", ls="", mfc=grey, mec=grey, ms=4,
               label="ensemble"),
        Line2D([], [], marker="o", ls="", mfc="none", mec=grey, ms=4,
               label=f"fails 0.05 gate ({n_fail}/{len(lad)})"),
    ]
    ax.legend(handles=mark_handles, loc="lower right", handletextpad=0.4,
              borderaxespad=0.2, labelspacing=0.25)

    return {"crosses": crosses, "n_rows": int(len(lad)), "n_gate_fail": n_fail}


def panel_b(ax, lad: pd.DataFrame) -> dict:
    """Conditioning against both criteria, on twin axes (spec-mandated)."""
    g = ps.ladder_summary(lad)
    ax2 = ax.twinx()
    ax2.grid(False)

    k = g["kappa"].to_numpy(float)
    k_sd = g["kappa_sd"].to_numpy(float)
    os_mean = g["one_step"].to_numpy(float)
    os_sd = g["one_step_sd"].to_numpy(float)
    ro_med = g["rollout_median"].to_numpy(float)
    ro_lo = ro_med - g["rollout_q25"].to_numpy(float)
    ro_hi = g["rollout_q75"].to_numpy(float) - ro_med

    dark = "#333333"
    ax.errorbar(k, os_mean, yerr=os_sd, xerr=k_sd, color=dark, lw=1.1,
                ls="-", marker="none", capsize=2.0, elinewidth=0.7, zorder=3)
    ax2.errorbar(k, ro_med, yerr=np.vstack([ro_lo, ro_hi]), color=dark,
                 lw=1.1, ls="--", marker="none", capsize=2.0, elinewidth=0.7,
                 zorder=3)
    for i, lib in enumerate(g["variant"]):
        c = ps.LIB_COLOR[str(lib)]
        ax.plot([k[i]], [os_mean[i]], marker="o", ms=5.5, mfc=c, mec=dark,
                mew=0.6, zorder=6, clip_on=False)
        ax2.plot([k[i]], [ro_med[i]], marker="s", ms=5.5, mfc=c, mec=dark,
                 mew=0.6, zorder=6, clip_on=False)
        ax.annotate(rf"$\kappa={k[i]:.2f}$", xy=(k[i], os_mean[i]),
                    xytext=(0, -11), textcoords="offset points",
                    ha="center", va="top", fontsize=6.5, color=dark)

    ax.set_xscale("log")
    ax2.set_yscale("log")
    ax.set_xlabel(r"condition number $\kappa$ of the feature matrix (log)")
    ax.set_ylabel(r"one-step RMSE ($^\circ$C), mean $\pm$ SD")
    ax2.set_ylabel(r"median 24-h rollout RMSE ($^\circ$C, log)")
    ax.set_xticks([8, 16, 32, 64])
    ax.get_xaxis().set_major_formatter(
        __import__("matplotlib").ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xlim(6.5, 72)
    lo, hi = float(os_mean.min() - os_sd.max()), float(os_mean.max() + os_sd.max())
    pad = 0.35 * (hi - lo)
    ax.set_ylim(lo - pad, hi + pad)
    ax2.set_ylim(1.6, 60.0)

    from matplotlib.lines import Line2D
    ax.legend(handles=[
        Line2D([], [], color=dark, ls="-", marker="o", mfc=ps.OKABE_ITO["grey"],
               mec=dark, ms=5, label="one-step (left)"),
        Line2D([], [], color=dark, ls="--", marker="s", mfc=ps.OKABE_ITO["grey"],
               mec=dark, ms=5, label="rollout median (right)"),
    ], loc="upper center", bbox_to_anchor=(0.5, 1.02), handletextpad=0.4,
        labelspacing=0.25)

    return {"variant": [str(v) for v in g["variant"]],
            "n": [int(v) for v in g["n"]],
            "kappa": k.tolist(), "kappa_sd": k_sd.tolist(),
            "one_step_mean": os_mean.tolist(), "one_step_sd": os_sd.tolist(),
            "rollout_median": ro_med.tolist(),
            "rollout_q25": g["rollout_q25"].astype(float).tolist(),
            "rollout_q75": g["rollout_q75"].astype(float).tolist(),
            "diverged_frac_mean": g["diverged"].astype(float).tolist()}


def panel_c(ax, cl: pd.DataFrame) -> dict:
    """Closed-loop economic outcome of the libraries that got that far."""
    from matplotlib.patches import Rectangle

    order = list(ps.LIB_ORDER)
    pos = {lib: i for i, lib in enumerate(order)}
    rng = np.random.default_rng(0)
    out = {"bars": [], "not_evaluated": None}

    for r in cl.itertuples():
        i = pos[r.library]
        c = ps.LIB_COLOR[r.library]
        ax.bar([i], [r.epi], width=0.62, color=c, alpha=0.85,
               edgecolor=c, linewidth=0.6, zorder=2)
        ax.errorbar([i], [r.epi], yerr=[r.epi_sd], color="#333333", lw=0.9,
                    capsize=2.5, zorder=5)
        v = np.asarray(r.epi_values, float)
        ax.scatter(i + rng.uniform(-0.17, 0.17, size=len(v)), v, s=3.2,
                   color="#333333", alpha=0.35, linewidths=0, zorder=4)
        ax.annotate(f"{r.epi:+.2f}", xy=(i, r.epi + r.epi_sd),
                    xytext=(0, 3), textcoords="offset points", ha="center",
                    va="bottom", fontsize=7)
        out["bars"].append({"library": r.library, "method": r.method,
                            "n": r.n, "epi": r.epi, "epi_sd": r.epi_sd,
                            "epi_min": r.epi_min, "epi_max": r.epi_max,
                            "epi_sd_between_season": r.epi_sd_between_season})

    ax.axhline(0.0, color="#666666", lw=0.6, zorder=1)
    lo = min(float(np.min(np.concatenate([np.asarray(r.epi_values, float)
                                          for r in cl.itertuples()]))), 0.0)
    hi = float(max(r.epi + r.epi_sd for r in cl.itertuples()))
    span = hi - lo
    ax.set_ylim(lo - 0.10 * span, hi + 0.26 * span)

    i = pos["physics"]
    y0, y1 = ax.get_ylim()
    ax.add_patch(Rectangle((i - 0.31, y0), 0.62, y1 - y0, facecolor="none",
                           edgecolor=ps.LIB_COLOR["physics"], hatch="////",
                           linewidth=0.7, alpha=0.75, zorder=2))
    ax.text(i, (y0 + y1) / 2.0, "not evaluated\nin closed loop", rotation=90,
            ha="center", va="center", fontsize=6.5,
            color=ps.LIB_COLOR["physics"])
    out["not_evaluated"] = "physics"

    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(["raw", "physics,\nno cross", "physics"])
    ax.set_xlim(-0.6, len(order) - 0.4)
    ax.set_ylabel(r"four-season mean EPI (EUR m$^{-2}$)")
    ax.set_xlabel("feature library")

    n = int(cl["n"].iloc[0])
    seeds, years = int(cl["n_seeds"].iloc[0]), int(cl["n_years"].iloc[0])
    ps.annotate_n(ax, f"n = {n} ({seeds} seeds $\\times$ {years} seasons)\n"
                      "whisker = SD, dots = runs", loc="lower left")
    return out


# ---------------------------------------------------------------------------
# Read-back: what the artists actually carry
# ---------------------------------------------------------------------------

def readback(ax_a, ax_b, ax_c) -> dict:
    """Pull the drawn geometry back out of the axes.

    This is deliberately not a copy of the numbers passed in: it inspects the
    artists, so the sidecar reflects what is on the page.
    """
    pts = []
    for coll in ax_a.collections:
        off = np.asarray(coll.get_offsets(), float)
        if off.size:
            pts.append(off.reshape(-1, 2))
    scat = np.vstack(pts) if pts else np.empty((0, 2))

    lines_b = []
    for a in (ax_b, ax_b.figure.axes[-1]):
        for ln in a.get_lines():
            xd, yd = np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float)
            if len(xd) == 3:                      # the three-library series
                lines_b.append({"x": xd.tolist(), "y": yd.tolist(),
                                "ls": ln.get_linestyle()})

    bars = [{"x": float(p.get_x() + p.get_width() / 2.0),
             "height": float(p.get_height())}
            for p in ax_c.patches if hasattr(p, "get_height")
            and p.get_height() not in (None,) and p.get_hatch() is None]

    return {
        "panel_a_scatter_n": int(len(scat)),
        "panel_a_x_range": [float(scat[:, 0].min()), float(scat[:, 0].max())],
        "panel_a_y_range": [float(scat[:, 1].min()), float(scat[:, 1].max())],
        "panel_b_series": lines_b,
        "panel_c_bars": bars,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ps.use_style()
    import matplotlib.pyplot as plt

    lad = ladder_block()
    cl = closed_loop_table()

    fig = plt.figure(figsize=(ps.W2, 6.4 * ps.CM))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.22, 1.18, 0.72],
                          wspace=0.60, left=0.065, right=0.945,
                          bottom=0.185, top=0.925)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    a = panel_a(ax_a, lad)
    b = panel_b(ax_b, lad)
    c = panel_c(ax_c, cl)

    ps.panel_label(ax_a, "a", dx=-0.20)
    ps.panel_label(ax_b, "b", dx=-0.22)
    ps.panel_label(ax_c, "c", dx=-0.42)

    stems = ["fig1_selection_and_conditioning", "fig1"]
    written = []
    for stem in stems:
        written += ps.finish(fig, stem)
    plt.close(fig)

    values = {
        "figure": "Figure 1 -- selection reversal and conditioning",
        "label": "fig:kappa",
        "sources": {
            "ladder": lad.attrs.get("source_files"),
            "ladder_rows_before_dedup": int(lad.attrs.get("rows_before_dedup", -1)),
            "ladder_rows_in_block": int(len(lad)),
            "priced_rows_before_dedup": int(cl.attrs["rows_before_dedup"]),
            "priced_rows_after_dedup": int(cl.attrs["rows_after_dedup"]),
            "priced_rows_usable": int(cl.attrs["rows_usable"]),
        },
        "panel_a": a,
        "panel_b": b,
        "panel_c": c,
        "readback": readback(ax_a, ax_b, ax_c),
        "outputs": [str(p) for p in written],
    }
    side = ps.FIGDIR / "fig1_values.json"
    side.write_text(json.dumps(values, indent=2, default=float), encoding="utf-8")

    print(f"ladder block : {lad.attrs.get('rows_before_dedup')} raw rows -> "
          f"{len(lad)} in the degree-1 undenoised sparse block")
    for i, lib in enumerate(b["variant"]):
        print(f"  {lib:<17} n={b['n'][i]:<3} kappa={b['kappa'][i]:8.4f}  "
              f"one-step={b['one_step_mean'][i]:.4f} degC  "
              f"rollout median={b['rollout_median'][i]:8.4f} degC  "
              f"diverged={b['diverged_frac_mean'][i]:.4f}")
    print(f"  gate failures drawn open: {a['n_gate_fail']} of {a['n_rows']}")
    print(f"priced pool  : {cl.attrs['rows_before_dedup']} raw -> "
          f"{cl.attrs['rows_after_dedup']} dedup -> {cl.attrs['rows_usable']} usable")
    for r in c["bars"]:
        print(f"  {r['method']:<18} ({r['library']:<16}) n={r['n']}  "
              f"EPI={r['epi']:+.4f} EUR/m2  SD={r['epi_sd']:.4f}  "
              f"(between-season SD {r['epi_sd_between_season']:.4f})")
    print("  physics: no closed-loop run exists -- slot drawn empty and hatched")
    print("wrote " + ", ".join(str(p) for p in written))
    print(f"wrote {side}")


if __name__ == "__main__":
    main()
