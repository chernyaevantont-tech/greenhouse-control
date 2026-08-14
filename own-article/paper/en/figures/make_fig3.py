"""Figure 3 -- Sparsity sweep, boiler-term survival, and the knock-in.

Spec: ``figures/SPEC.md``, section "Figure 3".  Label ``fig:lambda``, lives in
Section 3.5, 17.5 cm wide.  Referenced from Section 3.5 and, as "Figure 3c",
from Section 4.1.

This is the figure that now carries the paper's MECHANISM.  Since the full
``physics`` library reached closed loop (2026-08-13) the closed-loop outcome is
known to be non-monotone in the condition number, so conditioning cannot be the
mechanism; what the closed loop tracks is whether the actuator pathway survives
thresholding.  Panels (a) and (b) show the sparsity threshold destroying that
pathway, and panel (c) is the controlled single-coefficient intervention that
makes the link causal rather than correlational.

  (a)  Mean EPI against the sparsity threshold lambda, one curve per stage cost
       (priced, default), +-1 SD shaded.  13 levels, 20 replicates each,
       season 2020 only.
  (b)  Boiler-term survival against lambda on the same axis -- the collapse
       between lambda = 0.03 and 0.06 that panel (a) is reacting to -- with the
       survival of every closed-loop controller marked on the right, so the
       reader can place each controller of the main table on this axis.
  (c)  The knock-in: EPI of the confirmatory fit with the boiler coefficient
       restored, minus the same replicate's baseline.  Both stage costs, lines
       joining the same seed, IQR box, MEDIAN AS A HEAVY TICK and mean as an
       open symbol.

RETRACTION GUARD (REVISION_LOG G-6).  The knock-in median under the defective
objective, +3.05, is a SUPERSEDED magnitude.  It may appear only beside its
priced replacement, +0.21, which this panel draws next to it.  Under the priced
objective the mean is nine times the median, so plotting the mean alone would
restate the retracted number in disguise: the heavy median tick must dominate.

Every number drawn is computed here from the CSVs under
``own-article/regen/results`` through ``_plotstyle``; none is a literal.  After
drawing, the values are read back OUT OF THE MATPLOTLIB ARTISTS into
``fig3_values.json``, and :func:`selfcheck` re-derives them from the raw CSVs
along an independent code path and compares.

Run:
    PYTHONIOENCODING=utf-8 python make_fig3.py
"""

from __future__ import annotations

import glob
import json
import sys

import numpy as np
import pandas as pd
from scipy import stats

import _plotstyle as ps

OBJECTIVES = ("priced", "default")
OBJ_COLOR = {"priced": "#000000", "default": "#999999"}
OBJ_STYLE = {"priced": "-", "default": "--"}
OBJ_LABEL = {"priced": "priced stage cost", "default": "default stage cost"}
RECIPE_LAMBDA = 0.05        # regen_config.CONFIRMATORY threshold, the Figure 1 recipe
SEASON = ps.IN_DIST_YEAR    # the mechanism block is season 2020 only


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def sweeps() -> dict:
    """Lambda sweep per objective: 13 levels, n = 20, season 2020."""
    return {obj: ps.lambda_sweep(obj, SEASON) for obj in OBJECTIVES}


def knocks() -> dict:
    """Per-seed knock-in / knock-out deltas per objective, paired on the seed."""
    return {obj: ps.knock_effects(obj, SEASON) for obj in OBJECTIVES}


def knock_stats(k: dict) -> dict:
    """Wilcoxon signed-rank per effect and objective, plus a Holm adjustment.

    THE FAMILY MATTERS AND MUST BE NAMED.  These four tests -- knock-in and
    knock-out under each stage cost -- are the family adjusted over.  The same
    raw p becomes 6.4e-4 in a family of two and 1.3e-3 in this family of four.
    """
    raw = {}
    for obj in OBJECTIVES:
        for eff in ("knockin", "knockout"):
            v = k[obj][eff].to_numpy(float)
            try:
                raw[(obj, eff)] = float(stats.wilcoxon(v).pvalue)
            except ValueError:                              # all-zero differences
                raw[(obj, eff)] = float("nan")
    adj = ps.holm(raw)
    return {"raw": raw, "holm": adj, "family": sorted(f"{o}/{e}" for o, e in raw)}


