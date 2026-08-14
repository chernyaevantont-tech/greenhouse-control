"""Figure 1 -- Selection reversal and the survival of the actuator pathway.

REBUILT 2026-08-14.  The previous version of this figure carried the
conditioning thesis: kappa as *the* mechanism, monotone in the closed loop.
The full ``physics`` library reached closed loop on 2026-08-13
(``regen/results/phys_lib/``) and that thesis is false.  With the threshold,
the degree and the optimiser all held fixed and ONLY the feature library
changing, the closed-loop series is NON-MONOTONE in kappa:

    library             kappa   24-h rollout    EPI      boiler term kept
    raw                   8.2        2.67      +4.32          55 %
    physics_no_cross     24.5       10.99      +0.28          15 %
    physics              53.4       24.27      +2.75          55 %

The worst-conditioned library beats the middle one tenfold.  What the closed
loop tracks is whether the ACTUATOR PATHWAY survives thresholding, not how
well the feature matrix is conditioned.  Conditioning still predicts open-loop
multi-step stability cleanly -- that part is kept, in panel (b), and labelled
as what it is.

  (a)  The reversal, as raw data.  One-step RMSE of ``t_in`` (linear x) against
       24-h rollout RMSE (log y), one marker per fit.  Colour = library,
       marker = sparse estimator, OPEN FACE = fails the 0.05 divergence gate.
       Median + IQR cross per library.  Unchanged in substance: this result is
       untouched by the correction.
  (b)  What conditioning DOES buy.  kappa (log x) against one-step RMSE (left)
       and median 24-h rollout RMSE (right, log).  Monotone, clean, open loop.
  (c)  THE CORRECTION.  Closed-loop EPI against boiler-term survival for all
       three libraries under the matched recipe (ensemble, threshold 0.05,
       degree 1, no denoising).  Each point carries its kappa, and the grey
       path joins the points IN ORDER OF INCREASING KAPPA so the reader sees
       conditioning order them wrongly.  Open markers repeat the comparison
       under STLSQ.
  (d)  Why ``physics_no_cross`` is the one that fails.  Identified boiler
       coefficient per seed against the 0.05 cut, symlog so a cut coefficient
       sits at exactly 0.  Its estimate is the smallest of the three and falls
       below the cut in 17 of 20 seeds; the full library, which is the only one
       carrying the bilinear ``t_uBoil`` detour, puts half its survivors at
       roughly three times the cut.

Every number drawn is computed here from the CSVs under
``own-article/regen/results`` through ``_plotstyle``; none is a literal.  After
drawing, the values are read back OUT OF THE MATPLOTLIB ARTISTS into
``fig1_values.json``, and :func:`selfcheck` re-derives them from the raw CSVs
along an independent code path and compares.

Run:
    PYTHONIOENCODING=utf-8 python make_fig1.py
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import _plotstyle as ps

MATCHED_OPT = "ensemble"        # the one-factor row that is complete for all three
REPLICATE_OPT = "stlsq"         # complete for raw and physics only
THRESHOLD = 0.05                # regen_config.CONFIRMATORY/RAW_ENS/PHYS_ENS


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def ladder_block() -> pd.DataFrame:
    """Degree-1, undenoised, sparse-estimator block: 120 rows, 40 per library.

    SCOPE.  The reversal is stated over this block only (2 of 72 labels per
    library).  Pooled over all 72 labels the raw library has the best mean
    one-step RMSE and there is no reversal -- see the loader docstring.
    """
    return ps.load_ladder(degree=1, denoise="none",
                          optimizers=("stlsq", "ensemble"))


def matched_table() -> pd.DataFrame:
    """One-factor closed-loop comparison, joined to the ladder's kappa/rollout.

    The ladder row is the SAME library at the same degree and denoising, under
    the same estimator; the ladder does not vary the threshold, so the join is
    on (library, optimizer) and is exact for everything except the threshold,
    which the ladder fixes at its own default.  Stated in the caption.
    """
    lad = ps.load_ladder(degree=1, denoise="none", optimizers=(MATCHED_OPT,))
    lsum = ps.ladder_summary(lad).set_index("variant")
    out = {}
    for opt in (MATCHED_OPT, REPLICATE_OPT):
        t = ps.library_one_factor(opt)
        t["kappa"] = [float(lsum.loc[l, "kappa"]) for l in t["library"]]
        t["rollout_median"] = [float(lsum.loc[l, "rollout_median"]) for l in t["library"]]
        t["one_step"] = [float(lsum.loc[l, "one_step"]) for l in t["library"]]
        out[opt] = t
    m = out[MATCHED_OPT]
    m.attrs["replicate"] = out[REPLICATE_OPT]
    return m


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

def panel_a(ax, lad: pd.DataFrame) -> dict:
    """Scatter of the two prediction criteria, one marker per fit."""
    ps.scatter_by_library(ax, lad, "one_step_rmse_t_in", "rollout_rmse_t_in",
                          legend=False)
    for coll in ax.collections:
        coll.set_gid("a:scatter")

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
        h = ax.hlines(my, xq[0], xq[1], color=c, lw=1.8, zorder=6)
        v = ax.vlines(mx, yq[0], yq[1], color=c, lw=1.8, zorder=6)
        h.set_gid(f"a:crossh:{lib}")
        v.set_gid(f"a:crossv:{lib}")
        crosses[lib] = {"n": int(len(s)), "median_one_step": mx,
                        "median_rollout": my, "one_step_iqr": list(xq),
                        "rollout_iqr": list(yq)}

    ax.set_yscale("log")
    ax.set_xlabel(r"one-step RMSE of $T_{\mathrm{in}}$ ($^\circ$C)")
    ax.set_ylabel(r"24-h rollout RMSE ($^\circ$C, log)")
    ax.set_title("prediction criteria disagree", fontsize=8, pad=4)

    from matplotlib.lines import Line2D
    grey = ps.OKABE_ITO["grey"]
    n_fail = int((~lad["passes_gate"].astype(bool)).sum())
    handles = [Line2D([], [], marker="o", ls="", color=ps.LIB_COLOR[l],
                      label=ps.LIB_LABEL[l], markersize=4) for l in ps.LIB_ORDER]
    handles += [
        Line2D([], [], marker="o", ls="", mfc=grey, mec=grey, ms=4, label="STLSQ"),
        Line2D([], [], marker="s", ls="", mfc=grey, mec=grey, ms=4, label="ensemble"),
        Line2D([], [], marker="o", ls="", mfc="none", mec=grey, ms=4,
               label=f"open: fails the 0.05 gate ({n_fail}/{len(lad)})"),
    ]
    ax.legend(handles=handles, loc="lower left", ncol=1, fontsize=6.4,
              handletextpad=0.4, borderaxespad=0.2, labelspacing=0.22)

    ax.set_ylim(top=60.0)
    ps.annotate_n(ax, "degree 1, undenoised, sparse estimators\n"
                      "$n=40$ fits per library", loc="upper right")
    return {"crosses": crosses, "n_rows": int(len(lad)), "n_gate_fail": n_fail}


def panel_b(ax, lad: pd.DataFrame) -> dict:
    """Conditioning against both OPEN-LOOP criteria.  This part survives."""
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
    e1 = ax.errorbar(k, os_mean, yerr=os_sd, xerr=k_sd, color=dark, lw=1.1,
                     ls="-", marker="none", capsize=2.0, elinewidth=0.7, zorder=3)
    e2 = ax2.errorbar(k, ro_med, yerr=np.vstack([ro_lo, ro_hi]), color=dark,
                      lw=1.1, ls="--", marker="none", capsize=2.0,
                      elinewidth=0.7, zorder=3)
    e1.lines[0].set_gid("b:onestep")
    e2.lines[0].set_gid("b:rollout")

    for i, lib in enumerate(g["variant"]):
        c = ps.LIB_COLOR[str(lib)]
        p1, = ax.plot([k[i]], [os_mean[i]], marker="o", ms=5.5, mfc=c, mec=dark,
                      mew=0.6, zorder=6, clip_on=False)
        p2, = ax2.plot([k[i]], [ro_med[i]], marker="s", ms=5.5, mfc=c, mec=dark,
                       mew=0.6, zorder=6, clip_on=False)
        p1.set_gid(f"b:pt_onestep:{lib}")
        p2.set_gid(f"b:pt_rollout:{lib}")
        ax.annotate(rf"$\kappa={k[i]:.1f}$", xy=(k[i], os_mean[i]),
                    xytext=(0, -11), textcoords="offset points",
                    ha="center", va="top", fontsize=6.5, color=dark)

    ax.set_xscale("log")
    ax2.set_yscale("log")
    ax.set_xlabel(r"condition number $\kappa$ of the feature matrix (log)")
    ax.set_ylabel(r"one-step RMSE ($^\circ$C), mean $\pm$ SD")
    ax2.set_ylabel(r"median 24-h rollout RMSE ($^\circ$C, log)")
    ax.set_title(r"$\kappa$ orders the OPEN loop", fontsize=8, pad=4)
    ax.set_xticks([8, 16, 32, 64])
    import matplotlib.ticker as mticker
    ax.get_xaxis().set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
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


def panel_c(ax, m: pd.DataFrame) -> dict:
    """Closed-loop EPI against boiler-term survival.  kappa orders this wrongly."""
    rep = m.attrs["replicate"]
    dark = "#333333"

    # the path a reader would follow if kappa ranked controllers
    order = m.sort_values("kappa")
    pth, = ax.plot(order["survival"], order["epi"], ls="--", lw=0.9,
                   color=ps.OKABE_ITO["grey"], zorder=2)
    pth.set_gid("c:kappapath")
    xs, ys = order["survival"].to_numpy(float), order["epi"].to_numpy(float)
    for i in range(len(xs) - 1):
        ax.annotate("", xy=(xs[i + 1], ys[i + 1]), xytext=(xs[i], ys[i]),
                    arrowprops=dict(arrowstyle="-|>", lw=0.0, color=ps.OKABE_ITO["grey"],
                                    shrinkA=8, shrinkB=8, mutation_scale=8))

    out = {"matched": [], "replicate": [], "optimizer": MATCHED_OPT}
    for r in m.itertuples():
        c = ps.LIB_COLOR[r.library]
        e = ax.errorbar([r.survival], [r.epi], yerr=[r.epi_se_seed],
                        xerr=[[r.survival - r.survival_lo], [r.survival_hi - r.survival]],
                        fmt="o", ms=7.0, mfc=c, mec=dark, mew=0.7, color=dark,
                        elinewidth=0.8, capsize=2.0, zorder=6)
        e.lines[0].set_gid(f"c:ens:{r.library}")
        off = {"raw": (10, 8, "left", "bottom"),
               "physics_no_cross": (12, 10, "left", "bottom"),
               "physics": (11, -6, "left", "top")}[r.library]
        ax.annotate(f"{ps.LIB_LABEL[r.library]}\n"
                    rf"$\kappa={r.kappa:.1f}$,  EPI ${r.epi:+.2f}$",
                    xy=(r.survival, r.epi), xytext=off[:2],
                    textcoords="offset points", ha=off[2], va=off[3],
                    fontsize=6.6, color=dark, linespacing=1.3)
        out["matched"].append({"library": r.library, "method": r.method,
                               "n_runs": r.n_runs, "n_seeds": r.n_seeds,
                               "survival": r.survival, "survival_k": r.survival_k,
                               "survival_lo": r.survival_lo, "survival_hi": r.survival_hi,
                               "epi": r.epi, "epi_sd": r.epi_sd,
                               "epi_se_seed": r.epi_se_seed, "epi_median": r.epi_median,
                               "kappa": r.kappa, "truncated": r.truncated})

    for r in rep.itertuples():
        c = ps.LIB_COLOR[r.library]
        p, = ax.plot([r.survival], [r.epi], marker="D", ms=4.6, mfc="none",
                     mec=c, mew=1.0, ls="", zorder=5)
        p.set_gid(f"c:stlsq:{r.library}")
        out["replicate"].append({"library": r.library, "method": r.method,
                                 "n_runs": r.n_runs, "survival": r.survival,
                                 "epi": r.epi, "epi_se_seed": r.epi_se_seed})

    ax.axhline(0.0, color="#888888", lw=0.6, zorder=1)
    ax.set_xlim(0.02, 0.99)
    ax.set_ylim(-1.6, 8.6)
    ax.set_xlabel("boiler term kept, fraction of 20 seeds")
    ax.set_ylabel(r"four-season mean EPI (EUR m$^{-2}$)")
    ax.set_title("survival orders the CLOSED loop", fontsize=8, pad=4)

    from matplotlib.lines import Line2D
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="", mfc=ps.OKABE_ITO["grey"], mec=dark,
               ms=5.5, label="ensemble, $\\lambda=0.05$"),
        Line2D([], [], marker="D", ls="", mfc="none", mec=ps.OKABE_ITO["grey"],
               ms=4.6, label="STLSQ, $\\lambda=0.05$ (2 of 3)"),
        Line2D([], [], ls="--", lw=0.9, color=ps.OKABE_ITO["grey"],
               label=r"path in order of rising $\kappa$"),
    ], loc="lower right", fontsize=6.4, handletextpad=0.5, labelspacing=0.28,
        borderaxespad=0.3)

    ps.annotate_n(ax, "vertical bar: seed-level SE;  horizontal: Wilson 95 %\n"
                      "these three differ in nothing but the library.  Survival\n"
                      "does not rank controllers that differ in more than that.",
                  loc="upper left")
    return out


def panel_d(ax, coef: pd.DataFrame, struct: pd.DataFrame) -> dict:
    """Identified boiler coefficient against the 0.05 cut, per seed."""
    rng = np.random.default_rng(7)
    st = struct.set_index("library")
    dark = "#333333"
    out = {"threshold": THRESHOLD, "libraries": []}

    ax.axhspan(-0.004, THRESHOLD, color="#F2F2F2", zorder=0)
    thr = ax.axhline(THRESHOLD, color=dark, ls=":", lw=0.9, zorder=3)
    thr.set_gid("d:threshold")

    for i, lib in enumerate(ps.LIB_ORDER):
        s = coef[coef["library"] == lib].sort_values("seed")
        v = s["abs_xi"].to_numpy(float)
        c = ps.LIB_COLOR[lib]
        xs = i + rng.uniform(-0.17, 0.17, size=len(v))
        sc = ax.scatter(xs, v, s=16, facecolors=c, edgecolors=dark,
                        linewidths=0.35, alpha=0.9, zorder=4)
        sc.set_gid(f"d:strip:{lib}")
        alive = v[v > 0]
        med = float(np.median(alive)) if len(alive) else float("nan")
        h = ax.hlines(med, i - 0.28, i + 0.28, color=c, lw=2.2, zorder=5)
        h.set_gid(f"d:median:{lib}")
        ax.annotate(f"kept {len(alive)}/{len(v)}\ncut {len(v) - len(alive)}/{len(v)}",
                    xy=(i, 0.40), ha="center", va="bottom", fontsize=6.8,
                    color=c, linespacing=1.3)
        out["libraries"].append({
            "library": lib, "n_seeds": int(len(v)),
            "n_alive": int(len(alive)), "n_cut": int(len(v) - len(alive)),
            "median_surviving_abs_xi": med,
            "min_surviving_abs_xi": float(alive.min()) if len(alive) else float("nan"),
            "max_surviving_abs_xi": float(alive.max()) if len(alive) else float("nan"),
            "abs_xi_sorted": np.sort(v).tolist(),
            "n_features": int(st.loc[lib, "n_features"]),
            "has_direct": bool(st.loc[lib, "has_direct"]),
            "has_cross": bool(st.loc[lib, "has_cross"]),
        })

    ax.set_yscale("symlog", linthresh=THRESHOLD, linscale=0.55)
    ax.set_ylim(-0.006, 1.15)
    ax.set_xlim(-0.55, 2.55)
    ax.set_xticks(range(3))
    ax.set_xticklabels([f"{ps.LIB_LABEL[l]}\n{int(st.loc[l, 'n_features'])} terms"
                        f"{'  +' + ps.CROSS_TERM if st.loc[l, 'has_cross'] else ''}"
                        for l in ps.LIB_ORDER], fontsize=6.6)
    import matplotlib.ticker as mticker
    ax.set_yticks([0.0, THRESHOLD, 0.1, 0.2, 0.4])
    ax.get_yaxis().set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_ylabel(r"$|\xi_{u\mathrm{Boil}}|$ identified (symlog)")
    ax.set_title("the cut is decided near the threshold", fontsize=8, pad=4)
    ax.annotate(rf"threshold $\lambda={THRESHOLD}$", xy=(-0.50, THRESHOLD),
                xytext=(0, -4), textcoords="offset points", ha="left",
                va="top", fontsize=6.6, color=dark)
    ax.text(0.5, 0.145, "one fit per seed; heavy tick = median of survivors.\n"
                        "A cut coefficient is written as exactly 0, so its\n"
                        "pre-threshold size is not recoverable from these files.",
            transform=ax.transAxes, ha="center", va="center", fontsize=6.4,
            color="#555555", linespacing=1.35)
    return out


# ---------------------------------------------------------------------------
# Read-back: what the artists actually carry
# ---------------------------------------------------------------------------

def _by_gid(fig, prefix: str) -> dict:
    found = {}
    for art in fig.findobj():
        g = art.get_gid()
        if g and g.startswith(prefix):
            found.setdefault(g, []).append(art)
    return found


def readback(fig, ax_a) -> dict:
    """Pull the drawn geometry back out of the artists.

    Deliberately not a copy of what was passed in: this inspects the figure, so
    the sidecar reflects what is on the page.
    """
    # Only the scatter collections: ``hlines``/``vlines`` also land in
    # ``ax.collections`` and carry a dummy (0, 0) offset, which would silently
    # widen both ranges and inflate the marker count.
    pts = []
    for coll in ax_a.collections:
        if coll.get_gid() != "a:scatter":
            continue
        off = np.asarray(coll.get_offsets(), float)
        if off.size:
            pts.append(off.reshape(-1, 2))
    scat = np.vstack(pts) if pts else np.empty((0, 2))

    out = {
        "panel_a_scatter_n": int(len(scat)),
        "panel_a_x_range": [float(scat[:, 0].min()), float(scat[:, 0].max())],
        "panel_a_y_range": [float(scat[:, 1].min()), float(scat[:, 1].max())],
        "panel_b": {}, "panel_c": {}, "panel_d": {},
    }
    for g, arts in _by_gid(fig, "b:").items():
        ln = arts[0]
        out["panel_b"][g] = {"x": np.asarray(ln.get_xdata(), float).tolist(),
                             "y": np.asarray(ln.get_ydata(), float).tolist()}
    for g, arts in _by_gid(fig, "c:").items():
        ln = arts[0]
        out["panel_c"][g] = {"x": np.asarray(ln.get_xdata(), float).tolist(),
                             "y": np.asarray(ln.get_ydata(), float).tolist()}
    for g, arts in _by_gid(fig, "d:strip:").items():
        off = np.asarray(arts[0].get_offsets(), float)
        out["panel_d"][g] = {"y_sorted": np.sort(off[:, 1]).tolist(),
                             "n": int(len(off))}
    for g, arts in _by_gid(fig, "d:median:").items():
        seg = np.asarray(arts[0].get_segments(), float)
        out["panel_d"][g] = {"y": float(seg[0][0][1])}
    return out


# ---------------------------------------------------------------------------
# Self-check: recompute everything along an independent path
# ---------------------------------------------------------------------------

def _raw_concat(patterns) -> pd.DataFrame:
    """Read CSVs with plain pandas.

    The house rule is that figure scripts never touch a CSV directly -- the
    loaders in ``_plotstyle`` own the dedup key and the abort filter.  This
    function is the ONE sanctioned exception and exists only inside the
    self-check: a check that re-imports the code it is checking cannot catch a
    bug in that code.  The dedup and abort rules are therefore restated here by
    hand, and a disagreement with the loaders is itself a finding.
    """
    frames = []
    for pat in patterns:
        hits = sorted(glob.glob(str(ps.RESULTS / pat)))
        if not hits:
            raise FileNotFoundError(pat)
        frames += [pd.read_csv(h) for h in hits]
    return pd.concat(frames, ignore_index=True)


def _independent_closed_loop() -> pd.DataFrame:
    d = _raw_concat(["priced_main/*.csv", "priced_dagger/*.csv",
                     "phys_lib/main_physlib*.csv"])
    d = d.drop_duplicates(subset=["method", "seed", "test_year"], keep="first")
    d = d[d["stop_reason"] != "solver_aborted"]
    return d


def _independent_ladder(optimizers) -> pd.DataFrame:
    d = _raw_concat(["ladder_rerun/ladder_rerun.csv", "ladder_rerun/ladder_rerun2.csv"])
    d = d.drop_duplicates(subset=["variant", "degree", "optimizer", "denoise", "seed"],
                          keep="first")
    return d[(d["degree"] == 1) & (d["denoise"] == "none")
             & (d["optimizer"].isin(list(optimizers)))]


def selfcheck(values: dict) -> int:
    """Recompute every plotted quantity from the CSVs and compare with the page.

    Returns the number of failures; prints one OK/FAIL line per check.
    """
    fails, checks = 0, []

    def chk(name, got, want, tol=1e-9):
        nonlocal fails
        got_a, want_a = np.atleast_1d(np.asarray(got, float)), np.atleast_1d(np.asarray(want, float))
        ok = got_a.shape == want_a.shape and bool(np.allclose(got_a, want_a, rtol=0, atol=tol,
                                                              equal_nan=True))
        fails += (not ok)
        checks.append((ok, name, got, want))

    def chk_eq(name, got, want):
        nonlocal fails
        ok = (got == want)
        fails += (not ok)
        checks.append((ok, name, got, want))

    rb = values["readback"]

    # --- panel (a) + (b): the ladder block -------------------------------
    lad = _independent_ladder(("stlsq", "ensemble"))
    chk_eq("a: rows in the degree-1 undenoised sparse block", len(lad), 120)
    chk_eq("a: markers drawn", rb["panel_a_scatter_n"], len(lad))
    gate_fail = int(((lad["diverged_frac"].fillna(1.0) > ps.DIVERGENCE_GATE)
                     | (~lad["embeddable"].fillna(False).astype(bool))).sum())
    chk_eq("a: open (gate-failing) markers", values["panel_a"]["n_gate_fail"], gate_fail)
    chk("a: x range of the scatter", rb["panel_a_x_range"],
        [lad["one_step_rmse_t_in"].min(), lad["one_step_rmse_t_in"].max()])
    chk("a: y range of the scatter", rb["panel_a_y_range"],
        [lad["rollout_rmse_t_in"].min(), lad["rollout_rmse_t_in"].max()])
    for lib in ps.LIB_ORDER:
        s = lad[lad["variant"] == lib]
        chk(f"a: median cross, {lib}",
            [values["panel_a"]["crosses"][lib]["median_one_step"],
             values["panel_a"]["crosses"][lib]["median_rollout"]],
            [s["one_step_rmse_t_in"].median(), s["rollout_rmse_t_in"].median()])

    lad_e = _independent_ladder((MATCHED_OPT,))
    kap = [float(lad_e[lad_e["variant"] == l]["kappa"].mean()) for l in ps.LIB_ORDER]
    one = [float(lad_e[lad_e["variant"] == l]["one_step_rmse_t_in"].mean()) for l in ps.LIB_ORDER]
    rol = [float(lad_e[lad_e["variant"] == l]["rollout_rmse_t_in"].median()) for l in ps.LIB_ORDER]
    chk("b: kappa on the drawn line", rb["panel_b"]["b:onestep"]["x"], kap)
    chk("b: one-step on the drawn line", rb["panel_b"]["b:onestep"]["y"], one)
    chk("b: rollout median on the drawn line", rb["panel_b"]["b:rollout"]["y"], rol)
    chk_eq("b: kappa is monotone in library order",
           bool(np.all(np.diff(kap) > 0)), True)
    chk_eq("b: rollout is monotone in library order",
           bool(np.all(np.diff(rol) > 0)), True)

    # --- panel (c): the closed-loop correction ---------------------------
    cl = _independent_closed_loop()
    epis, survs = {}, {}
    for lib, method in ps.LIBRARY_ONE_FACTOR[MATCHED_OPT].items():
        g = cl[cl["method"] == method]
        chk_eq(f"c: runs for {lib} ({method})", len(g), 80)
        seed_alive = g.groupby("seed")["xi_uboil"].first().abs() > 0
        epis[lib] = float(g["epi"].mean())
        survs[lib] = float(seed_alive.mean())
        drawn = rb["panel_c"][f"c:ens:{lib}"]
        chk(f"c: drawn point for {lib}", [drawn["x"][0], drawn["y"][0]],
            [survs[lib], epis[lib]])
        se = float(g.groupby("seed")["epi"].mean().std(ddof=1) / np.sqrt(g["seed"].nunique()))
        chk(f"c: seed-level SE for {lib}",
            [d["epi_se_seed"] for d in values["panel_c"]["matched"]
             if d["library"] == lib][0], se)
    for lib, method in ps.LIBRARY_ONE_FACTOR[REPLICATE_OPT].items():
        g = cl[cl["method"] == method]
        drawn = rb["panel_c"][f"c:stlsq:{lib}"]
        chk(f"c: STLSQ replicate for {lib}", [drawn["x"][0], drawn["y"][0]],
            [float((g.groupby("seed")["xi_uboil"].first().abs() > 0).mean()),
             float(g["epi"].mean())])
    # the point of the panel: kappa order is NOT the EPI order
    kappa_order = [l for _, l in sorted(zip(kap, ps.LIB_ORDER))]
    chk_eq("c: EPI is NOT monotone along rising kappa",
           bool(np.all(np.diff([epis[l] for l in kappa_order]) < 0)), False)
    chk_eq("c: the two 55 % libraries both beat the 15 % one",
           bool(epis["raw"] > epis["physics_no_cross"]
                and epis["physics"] > epis["physics_no_cross"]), True)
    chk_eq("c: worst-conditioned library beats the middle one",
           bool(epis["physics"] > epis["physics_no_cross"]), True)

    # --- panel (d): the coefficients -------------------------------------
    for lib, method in ps.LIBRARY_ONE_FACTOR[MATCHED_OPT].items():
        g = cl[cl["method"] == method]
        per_seed = g.groupby("seed")["xi_uboil"].first().abs().sort_values().to_numpy(float)
        chk(f"d: coefficients drawn for {lib}",
            rb["panel_d"][f"d:strip:{lib}"]["y_sorted"], per_seed)
        alive = per_seed[per_seed > 0]
        chk(f"d: median of survivors, {lib}",
            rb["panel_d"][f"d:median:{lib}"]["y"], float(np.median(alive)))
        chk_eq(f"d: survivors counted, {lib}",
               [x["n_alive"] for x in values["panel_d"]["libraries"]
                if x["library"] == lib][0], int(len(alive)))

    # structural facts, parsed from the experiment module, not typed here
    st = {r["library"]: r for r in values["panel_d"]["libraries"]}
    chk_eq("d: only `physics` carries the bilinear detour",
           [st[l]["has_cross"] for l in ps.LIB_ORDER], [False, False, True])
    chk_eq("d: every library carries the direct boiler term",
           [st[l]["has_direct"] for l in ps.LIB_ORDER], [True, True, True])
    chk_eq("d: library sizes", [st[l]["n_features"] for l in ps.LIB_ORDER], [11, 14, 18])

    # --- retraction guards ------------------------------------------------
    chk_eq("guard: no closed-loop claim is imputed for `physics`",
           all(d["n_runs"] == 80 for d in values["panel_c"]["matched"]), True)
    chk_eq("guard: zero truncated runs in the one-factor set",
           sum(d["truncated"] for d in values["panel_c"]["matched"]), 0)

    width = max(len(c[1]) for c in checks)
    for ok, name, got, want in checks:
        def fmt(v):
            if isinstance(v, (list, tuple, np.ndarray)):
                a = np.atleast_1d(np.asarray(v, float))
                return "[" + ", ".join(f"{x:.4f}" for x in a[:4]) + ("...]" if len(a) > 4 else "]")
            return f"{v:.6f}" if isinstance(v, float) else str(v)
        print(f"  [{'OK ' if ok else 'FAIL'}] {name:<{width}}  drawn {fmt(got)}"
              + ("" if ok else f"   expected {fmt(want)}"))
    print(f"  {len(checks) - fails}/{len(checks)} checks passed")
    return fails


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ps.use_style()
    import matplotlib.pyplot as plt

    lad = ladder_block()
    lad_matched = ps.load_ladder(degree=1, denoise="none", optimizers=(MATCHED_OPT,))
    m = matched_table()
    coef = ps.boiler_coefficients(MATCHED_OPT)
    struct = ps.library_structure()

    fig = plt.figure(figsize=(ps.W2, 12.4 * ps.CM))
    gs = fig.add_gridspec(2, 2, wspace=0.42, hspace=0.52,
                          left=0.070, right=0.930, bottom=0.095, top=0.940)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    a = panel_a(ax_a, lad)
    b = panel_b(ax_b, lad_matched)
    c = panel_c(ax_c, m)
    d = panel_d(ax_d, coef, struct)

    for ax, letter in ((ax_a, "a"), (ax_b, "b"), (ax_c, "c"), (ax_d, "d")):
        ps.panel_label(ax, letter, dx=-0.16, dy=1.06)

    written = []
    for stem in ("fig1_selection_and_conditioning", "fig1"):
        written += ps.finish(fig, stem)

    values = {
        "figure": "Figure 1 -- selection reversal and survival of the actuator pathway",
        "label": "fig:kappa",
        "rebuilt": "2026-08-14; supersedes the conditioning-mechanism version",
        "sources": {
            "ladder": lad.attrs.get("source_files"),
            "ladder_rows_before_dedup": int(lad.attrs.get("rows_before_dedup", -1)),
            "ladder_rows_in_sparse_block": int(len(lad)),
            "ladder_rows_in_matched_block": int(len(lad_matched)),
            "closed_loop": list(m.attrs["source_files"]),
            "matched_optimizer": MATCHED_OPT,
            "threshold": THRESHOLD,
        },
        "panel_a": a, "panel_b": b, "panel_c": c, "panel_d": d,
        "readback": readback(fig, ax_a),
        "outputs": [str(p) for p in written],
    }
    plt.close(fig)

    side = ps.FIGDIR / "fig1_values.json"
    side.write_text(json.dumps(values, indent=2, default=float), encoding="utf-8")

    print(f"ladder       : {lad.attrs.get('rows_before_dedup')} raw rows -> "
          f"{len(lad)} in the degree-1 undenoised sparse block "
          f"({len(lad_matched)} under {MATCHED_OPT} alone)")
    for i, lib in enumerate(b["variant"]):
        print(f"  {lib:<17} kappa={b['kappa'][i]:8.4f}  "
              f"one-step={b['one_step_mean'][i]:.4f} degC  "
              f"rollout median={b['rollout_median'][i]:8.4f} degC  "
              f"diverged={b['diverged_frac_mean'][i]:.4f}")
    print(f"  gate failures drawn open: {a['n_gate_fail']} of {a['n_rows']}")
    print(f"closed loop  : {MATCHED_OPT}, lambda={THRESHOLD}, only the library changes")
    for r in c["matched"]:
        print(f"  {r['library']:<17} {r['method']:<19} n={r['n_runs']}  "
              f"EPI={r['epi']:+.4f} +-{r['epi_se_seed']:.4f} (seed SE)  "
              f"median={r['epi_median']:+.4f}  survival={r['survival']:.2f} "
              f"[{r['survival_lo']:.2f},{r['survival_hi']:.2f}]  kappa={r['kappa']:.2f}")
    for r in c["replicate"]:
        print(f"  {r['library']:<17} {r['method']:<19} n={r['n_runs']}  "
              f"EPI={r['epi']:+.4f}  survival={r['survival']:.2f}   (STLSQ replicate)")
    print("  no physics_no_cross controller exists at STLSQ/0.05 -- the replicate row is 2 of 3")
    for r in d["libraries"]:
        print(f"  {r['library']:<17} {r['n_features']:2d} terms, "
              f"bilinear {ps.CROSS_TERM}: {'yes' if r['has_cross'] else 'no ':<3}  "
              f"kept {r['n_alive']}/{r['n_seeds']}  "
              f"median |xi| of survivors={r['median_surviving_abs_xi']:.4f}")
    print("wrote " + ", ".join(str(p) for p in written))
    print(f"wrote {side}")

    print("\nself-check (recomputed from the CSVs, compared with the drawn artists):")
    fails = selfcheck(values)
    print("SELF-CHECK: " + ("OK" if fails == 0 else f"FAIL ({fails})"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
