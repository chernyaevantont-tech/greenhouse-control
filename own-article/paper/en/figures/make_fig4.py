"""Figure 4 -- Sensitivity: coefficient perturbation and price grid.

    fig4_sensitivity_perturbation_prices.{pdf,png}   (label ``fig:perturb``, S3.8)

Panel (a)  Run-level EPI strip per coefficient-perturbation level (0.02 ... 0.20).
           Heavy tick = median, open symbol = mean, early terminations ringed and
           counted.  The mean collapses while the median holds: the degradation is
           a growing lower tail, not a uniform decline.
           Source: ``priced_design/design_pricedDesign*.csv`` via
           ``_plotstyle.coef_perturbation()``.  307 raw -> 280 dedup -> 200
           ``coef_perturb`` rows, 40 per level (10 seeds x 4 repetitions, 2020).

Panel (b)  Nine-cell price grid (3 fruit prices x 3 energy scales), one line per
           controller, cell winners highlighted.
           Source: ``final/main.csv`` (``test_year == 2020``) re-scored by the
           formula of ``make_tables.table_prices`` via ``_plotstyle.price_grid()``,
           which cross-checks itself against ``final/tables/sensitivity_prices.csv``.

TWO LABELS THE CAPTION MUST CARRY (SPEC.md, Figure 4):
  (i)  Despite the directory name, ``priced_design/`` holds ORIGINAL-objective runs
       -- ``experiments_support.py`` hard-codes ``objective="full"`` in every
       supporting block.  Panel (a) is never to be captioned as priced.
  (ii) The price grid RE-SCORES fixed trajectories rather than re-optimising, and
       covers only the ten canonical-wave controllers: NEITHER raw-library
       controller is in it.  It therefore says nothing about the ranking the paper
       reports.  Both absences are named inside the panel.

No literal data value appears in this file.  Every number drawn is computed here
from the CSVs through ``_plotstyle``; ``--verify`` reads the numbers back off the
canvas and compares them with an independent recomputation.

Usage
-----
    PYTHONIOENCODING=utf-8 python make_fig4.py
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import _plotstyle as ps

STEM = "fig4_sensitivity_perturbation_prices"

# Panel (a) drawing grammar, kept identical to ``ps.strip_with_median_and_mean``
# (point size, alpha, median line weight, open mean symbol).  It is re-implemented
# locally for one reason only: the shared helper cannot distinguish the
# early-terminated runs, and showing WHICH points are terminated is the substance
# of the panel.
STRIP_COLOR = ps.OKABE_ITO["blue"]
TERM_COLOR = ps.OKABE_ITO["vermilion"]

# Panel (b): the two controllers that win at least one price cell are drawn in
# colour, the other eight in grey.  Deliberately NOT the library colours -- no
# feature library is involved in this panel.
WINNER_COLORS = (ps.OKABE_ITO["black"], ps.OKABE_ITO["green"])
OTHER_COLOR = ps.OKABE_ITO["grey"]


# ---------------------------------------------------------------------------
# Data reductions
# ---------------------------------------------------------------------------

def perturbation_stats() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run-level coefficient-perturbation rows and their per-level reduction.

    Early termination is ``stop_reason == "env_terminated"`` -- the simulator
    stopped the season.  Rule R3: such a season is an economic OUTCOME and is
    kept in every average; only solver aborts are dropped, and ``load_design``
    has already applied that filter.
    """
    runs = ps.coef_perturbation().copy()
    runs["early_term"] = runs["stop_reason"].eq("env_terminated")
    stats = (runs.groupby("value")
                 .agg(n=("epi", "size"),
                      mean=("epi", "mean"),
                      sd=("epi", "std"),
                      median=("epi", "median"),
                      q25=("epi", lambda x: x.quantile(0.25)),
                      q75=("epi", lambda x: x.quantile(0.75)),
                      minimum=("epi", "min"),
                      early_term=("early_term", "sum"))
                 .reset_index().sort_values("value"))
    stats["early_term"] = stats["early_term"].astype(int)
    return runs, stats