def controller_survival() -> pd.DataFrame:
    """Boiler-term survival of every closed-loop controller, priced objective.

    Pools :func:`_plotstyle.load_library_pool`, so the two ``physics``-library
    controllers measured on 2026-08-13 are included alongside the eight of the
    main priced comparison.  Survival is a property of the SEED (one fit per
    seed), so it is computed over seeds, not over the 4x seasons.
    """
    pool = ps.load_library_pool()
    rows = []
    for method, g in pool.groupby("method"):
        per_seed = g.groupby("seed")["boiler_alive"].first()
        rows.append({"method": method, "label": ps.METHOD_LABEL.get(method, method),
                     "library": ps.METHOD_LIBRARY.get(method),
                     "survival": float(per_seed.mean()), "n_seeds": int(len(per_seed)),
                     "n_runs": int(len(g)), "epi": float(g["epi"].mean())})
    return pd.DataFrame(rows).sort_values(["survival", "method"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

def panel_a(ax, sw: dict) -> dict:
    """Mean EPI against lambda, both stage costs, +-1 SD."""
    out = {"objectives": {}}
    for obj in OBJECTIVES:
        s = sw[obj]
        lam = s["lam"].to_numpy(float)
        idx = np.arange(len(lam), dtype=float)
        mu, sd = s["epi_mean"].to_numpy(float), s["epi_sd"].to_numpy(float)
        c = OBJ_COLOR[obj]
        band = ax.fill_between(idx, mu - sd, mu + sd, color=c, alpha=0.13,
                               linewidth=0, zorder=2)
        band.set_gid(f"a:band:{obj}")
        ln, = ax.plot(idx, mu, ls=OBJ_STYLE[obj], color=c, lw=1.2, marker="o",
                      ms=3.0, mfc=c, mec=c, zorder=4, label=OBJ_LABEL[obj])
        ln.set_gid(f"a:mean:{obj}")
        out["objectives"][obj] = {
            "lam": lam.tolist(), "epi_mean": mu.tolist(), "epi_sd": sd.tolist(),
            "epi_median": s["epi_median"].astype(float).tolist(),
            "n": s["n"].astype(int).tolist(),
        }

    _lambda_axis(ax, sw[OBJECTIVES[0]]["lam"].to_numpy(float))
    ax.set_ylim(-4.6, 9.6)
    ax.set_ylabel(r"mean EPI (EUR m$^{-2}$), $\pm$1 SD")
    ax.set_title("economics against the threshold", fontsize=8, pad=4)
    ax.legend(loc="lower left", fontsize=6.5, labelspacing=0.25,
              handletextpad=0.5, borderaxespad=0.3)
    ps.annotate_n(ax, f"season {SEASON} only, $n=20$ per level\n"
                      "levels evenly spaced, not to scale", loc="upper right")
    return out


def _lambda_axis(ax, lam: np.ndarray) -> None:
    """Shared x-axis of panels (a) and (b).

    The 13 levels are drawn EVENLY SPACED, not on a log scale.  On a log axis
    four of the six decades carry a flat plateau and the collapse -- 0.03 to
    0.06, which is the whole point -- is squeezed into two millimetres.  The
    axis is labelled with every level, so nothing is hidden; the price is that
    horizontal distance is ordinal, which the label states.
    """
    n = len(lam)
    lo = float(np.searchsorted(lam, 0.03))
    hi = float(np.searchsorted(lam, 0.06))
    ax.axvspan(lo, hi, color=ps.OKABE_ITO["yellow"], alpha=0.25, zorder=0)
    ax.axvline(float(np.searchsorted(lam, RECIPE_LAMBDA)), color="#555555",
               ls=":", lw=0.8, zorder=1)
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_xticks(np.arange(n))
    ax.set_xticklabels([f"{v:g}" for v in lam], rotation=90, fontsize=5.8)
    ax.set_xlabel(r"sparsity threshold $\lambda$")


def panel_b(ax, ax_strip, sw: dict, cs: pd.DataFrame) -> dict:
    """Boiler-term survival against lambda, and where each controller sits."""
    out = {"objectives": {}, "controllers": []}
    for obj in OBJECTIVES:
        s = sw[obj]
        lam, sv = s["lam"].to_numpy(float), s["survival"].to_numpy(float)
        idx = np.arange(len(lam), dtype=float)
        c = OBJ_COLOR[obj]
        ln, = ax.plot(idx, sv, ls=OBJ_STYLE[obj], color=c, lw=1.2, marker="o",
                      ms=3.0, mfc=c, mec=c, zorder=4, label=OBJ_LABEL[obj])
        ln.set_gid(f"b:surv:{obj}")
        out["objectives"][obj] = {"lam": lam.tolist(), "survival": sv.tolist(),
                                  "n": s["n"].astype(int).tolist()}

    lam0 = sw[OBJECTIVES[0]]["lam"].to_numpy(float)
    _lambda_axis(ax, lam0)
    ax.set_ylim(-0.06, 1.16)
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("boiler term kept, fraction of fits")
    ax.set_title("what the threshold destroys", fontsize=8, pad=4)
    mid = 0.5 * (np.searchsorted(lam0, 0.03) + np.searchsorted(lam0, 0.06))
    ax.annotate("collapse", xy=(mid, 1.10), ha="center", va="center",
                fontsize=6.6, color="#7A6000")
    ax.legend(loc="lower left", fontsize=6.5, labelspacing=0.25,
              handletextpad=0.5, borderaxespad=0.3)

    # --- right-hand strip: the closed-loop controllers on the same y axis ---
    ax_strip.set_ylim(*ax.get_ylim())
    ax_strip.set_xlim(0.0, 1.0)
    ax_strip.set_xticks([])
    ax_strip.set_yticks([])
    ax_strip.grid(False)
    for side in ("left", "bottom"):
        ax_strip.spines[side].set_visible(False)

    # Group by (survival, library) so a tick never mixes two libraries and the
    # fixed library colours of Figure 1 keep their meaning here.
    groups: dict[tuple, list] = {}
    for r in cs.itertuples():
        groups.setdefault((round(r.survival, 4), r.library or "none"), []).append(r)
    ordered = sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1]))

    # Push the label blocks apart just enough that none overlaps, then draw a
    # leader from the tick (at its true survival) to the displaced label.  The
    # TICK never moves: only the text does.
    line_h = 0.055
    heights = [line_h * len(rows) for _, rows in ordered]
    ys = [sv for (sv, _), _ in ordered]
    for i in range(1, len(ys)):
        need = 0.5 * (heights[i] + heights[i - 1]) + 0.014
        ys[i] = max(ys[i], ys[i - 1] + need)
    over = ys[-1] + 0.5 * heights[-1] - 1.14
    if over > 0:
        ys = [y - over for y in ys]

    for ((sv, lib), rows), ylab in zip(ordered, ys):
        col = ps.LIB_COLOR.get(lib, "#555555")
        h = ax_strip.hlines(sv, 0.04, 0.26, color=col, lw=1.8, zorder=4)
        h.set_gid(f"b:ctrl:{sv:.4f}:{lib}")
        ax_strip.plot([0.26, 0.34], [sv, ylab], color=col, lw=0.5, zorder=3)
        ax_strip.text(0.37, ylab, "\n".join(_short(r.method) for r in rows),
                      ha="left", va="center", fontsize=5.7, color=col,
                      linespacing=1.2)
        out["controllers"].append({"survival": sv, "library": lib,
                                   "gid": f"b:ctrl:{sv:.4f}:{lib}",
                                   "methods": [r.method for r in rows],
                                   "n_seeds": [r.n_seeds for r in rows],
                                   "epi": [r.epi for r in rows]})
    ax_strip.set_title("controllers", fontsize=7, pad=4)
    ax_strip.set_xlabel("priced pool,\none fit per seed", fontsize=6.0,
                        color="#555555", linespacing=1.25)
    return out


