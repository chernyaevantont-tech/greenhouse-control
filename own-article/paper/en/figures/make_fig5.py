"""Figure 5 -- Corrections waterfall (label ``fig:disc-corrections``, section 4.4).

Two panels, both in EUR m^-2 of economic performance index (EPI) difference:

  (a) Raw-library advantage over the agronomic heuristic.
      start  +5.5437  raw_ens (priced) minus the STOCK heuristic
      step   -3.4878  "16-trial tuning of the baseline"
      end    +2.0560  raw_ens (priced) minus the TUNED heuristic
      Both ends come from ``n2_tune/tune_rb_n2.csv`` so the waterfall closes
      exactly.  Using the canonical ``rule_based`` row of ``final/main.csv``
      (-1.2061) for the start would give +5.52 and leave a 0.03 residual --
      cross-harness drift, NOT an effect, and it must not be drawn as a step.

  (b) Raw-minus-physics library gap.
      start  +3.6585  default objective  (n7 raw_ens  -  final lowthr)
      step   -2.4301  "stage cost priced to the criterion"
      end    +1.2285  priced objective   (priced raw_ens - priced lowthr)

Every number is computed here from the CSVs through ``_plotstyle`` -- which owns
the dedup key and the solver-abort rule -- and nothing is hard-coded.  The
literals in this docstring are documentation of the expected result; the script
asserts against its own recomputation, not against them.

TEST TYPE, which the caption must respect (SPEC.md, Figure 5):
  * Panel (a): both heuristics are DETERMINISTIC (one run per season, n = 4).
    The 76/80 and 75/80 counts are one-sample comparisons of 80 controller runs
    against a per-season constant.  Never call them paired.
  * Panel (b): 71/80 and 62/80 ARE paired on (seed, test_year).

Dispersion is drawn everywhere the claim depends on it: the run-level strip, the
median as a heavy tick, the mean as an open symbol on the bar top, and a +-1 SD
whisker.  In panel (a) the end bar's median (+2.85) sits ABOVE its mean (+2.06),
so the bar alone would understate the typical run -- which is exactly why the
manuscript quotes both.

Run:
    PYTHONIOENCODING=utf-8 python make_fig5.py
Writes ``fig5.pdf`` and ``fig5.png`` next to this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _plotstyle as ps  # noqa: E402

STEM = "fig5"
STEM_SPEC = "fig5_corrections_waterfall"   # the name 04-discussion.tex cites
JITTER = 0.085
BAR_W = 0.60
RNG_SEED = 11

C_BAR = ps.OKABE_ITO["blue"]        # raw library, fixed by the house convention
C_STEP = ps.OKABE_ITO["grey"]       # the correction itself -- deliberately not a
                                    # library colour (orange/vermilion are taken)
C_MARK = "#000000"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def panel_a_data() -> dict:
    """Raw-library advantage over the heuristic, both ends from ``n2_tune``."""
    priced = ps.load_priced_pool()
    tune = ps.load_heuristic_tuning()

    stock_by_year = tune[tune["block"] == "stock_test"].set_index("test_year")["epi"]
    tuned_by_year = tune[tune["block"] == "tuned_test"].set_index("test_year")["epi"]

    start = np.asarray(ps.deltas_vs_constant(priced, "sindy_mpc_raw_ens", stock_by_year), float)
    end = np.asarray(ps.deltas_vs_constant(priced, "sindy_mpc_raw_ens", tuned_by_year), float)

    # The step is a difference of two deterministic references, so it has no
    # run-level dispersion -- only a per-SEASON one, n = 4.
    season_gain = (tuned_by_year - stock_by_year).sort_index()

    return {
        "start": start, "end": end,
        "step": float(end.mean() - start.mean()),
        "season_gain": season_gain,
        "n_ref": int(len(stock_by_year)),
        "paired": False,
        "title": "Raw-library advantage over the heuristic",
        "labels": ("vs stock\nheuristic", "16-trial tuning\nof the baseline",
                   "vs tuned\nheuristic"),
        "test_note": ("reference is deterministic (n = %d seasons):\n"
                      "counts are one-sample, not paired" % len(stock_by_year)),
    }


def panel_b_data() -> dict:
    """Raw-minus-physics library gap, default objective against priced."""
    priced = ps.load_priced_pool()
    n7 = ps.load_raw_library_default()
    fin = ps.load_default_main()

    # Default-objective end: the only default runs of the raw library are in n7,
    # the physics-no-cross comparator is in final/main.csv.  Both are default.
    default_pool = pd.concat(
        [n7[n7["method"] == "sindy_mpc_raw_ens"],
         fin[fin["method"] == "sindy_mpc_lowthr"]], ignore_index=True)

    start_s = ps.paired_deltas(default_pool, "sindy_mpc_raw_ens", "sindy_mpc_lowthr")
    end_s = ps.paired_deltas(priced, "sindy_mpc_raw_ens", "sindy_mpc_lowthr")
    if not start_s.index.equals(end_s.index):
        raise AssertionError("panel (b): the two objectives are not seed/season matched")

    # Here the step IS defined per run, matched on (seed, test_year).
    step_runs = np.asarray((end_s - start_s).dropna(), float)

    return {
        "start": np.asarray(start_s, float), "end": np.asarray(end_s, float),
        "step": float(end_s.mean() - start_s.mean()),
        "step_runs": step_runs,
        "n_ref": len(step_runs),
        "paired": True,
        "title": "Raw-minus-physics library gap",
        "labels": ("default\nobjective", "stage cost priced\nto the criterion",
                   "priced\nobjective"),
        "test_note": "paired on (seed, test_year), n = %d" % len(step_runs),
    }


def _stats(v: np.ndarray) -> dict:
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    return {"n": int(v.size), "mean": float(v.mean()), "median": float(np.median(v)),
            "sd": float(v.std(ddof=1)), "wins": int((v > 0).sum()),
            "q25": float(np.percentile(v, 25)), "q75": float(np.percentile(v, 75))}


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def _strip(ax, x, v, color, rng, jitter=JITTER, size=5.0, alpha=0.40):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    ax.scatter(x + rng.uniform(-jitter, jitter, v.size), v, s=size, color=color,
               alpha=alpha, linewidths=0, zorder=3)


def _endbar(ax, x, v, rng, label_side="center"):
    """Bar at the mean, with the run-level strip, median tick, mean symbol, SD."""
    st = _stats(v)
    ax.bar(x, st["mean"], width=BAR_W, color=C_BAR, alpha=0.28,
           edgecolor=C_BAR, linewidth=0.9, zorder=2)
    _strip(ax, x, v, C_BAR, rng)
    ax.vlines(x, st["mean"] - st["sd"], st["mean"] + st["sd"], color=C_MARK,
              lw=0.8, zorder=4)
    ax.hlines(st["median"], x - BAR_W / 2, x + BAR_W / 2, color=C_MARK, lw=2.2,
              zorder=6)
    ax.scatter([x], [st["mean"]], s=30, facecolors="white", edgecolors=C_MARK,
               linewidths=1.0, zorder=7)
    return st


def _stepbar(ax, x, top, bottom, spread_vals, rng, spread_kind):
    """Floating correction bar from ``top`` down to ``bottom``."""
    ax.bar(x, bottom - top, width=BAR_W, bottom=top, color=C_STEP, alpha=0.55,
           edgecolor="#555555", linewidth=0.9, zorder=2)
    if spread_kind == "seasons":
        # Where the end would land under each season's own tuning gain (n = 4).
        for g in np.asarray(spread_vals, float):
            ax.hlines(top - g, x - BAR_W / 2 * 0.8, x + BAR_W / 2 * 0.8,
                      color="#555555", lw=0.9, zorder=5)
    else:
        # Per-run correction, anchored at the start mean (n = 80).
        _strip(ax, x, top + np.asarray(spread_vals, float), "#555555", rng,
               size=5.0, alpha=0.40)


def draw_panel(ax, d: dict, letter: str, rng) -> dict:
    xs = (0, 1, 2)
    s_start = _endbar(ax, xs[0], d["start"], rng)
    s_end = _endbar(ax, xs[2], d["end"], rng)

    top, bottom = s_start["mean"], s_end["mean"]
    if d["paired"]:
        _stepbar(ax, xs[1], top, bottom, d["step_runs"], rng, "runs")
    else:
        _stepbar(ax, xs[1], top, bottom, d["season_gain"].to_numpy(), rng, "seasons")

    # connectors
    for x0, y in ((xs[0], top), (xs[1], bottom)):
        ax.plot([x0 + BAR_W / 2, x0 + 1 - BAR_W / 2], [y, y], ls=(0, (2, 2)),
                lw=0.7, color="#555555", zorder=1)
    ax.axhline(0.0, color="#333333", lw=0.7, zorder=1)

    # value labels
    ax.annotate(f"{s_start['mean']:+.2f}", (xs[0], s_start["mean"] + s_start["sd"]),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                fontsize=7.5, fontweight="bold", color=C_BAR)
    ax.annotate(f"{s_end['mean']:+.2f}", (xs[2], s_end["mean"] + s_end["sd"]),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                fontsize=7.5, fontweight="bold", color=C_BAR)
    ax.annotate(f"{d['step']:+.2f}", (xs[1], (top + bottom) / 2.0),
                ha="center", va="center", fontsize=7.5, fontweight="bold",
                color="#333333",
                bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="none", alpha=0.75))

    # median / win-count annotations under each end bar
    kind = "paired" if d["paired"] else "one-sample"
    for x, st in ((xs[0], s_start), (xs[2], s_end)):
        ax.annotate(f"med {st['median']:+.2f}\n{st['wins']}/{st['n']} {kind}",
                    (x, 0.0), xytext=(0, -4), textcoords="offset points",
                    ha="center", va="top", fontsize=6.3, color="#444444")

    ax.set_xticks(xs)
    ax.set_xticklabels(d["labels"], fontsize=7)
    ax.set_xlim(-0.62, 2.62)
    ax.set_title(d["title"], fontsize=8, pad=10)
    ax.grid(axis="x", visible=False)
    ps.panel_label(ax, letter, dx=-0.13)
    ps.annotate_n(ax, d["test_note"], loc="lower left")
    return {"start": s_start, "end": s_end, "step": d["step"]}


def main() -> int:
    ps.use_style()
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    A, B = panel_a_data(), panel_b_data()
    rng = np.random.default_rng(RNG_SEED)

    fig, axes = ps.new_figure(ncols=2, width=ps.W2, height=7.6, sharey=True)
    out_a = draw_panel(axes[0], A, "a", rng)
    out_b = draw_panel(axes[1], B, "b", rng)

    axes[0].set_ylabel(r"EPI difference (EUR m$^{-2}$)")
    lo = min(np.min(A["start"]), np.min(A["end"]), np.min(B["start"]), np.min(B["end"]))
    hi = max(np.max(A["start"]), np.max(A["end"]), np.max(B["start"]), np.max(B["end"]))
    axes[0].set_ylim(lo - 2.6, hi + 1.9)

    handles = [
        Patch(facecolor=C_BAR, alpha=0.28, edgecolor=C_BAR, label="mean over runs"),
        Line2D([], [], color=C_MARK, lw=2.2, label="median"),
        Line2D([], [], marker="o", ls="", mfc="white", mec=C_MARK, mew=1.0,
               markersize=5, label="mean"),
        Line2D([], [], color=C_MARK, lw=0.8, label=r"$\pm$1 SD"),
        Line2D([], [], marker="o", ls="", color=C_BAR, alpha=0.5, markersize=3.2,
               label="one run"),
        Patch(facecolor=C_STEP, alpha=0.55, edgecolor="#555555", label="correction"),
    ]
    axes[0].legend(handles=handles, loc="upper right", ncol=2, fontsize=6.3,
                   handlelength=1.3, columnspacing=0.9, borderaxespad=0.2)

    fig.text(0.5, -0.045,
             "Positive = the raw library is ahead. "
             "Panel (a): both ends from n2_tune/tune_rb_n2.csv so the waterfall closes exactly. "
             "Panel (b): n7/main_n7.csv and final/main.csv (default) against the priced pool.",
             ha="center", va="top", fontsize=6.2, color="#444444")

    fig.tight_layout()
    # Two stems, as in make_fig1.py / make_fig6.py: the manuscript cites the
    # descriptive SPEC.md name, while the short name keeps the slot ordering
    # legible on disk. Both are written so 04-discussion.tex resolves.
    paths = []
    for stem in (STEM, STEM_SPEC):
        paths += ps.finish(fig, stem)
    plt.close(fig)

    verify(fig_paths=paths, out_a=out_a, out_b=out_b, A=A, B=B)
    return 0


# ---------------------------------------------------------------------------
# Verification: geometry actually drawn vs a direct recomputation
# ---------------------------------------------------------------------------

def verify(fig_paths, out_a, out_b, A, B) -> None:
    """Re-derive every plotted quantity straight from the CSVs and compare."""
    priced = ps.load_priced_pool()
    tune = ps.load_heuristic_tuning()
    n7 = ps.load_raw_library_default()
    fin = ps.load_default_main()

    stock = tune[tune["block"] == "stock_test"]["epi"].mean()
    tuned = tune[tune["block"] == "tuned_test"]["epi"].mean()
    raw_ens_p = priced[priced["method"] == "sindy_mpc_raw_ens"]["epi"].mean()
    lowthr_p = priced[priced["method"] == "sindy_mpc_lowthr"]["epi"].mean()
    raw_ens_d = n7[n7["method"] == "sindy_mpc_raw_ens"]["epi"].mean()
    lowthr_d = fin[fin["method"] == "sindy_mpc_lowthr"]["epi"].mean()

    checks = [
        ("a start", out_a["start"]["mean"], raw_ens_p - stock),
        ("a end", out_a["end"]["mean"], raw_ens_p - tuned),
        ("a step", out_a["step"], stock - tuned),
        ("b start", out_b["start"]["mean"], raw_ens_d - lowthr_d),
        ("b end", out_b["end"]["mean"], raw_ens_p - lowthr_p),
        ("b step", out_b["step"], (raw_ens_p - lowthr_p) - (raw_ens_d - lowthr_d)),
    ]
    print("\nplotted value            drawn        recomputed     |delta|")
    worst = 0.0
    for name, drawn, ref in checks:
        d = abs(drawn - ref)
        worst = max(worst, d)
        print(f"  {name:<10} {drawn:+12.6f} {ref:+14.6f}   {d:.2e}")
        if d > 1e-9:
            raise AssertionError(f"{name}: drawn {drawn} != recomputed {ref}")

    # the waterfalls must close on their own arithmetic
    for tag, o in (("a", out_a), ("b", out_b)):
        res = o["start"]["mean"] + o["step"] - o["end"]["mean"]
        print(f"  waterfall {tag} closes: "
              f"{o['start']['mean']:+.4f} {o['step']:+.4f} -> "
              f"{o['end']['mean']:+.4f}  (residual {res:.2e})")
        if abs(res) > 1e-9:
            raise AssertionError(f"waterfall {tag} does not close: residual {res}")

    print("\n  panel  bar     n   mean     median   SD     wins  IQR")
    for tag, d, o in (("a", A, out_a), ("b", B, out_b)):
        for pos in ("start", "end"):
            s = o[pos]
            print(f"  ({tag})   {pos:<6} {s['n']:>3} {s['mean']:+8.4f} "
                  f"{s['median']:+8.4f} {s['sd']:6.4f}  {s['wins']:>2}/{s['n']}  "
                  f"[{s['q25']:+.2f}, {s['q75']:+.2f}]")
    print(f"  (a) per-season tuning gain (n = {A['n_ref']}): "
          + ", ".join(f"{y}: {v:+.4f}" for y, v in A["season_gain"].items()))
    sr = A["season_gain"]
    print(f"      mean of the four = {sr.mean():+.4f} (= -step)")
    sb = B["step_runs"]
    print(f"  (b) per-run correction: n={sb.size} mean={sb.mean():+.4f} "
          f"median={np.median(sb):+.4f} SD={sb.std(ddof=1):.4f} "
          f"negative in {(sb < 0).sum()}/{sb.size}")

    for p in fig_paths:
        sz = Path(p).stat().st_size
        print(f"\nwrote {p}  ({sz/1024:.1f} kB)")
        if sz < 8_000:
            raise AssertionError(f"{p} is implausibly small ({sz} B)")


if __name__ == "__main__":
    raise SystemExit(main())