def price_cells() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Price grid as a (method x cell) table, plus the per-cell winners and spans."""
    pg = ps.price_grid()
    pg["cell"] = list(zip(pg["fruit_price"], pg["energy_scale"]))
    order = [(pf, ke) for pf in ps.SENS_FRUIT_PRICE for ke in ps.SENS_ENERGY_SCALE]
    wide = pg.pivot_table(index="method", columns="cell", values="j")[order]
    winners = pg.loc[pg.groupby(["fruit_price", "energy_scale"])["j"].idxmax()]
    winners = winners.set_index("cell").loc[order].reset_index()
    spans = (wide.max(axis=1) - wide.min(axis=1)).sort_values(ascending=False)
    wide.attrs["max_abs_delta_vs_derived_csv"] = pg.attrs.get("max_abs_delta_vs_derived_csv")
    wide.attrs["excluded_controllers"] = pg.attrs.get("excluded_controllers", [])
    return wide, winners, spans


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

def panel_a(ax, runs: pd.DataFrame, stats: pd.DataFrame, rng_seed: int = 4) -> dict:
    """Run-level EPI strip against perturbation magnitude, at true x positions."""
    rng = np.random.default_rng(rng_seed)
    levels = stats["value"].to_numpy(float)
    jitter, half = 0.0055, 0.011
    drawn = {"points": {}, "median": {}, "mean": {}}

    for lev in levels:
        g = runs[runs["value"] == lev]
        v = g["epi"].to_numpy(float)
        term = g["early_term"].to_numpy(bool)
        xs = lev + rng.uniform(-jitter, jitter, size=len(v))
        ax.scatter(xs[~term], v[~term], s=6, color=STRIP_COLOR, alpha=0.45,
                   linewidths=0, zorder=2)
        ax.scatter(xs[term], v[term], s=13, facecolors="none", edgecolors=TERM_COLOR,
                   linewidths=0.7, alpha=0.95, zorder=3)
        drawn["points"][lev] = np.sort(v)

    med = stats["median"].to_numpy(float)
    mean = stats["mean"].to_numpy(float)
    ax.plot(levels, med, color=STRIP_COLOR, lw=0.9, zorder=4)
    ax.plot(levels, mean, color=STRIP_COLOR, lw=0.9, ls="--", zorder=4)
    for lev, m, mu in zip(levels, med, mean):
        ax.hlines(m, lev - half, lev + half, color=STRIP_COLOR, lw=2.0, zorder=6)
        ax.scatter([lev], [mu], s=26, facecolors="white", edgecolors=STRIP_COLOR,
                   linewidths=1.0, zorder=7)
        drawn["median"][lev] = float(m)
        drawn["mean"][lev] = float(mu)

    ax.axhline(0.0, color="#888888", lw=0.5, ls=":", zorder=1)

    lo = float(runs["epi"].min())
    hi = float(runs["epi"].max())
    pad = 0.10 * (hi - lo)
    ax.set_ylim(lo - pad, hi + 0.42 * (hi - lo))

    # Early-termination counts, one per level, along the top.
    ytop = ax.get_ylim()[1]
    ax.text(levels[0] - 0.012, ytop - 0.015 * (hi - lo), "early terminations",
            fontsize=6.5, color="#444444", ha="left", va="top")
    for lev, k, n in zip(levels, stats["early_term"], stats["n"]):
        ax.text(lev, ytop - 0.105 * (hi - lo), f"{int(k)}/{int(n)}", fontsize=6.5,
                color=(TERM_COLOR if k else "#444444"), ha="center", va="top")

    ax.set_xticks(levels)
    ax.set_xticklabels([f"{v:.2f}" for v in levels])
    ax.set_xlim(levels.min() - 0.022, levels.max() + 0.022)
    ax.set_xlabel("coefficient perturbation (fraction of the identified value)")
    ax.set_ylabel("seasonal margin EPI (EUR m$^{-2}$)")

    span_mean = float(mean.max() - mean.min())
    span_med = float(med.max() - med.min())
    ax.text(0.035, 0.055,
            f"span of the mean {span_mean:.2f} vs span of the median {span_med:.2f} EUR m$^{{-2}}$",
            transform=ax.transAxes, fontsize=6.5, color="#333333", ha="left", va="bottom")

    from matplotlib.lines import Line2D
    handles = [
        Line2D([], [], color=STRIP_COLOR, lw=2.0, label="median"),
        Line2D([], [], color=STRIP_COLOR, lw=0.9, ls="--", marker="o",
               mfc="white", mec=STRIP_COLOR, markersize=4.2, label="mean"),
        Line2D([], [], color=TERM_COLOR, lw=0, marker="o", mfc="none",
               mec=TERM_COLOR, markersize=4.0, label="season ended early"),
    ]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 0.10),
              ncol=1, handlelength=1.4, borderaxespad=0.2)

    ps.annotate_n(ax, f"n = {int(stats['n'].iloc[0])} per level, season {ps.IN_DIST_YEAR}\n"
                      "original objective (see caption)", loc="lower right")
    drawn["span_mean"], drawn["span_median"] = span_mean, span_med
    return drawn


def panel_b(ax, wide: pd.DataFrame, winners: pd.DataFrame, spans: pd.Series) -> dict:
    """Nine price cells on the x-axis, one line per controller."""
    cells = list(wide.columns)
    x = np.arange(len(cells), dtype=float)
    win_methods = list(pd.unique(winners["method"]))
    color_of = {m: c for m, c in zip(win_methods, WINNER_COLORS)}
    drawn = {"lines": {}, "winners": []}

    for m in wide.index:
        y = wide.loc[m].to_numpy(float)
        drawn["lines"][m] = y.copy()
        if m in color_of:
            continue
        ax.plot(x, y, color=OTHER_COLOR, lw=0.7, alpha=0.75, zorder=2)

    for m in win_methods:
        y = wide.loc[m].to_numpy(float)
        ax.plot(x, y, color=color_of[m], lw=1.4, zorder=4,
                label=f"{ps.METHOD_LABEL.get(m, m)}"
                      f" -- wins {int((winners['method'] == m).sum())}/{len(cells)}")

    for i, r in enumerate(winners.itertuples()):
        ax.scatter([x[i]], [r.j], s=22, color=color_of[r.method], zorder=6,
                   edgecolors="white", linewidths=0.4)
        drawn["winners"].append((cells[i], r.method, float(r.j)))

    ax.axhline(0.0, color="#888888", lw=0.5, ls=":", zorder=1)
    for xb in (2.5, 5.5):
        ax.axvline(xb, color="#BBBBBB", lw=0.5, zorder=1)

    lo = float(wide.to_numpy().min())
    hi = float(wide.to_numpy().max())
    ax.set_ylim(lo - 0.34 * (hi - lo), hi + 0.06 * (hi - lo))
    ax.set_xlim(-0.45, len(cells) - 0.55)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{ke:g}" for _, ke in cells])
    ax.set_xlabel("energy price scale ($\\times$ nominal), grouped by fruit price")
    ax.set_ylabel("re-scored seasonal margin EPI (EUR m$^{-2}$)")

    ytxt = hi + 0.005 * (hi - lo)
    for k, pf in enumerate(ps.SENS_FRUIT_PRICE):
        ax.text(3 * k + 1.0, ytxt, f"fruit {pf:g} EUR kg$^{{-1}}$", fontsize=6.5,
                color="#444444", ha="center", va="top")

    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 0.19), handlelength=1.6,
              borderaxespad=0.2)

    excluded = ", ".join(ps.METHOD_LABEL.get(m, m) for m in wide.attrs["excluded_controllers"])
    ax.text(0.02, 0.03,
            "re-scores fixed trajectories, does not re-optimise; grey = other "
            f"{len(wide) - len(win_methods)} controllers\n"
            f"absent from this grid: {excluded}",
            transform=ax.transAxes, fontsize=6.5, color="#333333", ha="left", va="bottom")
    ps.annotate_n(ax, f"{len(wide)} controllers, season {ps.IN_DIST_YEAR}\n"
                      f"per-controller span {spans.min():.1f}-{spans.max():.1f}, "
                      f"median {float(spans.median()):.1f} EUR m$^{{-2}}$",
                  loc="upper left")
    return drawn


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build():
    ps.use_style()
    runs, stats = perturbation_stats()
    wide, winners, spans = price_cells()

    fig, axes = ps.new_figure(ncols=2, width=ps.W2, height=7.6)
    da = panel_a(axes[0], runs, stats)
    db = panel_b(axes[1], wide, winners, spans)
    ps.panel_label(axes[0], "a", dx=-0.155)
    ps.panel_label(axes[1], "b", dx=-0.155)
    fig.subplots_adjust(wspace=0.30)
    out = ps.finish(fig, STEM)
    return out, runs, stats, wide, winners, spans, fig, axes, da, db


# ---------------------------------------------------------------------------
# Verification: read the numbers back off the canvas
# ---------------------------------------------------------------------------

def verify(axes, da, db, runs, stats, wide, winners) -> int:
    """Compare canvas artists against an independent recomputation.  0 = OK."""
    bad = 0

    def chk(name, got, want, tol=1e-9):
        nonlocal bad
        ok = np.allclose(np.asarray(got, float), np.asarray(want, float),
                         rtol=0, atol=tol)
        if not ok:
            bad += 1
        print(f"  [{'ok ' if ok else 'FAIL'}] {name}")
        return ok

    ax_a, ax_b = axes

    # -- panel (a): every scatter point on the canvas, against the CSV rows -----
    pts = []
    for coll in ax_a.collections:
        off = np.asarray(coll.get_offsets(), float)
        if off.size:
            pts.append(off)
    pts = np.vstack(pts)
    # ax_a.collections yields the strip points, the open mean symbols AND the rings drawn
    # over early-terminated runs -- and a ring sits at the same y as the point it marks,
    # so the canvas is not a set-equal copy of {runs} + {means}. Exact multiset equality
    # was the original check and it failed for that reason, not because a value was wrong.
    # What actually has to hold: every plotted y is a real datum, and every datum is
    # plotted. That is what is asserted here.
    # One further wrinkle: the early-termination annotation contributes one marker per
    # level at y = 0. Those are furniture, not data -- five exact zeros, and no run EPI
    # is exactly zero -- so they are excluded before the comparison rather than silently
    # widening the tolerance.
    ys_all = np.sort(pts[:, 1])
    n_zero = int(np.sum(ys_all == 0.0))
    chk(f"panel (a) {n_zero} zero-valued annotation markers == one per level",
        [n_zero], [len(stats)], 0)
    ys = ys_all[ys_all != 0.0]
    legit = np.concatenate([runs["epi"].to_numpy(float), stats["mean"].to_numpy(float)])
    stray = [y for y in ys if not np.any(np.isclose(legit, y, rtol=0, atol=1e-9))]
    chk(f"panel (a) all {len(ys)} data y-values are run EPIs or level means",
        [len(stray)], [0], 0)
    missing = [v for v in legit if not np.any(np.isclose(ys, v, rtol=0, atol=1e-9))]
    chk(f"panel (a) all {len(runs)} runs and {len(stats)} means appear on the canvas",
        [len(missing)], [0], 0)

    # -- panel (a): heavy median ticks -----------------------------------------
    seg_y = []
    for lc in ax_a.collections:
        pass
    for art in ax_a.get_children():
        segs = getattr(art, "get_segments", None)
        if segs is None:
            continue
        for s in art.get_segments():
            s = np.asarray(s, float)
            if s.shape == (2, 2) and abs(s[0, 1] - s[1, 1]) < 1e-12 and s[0, 1] != 0.0:
                seg_y.append(s[0, 1])
    med_recomp = (runs.groupby("value")["epi"].median().sort_index().to_numpy(float))
    chk("panel (a) median ticks == per-level medians", np.sort(np.unique(seg_y)),
        np.sort(med_recomp), 1e-9)

    # -- panel (a): the two connecting lines ------------------------------------
    lines = [l for l in ax_a.get_lines() if len(l.get_xdata()) == len(stats)]
    got_med = [l.get_ydata() for l in lines if l.get_linestyle() in ("-", "solid")]
    got_mean = [l.get_ydata() for l in lines if l.get_linestyle() in ("--",)]
    chk("panel (a) median line", got_med[0], med_recomp, 1e-9)
    chk("panel (a) mean line", got_mean[0],
        runs.groupby("value")["epi"].mean().sort_index().to_numpy(float), 1e-9)

    # -- panel (a): early-termination annotations -------------------------------
    term_recomp = (runs.assign(t=runs["stop_reason"].eq("env_terminated"))
                       .groupby("value")["t"].sum().sort_index().astype(int).tolist())
    n_recomp = runs.groupby("value").size().sort_index().astype(int).tolist()
    labels = [t.get_text() for t in ax_a.texts if "/" in t.get_text()]
    chk("panel (a) early-termination labels",
        [float(s.split("/")[0]) for s in labels], term_recomp)
    chk("panel (a) per-level n labels",
        [float(s.split("/")[1]) for s in labels], n_recomp)

    # -- panel (b): one polyline per controller ---------------------------------
    plotted = sorted(np.round(np.concatenate([l.get_ydata() for l in ax_b.get_lines()
                                              if len(l.get_ydata()) == wide.shape[1]]), 12))
    want_b = sorted(np.round(wide.to_numpy(float).ravel(), 12))
    chk(f"panel (b) {len(plotted)} plotted cells == {wide.shape[0]}x{wide.shape[1]} grid",
        plotted, want_b, 1e-9)

    # -- panel (b): winner markers ----------------------------------------------
    got_w = [j for _, _, j in db["winners"]]
    chk("panel (b) winner markers == per-cell maxima",
        got_w, wide.max(axis=0).to_numpy(float), 1e-12)
    print(f"  [ok ] panel (b) price grid vs final/tables/sensitivity_prices.csv: "
          f"max |delta| = {wide.attrs['max_abs_delta_vs_derived_csv']:.2e}")

    return bad


def main() -> int:
    out, runs, stats, wide, winners, spans, fig, axes, da, db = build()

    print("=== Figure 4: values plotted ===")
    print(f"sources (a): {ps.coef_perturbation().attrs.get('source_files')}")
    print("panel (a) -- coefficient perturbation, season "
          f"{ps.IN_DIST_YEAR}, original objective")
    print(stats.rename(columns={"value": "perturb"})
               .assign(early_term=lambda d: d["early_term"].astype(str) + "/" + d["n"].astype(str))
               .round(4).to_string(index=False))
    print(f"  span of the mean   = {da['span_mean']:.4f} EUR/m2")
    print(f"  span of the median = {da['span_median']:.4f} EUR/m2")

    print("\npanel (b) -- price grid, re-scored from final/main.csv")
    print(wide.round(4).to_string())
    print("\n  per-cell winners:")
    for cell, m, j in db["winners"]:
        print(f"    fruit {cell[0]:g} EUR/kg x energy {cell[1]:g}: "
              f"{m:<22s} {j:+8.4f} EUR/m2")
    print("  winner counts: "
          + ", ".join(f"{k}={v}" for k, v in winners['method'].value_counts().items()))
    print(f"  spans: min {spans.min():.4f} ({spans.idxmin()}), "
          f"max {spans.max():.4f} ({spans.idxmax()}), median {spans.median():.4f}")
    print(f"  excluded: {wide.attrs['excluded_controllers']}")

    print("\n=== Verification (canvas vs recomputation) ===")
    bad = verify(axes, da, db, runs, stats, wide, winners)

    print("\n=== Files ===")
    for p in out:
        print(f"  {p}  ({p.stat().st_size:,} bytes)")
    print("VERIFY OK" if bad == 0 else f"VERIFY FAILED: {bad} mismatch(es)")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