def _short(method: str) -> str:
    """Compact controller name for the strip.  ``*_dagger`` is never DAgger."""
    return {"sindy_mpc_raw": "raw, STLSQ",
            "sindy_mpc_raw_ens": "raw, ens.",
            "sindy_mpc_conf": "frozen recipe",
            "sindy_mpc_conf_dagger": "frozen + re-ident.",
            "sindy_mpc_dense": "dense",
            "sindy_mpc_dense_dagger": "dense + re-ident.",
            "sindy_mpc_lowthr": "low threshold",
            "sindy_mpc_phys": "physics, STLSQ",
            "sindy_mpc_phys_ens": "physics, ens.",
            "nn_mpc": "NN-MPC"}.get(method, method)


def panel_c(ax, k: dict, st: dict) -> dict:
    """Knock-in per replicate, paired strips, median heavy and mean open."""
    from matplotlib.patches import Rectangle

    rng = np.random.default_rng(3)
    pos = {obj: i for i, obj in enumerate(("default", "priced"))}
    xs = {}
    out = {"groups": [], "knockout": {}, "stats": {}}

    for obj, i in pos.items():
        v = k[obj].sort_values("seed")["knockin"].to_numpy(float)
        xs[obj] = i + rng.uniform(-0.10, 0.10, size=len(v))

    # lines join the SAME SEED: one identified model, two stage costs
    a = k["default"].sort_values("seed")["knockin"].to_numpy(float)
    b = k["priced"].sort_values("seed")["knockin"].to_numpy(float)
    for j in range(len(a)):
        ax.plot([xs["default"][j], xs["priced"][j]], [a[j], b[j]],
                color="#BBBBBB", lw=0.5, zorder=2)

    for obj, i in pos.items():
        v = k[obj].sort_values("seed")["knockin"].to_numpy(float)
        c = OBJ_COLOR[obj] if obj == "priced" else "#777777"
        q25, q50, q75 = (float(np.quantile(v, q)) for q in (0.25, 0.5, 0.75))
        mean = float(v.mean())
        ax.add_patch(Rectangle((i - 0.28, q25), 0.56, q75 - q25, facecolor=c,
                               alpha=0.10, edgecolor=c, linewidth=0.6, zorder=3))
        sc = ax.scatter(xs[obj], v, s=11, facecolors=c, edgecolors="none",
                        alpha=0.55, zorder=4)
        sc.set_gid(f"c:pts:{obj}")
        med = ax.hlines(q50, i - 0.30, i + 0.30, color=c, lw=3.0, zorder=6)
        med.set_gid(f"c:median:{obj}")
        mn, = ax.plot([i], [mean], marker="o", ms=6.5, mfc="none", mec=c,
                      mew=1.2, ls="", zorder=6)
        mn.set_gid(f"c:mean:{obj}")
        if obj == "default":            # name the two markers once, in place
            arrow = dict(arrowstyle="-", lw=0.5, color="#555555",
                         shrinkA=1.0, shrinkB=2.0)
            ax.annotate("median", xy=(i - 0.30, q50), xytext=(-0.58, q50 + 1.7),
                        fontsize=6.0, color="#555555", ha="left", va="center",
                        arrowprops=arrow)
            ax.annotate("mean", xy=(i - 0.05, mean), xytext=(-0.58, mean - 1.7),
                        fontsize=6.0, color="#555555", ha="left", va="center",
                        arrowprops=arrow)
        p_raw = st["raw"][(obj, "knockin")]
        p_adj = st["holm"][(obj, "knockin")]
        ax.text(0.25 + 0.50 * i, 0.985,
                f"median {q50:+.2f}\nmean {mean:+.2f}\n"
                f"{int((v > 0).sum())}/{len(v)} positive\n"
                f"$p$ = {p_raw:.1e}\n({p_adj:.1e} Holm)",
                transform=ax.transAxes, ha="center", va="top", fontsize=6.1,
                color=c, linespacing=1.35)
        out["groups"].append({"objective": obj, "n": int(len(v)),
                              "median": q50, "mean": mean, "q25": q25, "q75": q75,
                              "positive": int((v > 0).sum()),
                              "min": float(v.min()), "max": float(v.max()),
                              "p_wilcoxon": p_raw, "p_holm": p_adj})
        ko = k[obj]["knockout"].to_numpy(float)
        out["knockout"][obj] = {"median": float(np.median(ko)), "mean": float(ko.mean()),
                                "positive": int((ko > 0).sum()), "n": int(len(ko))}

    ax.axhline(0.0, color="#666666", lw=0.6, zorder=1)
    ax.set_xlim(-0.62, 1.62)
    ax.set_ylim(-5.8, 12.4)
    ax.set_yticks([-2, 0, 2, 4, 6])
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["default\nstage cost", "priced\nstage cost"])
    ax.set_ylabel(r"knock-in effect on EPI (EUR m$^{-2}$)")
    ax.set_title("restoring the term, one replicate at a time", fontsize=8, pad=4)

    kod = out["knockout"]
    ax.text(0.5, 0.012,
            "grey lines join the same seed\n"
            "(one model, two stage costs).\n"
            f"knock-OUT: median {kod['default']['median']:+.2f} and "
            f"{kod['priced']['median']:+.2f},\n"
            f"positive in {kod['default']['positive']}/{kod['default']['n']} and "
            f"{kod['priced']['positive']}/{kod['priced']['n']} -- mostly already cut",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=5.7,
            color="#555555", linespacing=1.35)
    out["stats"]["family"] = st["family"]
    return out


# ---------------------------------------------------------------------------
# Read-back
# ---------------------------------------------------------------------------

def _by_gid(fig, prefix: str) -> dict:
    found = {}
    for art in fig.findobj():
        g = art.get_gid()
        if g and g.startswith(prefix):
            found.setdefault(g, []).append(art)
    return found


def readback(fig, ax_a, ax_b) -> dict:
    out = {"panel_a": {}, "panel_b": {}, "panel_c": {}}
    # the x axis is ordinal, so what the reader actually reads is the TICK
    # LABELS: check those, not just the positions the lines were drawn at.
    for key, ax in (("panel_a", ax_a), ("panel_b", ax_b)):
        out[key]["xtick_positions"] = [float(t) for t in ax.get_xticks()]
        out[key]["xtick_labels"] = [t.get_text() for t in ax.get_xticklabels()]
    for g, arts in _by_gid(fig, "a:mean:").items():
        ln = arts[0]
        out["panel_a"][g] = {"x": np.asarray(ln.get_xdata(), float).tolist(),
                             "y": np.asarray(ln.get_ydata(), float).tolist()}
    for g, arts in _by_gid(fig, "a:band:").items():
        p = np.asarray(arts[0].get_paths()[0].vertices, float)
        out["panel_a"][g] = {"y_min": float(p[:, 1].min()), "y_max": float(p[:, 1].max())}
    for g, arts in _by_gid(fig, "b:surv:").items():
        ln = arts[0]
        out["panel_b"][g] = {"x": np.asarray(ln.get_xdata(), float).tolist(),
                             "y": np.asarray(ln.get_ydata(), float).tolist()}
    for g, arts in _by_gid(fig, "b:ctrl:").items():
        seg = np.asarray(arts[0].get_segments(), float)
        out["panel_b"][g] = {"y": float(seg[0][0][1])}
    for g, arts in _by_gid(fig, "c:pts:").items():
        off = np.asarray(arts[0].get_offsets(), float)
        out["panel_c"][g] = {"y_sorted": np.sort(off[:, 1]).tolist(), "n": int(len(off))}
    for g, arts in _by_gid(fig, "c:median:").items():
        seg = np.asarray(arts[0].get_segments(), float)
        out["panel_c"][g] = {"y": float(seg[0][0][1])}
    for g, arts in _by_gid(fig, "c:mean:").items():
        out["panel_c"][g] = {"y": float(np.asarray(arts[0].get_ydata(), float)[0])}
    return out


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def _raw_concat(patterns) -> pd.DataFrame:
    """Read CSVs with plain pandas.

    The house rule is that figure scripts never touch a CSV directly.  This is
    the ONE sanctioned exception and it lives only inside the self-check: a
    check that re-imports the code it is checking cannot catch a bug in that
    code.  The dedup key and the abort rule are therefore restated by hand
    below, and any disagreement with ``_plotstyle`` is itself a finding.
    """
    frames = []
    for pat in patterns:
        hits = sorted(glob.glob(str(ps.RESULTS / pat)))
        if not hits:
            raise FileNotFoundError(pat)
        frames += [pd.read_csv(h) for h in hits]
    return pd.concat(frames, ignore_index=True)


def _independent_mechanism(objective: str) -> pd.DataFrame:
    pats = {"priced": ["priced_mech/mechanism_pricedMech.csv",
                       "priced_mech/mechanism_pricedMech2.csv"],
            "default": ["final/mechanism.csv"]}[objective]
    d = _raw_concat(pats)
    d = d.drop_duplicates(subset=["block", "condition", "seed", "test_year"], keep="first")
    if "stop_reason" in d.columns:
        d = d[d["stop_reason"] != "solver_aborted"]
    return d[d["test_year"] == SEASON]


def selfcheck(values: dict) -> int:
    fails, checks = 0, []

    def chk(name, got, want, tol=1e-9):
        nonlocal fails
        g, w = np.atleast_1d(np.asarray(got, float)), np.atleast_1d(np.asarray(want, float))
        ok = g.shape == w.shape and bool(np.allclose(g, w, rtol=0, atol=tol, equal_nan=True))
        fails += (not ok)
        checks.append((ok, name, got, want))

    def chk_eq(name, got, want):
        nonlocal fails
        ok = (got == want)
        fails += (not ok)
        checks.append((ok, name, got, want))

    rb = values["readback"]

    for obj in OBJECTIVES:
        d = _independent_mechanism(obj)
        L = d[d["block"] == "lambda"].copy()
        L["alive"] = (L["xi_uboil"].fillna(0.0).abs() > 0).astype(float)
        g = L.groupby("lam").agg(n=("epi", "size"), mu=("epi", "mean"),
                                 sd=("epi", "std"), sv=("alive", "mean")).sort_index()
        chk_eq(f"a: lambda levels, {obj}", len(g), 13)
        chk_eq(f"a: replicates per level, {obj}", sorted(set(g["n"])), [20])
        chk(f"a: levels drawn in order, {obj}", rb["panel_a"][f"a:mean:{obj}"]["x"],
            np.arange(len(g), dtype=float))
        for key in ("panel_a", "panel_b"):
            chk(f"{key[-1]}: tick labels are the lambda values, {obj}",
                [float(t) for t in rb[key]["xtick_labels"]], g.index.to_numpy(float))
            chk(f"{key[-1]}: ticks sit under the drawn points, {obj}",
                rb[key]["xtick_positions"], np.arange(len(g), dtype=float))
        chk(f"a: mean EPI drawn, {obj}", rb["panel_a"][f"a:mean:{obj}"]["y"],
            g["mu"].to_numpy(float))
        chk(f"a: SD band extent, {obj}",
            [rb["panel_a"][f"a:band:{obj}"]["y_min"], rb["panel_a"][f"a:band:{obj}"]["y_max"]],
            [float((g["mu"] - g["sd"]).min()), float((g["mu"] + g["sd"]).max())])
        chk(f"b: survival drawn, {obj}", rb["panel_b"][f"b:surv:{obj}"]["y"],
            g["sv"].to_numpy(float))

        # the collapse: full survival up to 0.03, none from 0.06
        chk_eq(f"b: survival is 1.00 at the smallest lambda, {obj}",
               float(g["sv"].iloc[0]), 1.0)
        chk_eq(f"b: survival is 0.00 from lambda = 0.06, {obj}",
               float(g.loc[g.index >= 0.06, "sv"].max()), 0.0)
        chk_eq(f"b: survival is monotone non-increasing in lambda, {obj}",
               bool(np.all(np.diff(g["sv"].to_numpy(float)) <= 1e-12)), True)

        # --- panel (c): the knock block ---------------------------------
        K = d[d["block"] == "knock"]
        piv = K.pivot_table(index="seed", columns="condition", values="epi")
        ki = (piv["knockin"] - piv["baseline"]).sort_index().to_numpy(float)
        ko = (piv["knockout"] - piv["baseline"]).sort_index().to_numpy(float)
        chk_eq(f"c: replicates, {obj}", len(ki), 20)
        chk(f"c: knock-in points drawn, {obj}", rb["panel_c"][f"c:pts:{obj}"]["y_sorted"],
            np.sort(ki))
        chk(f"c: median tick, {obj}", rb["panel_c"][f"c:median:{obj}"]["y"], float(np.median(ki)))
        chk(f"c: mean symbol, {obj}", rb["panel_c"][f"c:mean:{obj}"]["y"], float(ki.mean()))
        grp = [x for x in values["panel_c"]["groups"] if x["objective"] == obj][0]
        chk_eq(f"c: positive replicates, {obj}", grp["positive"], int((ki > 0).sum()))
        chk(f"c: Wilcoxon p, {obj}", grp["p_wilcoxon"], float(stats.wilcoxon(ki).pvalue))
        chk(f"c: knock-out median, {obj}", values["panel_c"]["knockout"][obj]["median"],
            float(np.median(ko)))

    # the median must dominate the mean visually AND the retracted magnitude
    # may never stand alone: both objectives are on the page.
    meds = {x["objective"]: x["median"] for x in values["panel_c"]["groups"]}
    chk_eq("guard: both objectives drawn, so +3.05 never stands alone",
           sorted(meds), ["default", "priced"])
    chk_eq("guard: priced median is far below the priced mean (tail, not shift)",
           bool([x for x in values["panel_c"]["groups"] if x["objective"] == "priced"][0]["mean"]
                > 4 * meds["priced"]), True)

    # --- controller survival ticks ---------------------------------------
    cl = _raw_concat(["priced_main/*.csv", "priced_dagger/*.csv",
                      "phys_lib/main_physlib*.csv"])
    cl = cl.drop_duplicates(subset=["method", "seed", "test_year"], keep="first")
    cl = cl[cl["stop_reason"] != "solver_aborted"]
    want = {}
    for method, gg in cl.groupby("method"):
        want[method] = float((gg.groupby("seed")["xi_uboil"].first().abs() > 0).mean())
    drawn, gids = {}, {}
    for entry in values["panel_b"]["controllers"]:
        for m in entry["methods"]:
            drawn[m], gids[m] = entry["survival"], entry["gid"]
    chk_eq("b: every closed-loop controller has a tick", sorted(drawn), sorted(want))
    for m in sorted(want):
        chk(f"b: survival tick, {m}", drawn[m], want[m], tol=5e-5)
        chk(f"b: tick position on the axis, {m}",
            rb["panel_b"][gids[m]]["y"], drawn[m], tol=5e-5)

    width = max(len(c[1]) for c in checks)

    def fmt(v):
        if isinstance(v, (list, tuple, np.ndarray)):
            seq = list(v)
            if not all(isinstance(x, (int, float, np.floating, np.integer)) for x in seq):
                return "[" + ", ".join(str(x) for x in seq[:4]) + ("...]" if len(seq) > 4 else "]")
            return ("[" + ", ".join(f"{float(x):.4f}" for x in seq[:4])
                    + ("...]" if len(seq) > 4 else "]"))
        return f"{v:.6g}" if isinstance(v, float) else str(v)

    for ok, name, got, want_ in checks:
        print(f"  [{'OK ' if ok else 'FAIL'}] {name:<{width}}  drawn {fmt(got)}"
              + ("" if ok else f"   expected {fmt(want_)}"))
    print(f"  {len(checks) - fails}/{len(checks)} checks passed")
    return fails


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ps.use_style()
    import matplotlib.pyplot as plt

    sw = sweeps()
    k = knocks()
    st = knock_stats(k)
    cs = controller_survival()

    fig = plt.figure(figsize=(ps.W2, 7.6 * ps.CM))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.14, 0.98, 0.56, 1.06],
                          wspace=0.34, left=0.062, right=0.988,
                          bottom=0.205, top=0.900)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_bs = fig.add_subplot(gs[0, 2])
    ax_c = fig.add_subplot(gs[0, 3])

    a = panel_a(ax_a, sw)
    b = panel_b(ax_b, ax_bs, sw, cs)
    c = panel_c(ax_c, k, st)

    ps.panel_label(ax_a, "a", dx=-0.18, dy=1.05)
    ps.panel_label(ax_b, "b", dx=-0.24, dy=1.05)
    ps.panel_label(ax_c, "c", dx=-0.22, dy=1.05)

    written = []
    for stem in ("fig3_lambda_survival_knockin", "fig3"):
        written += ps.finish(fig, stem)

    mech_p = ps.load_mechanism("priced")
    mech_d = ps.load_mechanism("default")
    values = {
        "figure": "Figure 3 -- sparsity sweep, boiler-term survival, knock-in",
        "label": "fig:lambda",
        "sources": {
            "mechanism_priced": mech_p.attrs.get("source_files"),
            "mechanism_priced_rows": [int(mech_p.attrs["rows_before_dedup"]), int(len(mech_p))],
            "mechanism_default": mech_d.attrs.get("source_files"),
            "mechanism_default_rows": [int(mech_d.attrs["rows_before_dedup"]), int(len(mech_d))],
            "closed_loop": ps.load_library_pool().attrs["source_files"],
            "season": SEASON,
        },
        "panel_a": a, "panel_b": b, "panel_c": c,
        "knock_stats": {"raw": {f"{o}/{e}": v for (o, e), v in st["raw"].items()},
                        "holm": {f"{o}/{e}": v for (o, e), v in st["holm"].items()},
                        "family": st["family"]},
        "readback": readback(fig, ax_a, ax_b),
        "outputs": [str(p) for p in written],
    }
    plt.close(fig)

    side = ps.FIGDIR / "fig3_values.json"
    side.write_text(json.dumps(values, indent=2, default=float), encoding="utf-8")

    for obj in OBJECTIVES:
        s = sw[obj]
        coll = s[(s["lam"] >= 0.03) & (s["lam"] <= 0.06)]
        print(f"lambda sweep {obj:<8}: {len(s)} levels x n={int(s['n'].iloc[0])}, "
              f"survival "
              + " -> ".join(f"{v:.2f}" for v in coll["survival"])
              + f" across lambda = " + ", ".join(f"{v:g}" for v in coll["lam"]))
        print(f"  EPI at lambda=1e-06 {s['epi_mean'].iloc[0]:+.4f} "
              f"-> at lambda=0.2 {s['epi_mean'].iloc[-1]:+.4f} "
              f"(SD {s['epi_sd'].iloc[0]:.4f} -> {s['epi_sd'].iloc[-1]:.4f})")
    for g in c["groups"]:
        print(f"knock-in {g['objective']:<8}: n={g['n']} median={g['median']:+.4f} "
              f"mean={g['mean']:+.4f} IQR [{g['q25']:+.4f}, {g['q75']:+.4f}] "
              f"positive={g['positive']}/{g['n']} p={g['p_wilcoxon']:.3e} "
              f"(Holm {g['p_holm']:.3e} over {len(st['family'])} tests)")
    for obj, ko in c["knockout"].items():
        print(f"knock-out {obj:<7}: median={ko['median']:+.4f} mean={ko['mean']:+.4f} "
              f"positive={ko['positive']}/{ko['n']}")
    print("controller survival ticks:")
    for e in b["controllers"]:
        print(f"  {e['survival']:.2f}  " + ", ".join(e["methods"]))
    print("wrote " + ", ".join(str(p) for p in written))
    print(f"wrote {side}")

    print("\nself-check (recomputed from the CSVs, compared with the drawn artists):")
    fails = selfcheck(values)
    print("SELF-CHECK: " + ("OK" if fails == 0 else f"FAIL ({fails})"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
