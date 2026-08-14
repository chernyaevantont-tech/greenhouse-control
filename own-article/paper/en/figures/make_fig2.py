"""Figure 2 -- Pareto plane: economic margin against constraint pressure.

Spec: ``figures/SPEC.md``, section "Figure 2".  Single panel, MDPI single
column (8.5 cm).  Mean EPI (y) against mean ``violation_steps_total`` (x), one
marker per controller, SD bars where the replication is genuinely > 4, the
non-dominated set joined by a staircase, everything else grey, the tuned
heuristic labelled as dominated.

THREE HARNESSES ARE KEPT APART, deliberately (marker shape encodes which):

    priced  ``priced_main/*.csv`` + ``priced_dagger/*.csv``  7 SINDy-MPC + NN-MPC
    default ``final/main.csv``                               PPO, SAC, oracle MPC, stock heuristic
    tuning  ``n2_tune/tune_rb_n2.csv`` (``block == "tuned_test"``)  tuned heuristic

Every number drawn is computed here from those CSVs through ``_plotstyle``,
which owns the dedup key and the solver-abort rule.  Nothing is hardcoded; the
constants below are label text only.

Run:  python make_fig2.py            -> writes fig2_pareto_margin_violations.{pdf,png}
                                         and the aliases fig2.{pdf,png}
      python make_fig2.py --check    -> also re-reads the drawn artists and
                                         asserts they match a recomputation
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _plotstyle as ps  # noqa: E402

STEM = "fig2_pareto_margin_violations"
ALIAS = "fig2"

#: Compact point labels.  Long names do not fit an 8.5 cm panel; the full
#: names live in ``ps.METHOD_LABEL`` and in the caption.
SHORT = {
    "sindy_mpc_raw_ens":      "raw (ens.)",
    "sindy_mpc_raw":          "raw",
    "sindy_mpc_lowthr":       "low thr.",
    "sindy_mpc_dense":        "dense",
    "sindy_mpc_dense_dagger": "dense + re-ident.",
    "sindy_mpc_conf_dagger":  "frozen + re-ident.",
    "sindy_mpc_conf":         "frozen",
    "sindy_mpc_phys_ens":     "physics (ens.)",
    "sindy_mpc_phys":         "physics",
    "nn_mpc":                 "NN-MPC",
    "ppo":                    "PPO",
    "sac":                    "SAC",
    "oracle_mpc":             "oracle MPC",
    "rule_based":             "heuristic (stock)",
    "rule_based_tuned":       "heuristic (tuned)",
}

#: Harness -> marker.  The three pools are never averaged together, and the
#: reader has to be able to see which point came from which.
HARNESS_MARKER = {"priced": "o", "default": "^", "tuning": "s"}
HARNESS_LEGEND = {
    "priced":  "priced objective (SINDy-MPC, NN-MPC)",
    "default": "default objective (RL, oracle, stock)",
    "tuning":  "default objective, tuning wave",
}

#: Label placement, in typographic points relative to the marker.  Aesthetics
#: only -- the coordinates themselves come from the data.
OFFSET = {
    "sindy_mpc_raw_ens":      (-5.0,  5.0, "right", "bottom"),
    "sindy_mpc_raw":          (6.0,   1.0, "left",  "center"),
    "sindy_mpc_lowthr":       (-8.0,  1.0, "right", "center"),   # joint label
    "sindy_mpc_dense_dagger": (0.0,  -7.0, "center", "top"),
    "sindy_mpc_conf_dagger":  (-6.0,  4.0, "right", "bottom"),
    "sindy_mpc_conf":         (0.0,  -7.0, "center", "top"),
    # The two full-`physics` controllers entered the comparison on 2026-08-14
    # (regen/results/phys_lib/). They sit ~20 violation steps apart at +2.75 and
    # +2.48, so they are labelled on opposite sides to keep both readable.
    "sindy_mpc_phys_ens":     (8.0,   4.0, "left",  "bottom"),
    "sindy_mpc_phys":         (-8.0, -4.0, "right", "top"),
    "ppo":                    (0.0,   7.0, "center", "bottom"),
    "sac":                    (0.0,  -7.0, "center", "top"),
    "nn_mpc":                 (0.0,  -7.0, "center", "top"),
    "oracle_mpc":             (7.0,  -1.0, "left",  "center"),
    "rule_based":             (-7.0,  0.0, "right", "center"),
    "rule_based_tuned":       (9.0,  -7.0, "left",  "top"),
}

LABEL_BBOX = dict(facecolor="white", alpha=0.72, edgecolor="none",
                  boxstyle="square,pad=0.12")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def _replication(pool: pd.DataFrame) -> dict:
    """Per-method run count, and the EFFECTIVE count once determinism is seen.

    Both rule-based references are deterministic: their CSV rows repeat one
    value per season across seeds, so ``len(rows)`` overstates replication.
    A controller is called deterministic here when every season it was run in
    has more than one row and all of those rows carry the same EPI.  The
    effective n is then the number of distinct seasons.
    """
    out = {}
    for m, g in pool.groupby("method"):
        per_year_unique = g.groupby("test_year")["epi"].nunique()
        per_year_size = g.groupby("test_year")["epi"].size()
        det = bool((per_year_unique == 1).all() and (per_year_size > 1).all())
        years = sorted(g["test_year"].unique())
        out[m] = {
            "n_runs": int(len(g)),
            "years": years,
            "deterministic": det,
            "n_eff": int(len(years)) if det else int(len(g)),
            "truncated": int(np.asarray(g["truncated"], bool).sum())
            if "truncated" in g.columns else 0,
        }
    return out


def assemble() -> pd.DataFrame:
    """Build the 13-controller comparison table from the three harnesses."""
    priced = ps.load_library_pool()
    default = ps.load_default_main()
    tune = ps.load_heuristic_tuning()

    default_methods = ["ppo", "sac", "oracle_mpc", "rule_based"]
    default_sub = default[default["method"].isin(default_methods)].copy()

    tuned = tune[tune["block"] == "tuned_test"].copy()
    tuned["method"] = "rule_based_tuned"

    frames = []
    for harness, pool in (("priced", priced), ("default", default_sub),
                          ("tuning", tuned)):
        t = ps.controller_summary(pool)[
            ["method", "n", "epi", "epi_sd", "epi_se", "viol", "viol_sd"]]
        rep = _replication(pool)
        t["harness"] = harness
        t["n_runs"] = t["method"].map(lambda m: rep[m]["n_runs"])
        t["n_eff"] = t["method"].map(lambda m: rep[m]["n_eff"])
        t["deterministic"] = t["method"].map(lambda m: rep[m]["deterministic"])
        t["truncated"] = t["method"].map(lambda m: rep[m]["truncated"])
        t["years"] = t["method"].map(lambda m: tuple(rep[m]["years"]))
        frames.append(t)

    tab = pd.concat(frames, ignore_index=True)
    tab["on_front"] = ps.pareto_front(tab).values
    tab["library"] = tab["method"].map(ps.METHOD_LIBRARY)
    tab["label"] = tab["method"].map(lambda m: ps.METHOD_LABEL.get(m, m))
    missing = sorted(set(tab["method"]) - set(SHORT))
    if missing:
        raise KeyError(
            f"no short label for {missing}. Falling back to the raw method name "
            f"puts an underscore-laden identifier on the plot -- add the label.")
    tab["short"] = tab["method"].map(SHORT)
    tab = tab.sort_values("epi", ascending=False).reset_index(drop=True)

    # dominance count for the tuned heuristic, computed rather than asserted
    v, c = tab["epi"].to_numpy(float), tab["viol"].to_numpy(float)
    tab["dominated_by"] = [
        int(np.sum((v >= v[i]) & (c <= c[i]) & ((v > v[i]) | (c < c[i]))))
        for i in range(len(tab))
    ]
    tab.attrs["steps_expected"] = int(pd.unique(priced["steps_expected"])[0])
    tab.attrs["all_years"] = tuple(sorted(default["test_year"].unique()))
    return tab


def dagger_truncation_caveat() -> dict:
    """How much of ``dense + re-ident.``'s violation lead survives truncation.

    Its position on the front owes part of itself to runs that stopped early.
    Recomputed over completed runs only, the lead over ``dense`` shrinks.
    """
    p = ps.load_library_pool()
    dd = p[p["method"] == "sindy_mpc_dense_dagger"]
    de = p[p["method"] == "sindy_mpc_dense"]
    ddc = dd[~np.asarray(dd["truncated"], bool)]
    dec = de[~np.asarray(de["truncated"], bool)]
    return {
        "n_dagger": int(len(dd)),
        "truncated_dagger": int(np.asarray(dd["truncated"], bool).sum()),
        "lead_all": float(de["violation_steps_total"].mean()
                          - dd["violation_steps_total"].mean()),
        "lead_completed": float(dec["violation_steps_total"].mean()
                                - ddc["violation_steps_total"].mean()),
        "n_completed_dagger": int(len(ddc)),
        "n_completed_dense": int(len(dec)),
    }


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def _point_color(row) -> str:
    if not row.on_front:
        return ps.OKABE_ITO["grey"]
    lib = row.library
    if isinstance(lib, str):
        return ps.LIB_COLOR[lib]
    return ps.OKABE_ITO["green"]


def build():
    """Draw the panel.  Returns ``(fig, ax, table, notes)``."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    ps.use_style()
    tab = assemble()
    caveat = dagger_truncation_caveat()

    fig, ax = ps.new_figure(width=ps.W1, height=9.0)

    # --- dispersion first, so markers sit on top ---------------------------
    for row in tab.itertuples():
        col = _point_color(row)
        if row.n_eff > 4:                      # SD only where n > 4 (SPEC)
            ax.errorbar(row.viol, row.epi,
                        xerr=row.viol_sd, yerr=row.epi_sd,
                        fmt="none", ecolor=col, elinewidth=0.5,
                        capsize=1.2, capthick=0.5, alpha=0.5, zorder=2)

    # --- non-dominated staircase ------------------------------------------
    fr = tab[tab["on_front"]].sort_values("viol")
    ax.step(fr["viol"], fr["epi"], where="post",
            color=ps.OKABE_ITO["black"], lw=0.8, alpha=0.55, zorder=3)

    # --- dominance quadrant of the tuned heuristic ------------------------
    tuned = tab[tab["method"] == "rule_based_tuned"].iloc[0]
    ax.plot([ax.get_xlim()[0], tuned.viol], [tuned.epi, tuned.epi],
            ls=":", lw=0.5, color=ps.OKABE_ITO["grey"], zorder=1)
    ax.plot([tuned.viol, tuned.viol], [tuned.epi, tab["epi"].max()],
            ls=":", lw=0.5, color=ps.OKABE_ITO["grey"], zorder=1)

    ax.axhline(0.0, lw=0.5, ls="--", color="#BBBBBB", zorder=1)

    # --- markers -----------------------------------------------------------
    for row in tab.itertuples():
        col = _point_color(row)
        mk = HARNESS_MARKER[row.harness]
        ax.scatter([row.viol], [row.epi], marker=mk,
                   s=34 if row.on_front else 20,
                   facecolors=col, edgecolors="white" if row.on_front else col,
                   linewidths=0.6 if row.on_front else 0.4,
                   zorder=6 if row.on_front else 5)

    # --- point labels ------------------------------------------------------
    gap_epi = float(tab.set_index("method").loc["sindy_mpc_lowthr", "epi"]
                    - tab.set_index("method").loc["sindy_mpc_dense", "epi"])
    gap_viol = float(tab.set_index("method").loc["sindy_mpc_lowthr", "viol"]
                     - tab.set_index("method").loc["sindy_mpc_dense", "viol"])

    for row in tab.itertuples():
        if row.method == "sindy_mpc_dense":
            continue                            # labelled jointly with lowthr
        if row.method not in OFFSET:
            raise KeyError(
                f"no label placement for {row.method!r}. A controller entered "
                f"the pool without being placed -- add it to OFFSET rather than "
                f"letting it land on a default and silently overlap.")
        dx, dy, ha, va = OFFSET[row.method]
        txt = row.short
        size = 6.0
        if row.method == "sindy_mpc_lowthr":
            txt = (f"dense, low thr.\n(one controller, two thresholds:\n"
                   f"{abs(gap_epi):.4f} EUR m$^{{-2}}$ and "
                   f"{abs(gap_viol):.0f} steps apart)")
        elif row.method == "sindy_mpc_dense_dagger":
            txt = f"{row.short}$^{{\\dagger}}$"
        elif row.method == "rule_based_tuned":
            txt = f"{row.short}\ndominated by {row.dominated_by}"
        ax.annotate(txt, (row.viol, row.epi), textcoords="offset points",
                    xytext=(dx, dy), ha=ha, va=va, fontsize=size,
                    color="#222222", zorder=7, linespacing=1.15,
                    bbox=LABEL_BBOX)

    # --- axes --------------------------------------------------------------
    lo_x = float(np.nanmin(tab["viol"] - tab["viol_sd"].fillna(0)))
    hi_x = float(np.nanmax(tab["viol"] + tab["viol_sd"].fillna(0)))
    lo_y = float(np.nanmin(tab["epi"] - tab["epi_sd"].fillna(0)))
    hi_y = float(np.nanmax(tab["epi"] + tab["epi_sd"].fillna(0)))
    ax.set_xlim(lo_x - 0.10 * (hi_x - lo_x), hi_x + 0.12 * (hi_x - lo_x))
    ax.set_ylim(lo_y - 0.28 * (hi_y - lo_y), hi_y + 0.16 * (hi_y - lo_y))

    ax.set_xlabel(f"Mean violation steps per season "
                  f"(of {tab.attrs['steps_expected']})")
    ax.set_ylabel("Mean economic performance index (EUR m$^{-2}$)")

    handles = [Line2D([], [], ls="", marker=HARNESS_MARKER[h],
                      color="#555555", markersize=4, label=HARNESS_LEGEND[h])
               for h in ("priced", "default", "tuning")]
    handles.append(Line2D([], [], color=ps.OKABE_ITO["black"], lw=0.8,
                          alpha=0.55, label="non-dominated front"))
    ax.legend(handles=handles, loc="upper left", fontsize=6.0,
              handletextpad=0.5, borderpad=0.2, labelspacing=0.35)

    # --- replication and truncation notes ---------------------------------
    idx = tab.set_index("method")
    n_big = sorted({int(idx.loc[m, "n_eff"]) for m in
                    ("sindy_mpc_raw_ens", "ppo", "sac")})
    oracle_missing = sorted(set(tab.attrs["all_years"])
                            - set(idx.loc["oracle_mpc", "years"]))
    n_heur = sorted({int(idx.loc[m, "n_eff"]) for m in
                     ("rule_based", "rule_based_tuned")})
    note = (
        f"n = {n_big[0]} SINDy-MPC, PPO, SAC $\\cdot$ "
        f"{int(idx.loc['oracle_mpc', 'n_eff'])} oracle MPC "
        f"({', '.join(str(y) for y in oracle_missing)} aborted)\n"
        f"{int(idx.loc['nn_mpc', 'n_eff'])} NN-MPC $\\cdot$ "
        f"{n_heur[0]} both heuristics (deterministic, no SD bar)\n"
        f"$\\dagger$ {caveat['truncated_dagger']} of {caveat['n_dagger']} runs "
        f"truncated; lead over dense "
        f"{caveat['lead_all']:.0f} $\\rightarrow$ "
        f"{caveat['lead_completed']:.0f} steps if dropped"
    )
    ps.annotate_n(ax, note, loc="lower right")

    notes = {"caveat": caveat, "gap_epi": gap_epi, "gap_viol": gap_viol}
    fig.tight_layout()
    return fig, ax, tab, notes


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify(fig, ax, tab) -> None:
    """Re-read the drawn artists and compare them with a recomputation.

    The recomputation deliberately does not reuse :func:`assemble`: it goes
    back to the loaders, groups again, and checks the coordinates that ended
    up inside the matplotlib collections.
    """
    drawn = {}
    for coll in ax.collections:
        off = np.asarray(coll.get_offsets(), float)
        if off.shape[0] == 1:
            drawn[(round(off[0, 0], 6), round(off[0, 1], 6))] = True

    priced = ps.load_library_pool()
    default = ps.load_default_main()
    tune = ps.load_heuristic_tuning()
    tuned = tune[tune["block"] == "tuned_test"]

    recomputed = {}
    for m, g in priced.groupby("method"):
        recomputed[m] = (g["violation_steps_total"].mean(), g["epi"].mean())
    for m in ("ppo", "sac", "oracle_mpc", "rule_based"):
        g = default[default["method"] == m]
        recomputed[m] = (g["violation_steps_total"].mean(), g["epi"].mean())
    recomputed["rule_based_tuned"] = (tuned["violation_steps_total"].mean(),
                                      tuned["epi"].mean())

    assert len(recomputed) == len(tab), (len(recomputed), len(tab))
    for row in tab.itertuples():
        x, y = recomputed[row.method]
        assert abs(x - row.viol) < 1e-9, (row.method, x, row.viol)
        assert abs(y - row.epi) < 1e-9, (row.method, y, row.epi)
        key = (round(float(row.viol), 6), round(float(row.epi), 6))
        assert key in drawn, f"{row.method} not found among drawn markers"

    front = set(tab.loc[tab["on_front"], "method"])
    brute = set()
    for row in tab.itertuples():
        dom = any((o.epi >= row.epi) and (o.viol <= row.viol)
                  and ((o.epi > row.epi) or (o.viol < row.viol))
                  for o in tab.itertuples() if o.method != row.method)
        if not dom:
            brute.add(row.method)
    assert front == brute, (front, brute)
    print(f"verify: {len(tab)} markers match a direct recomputation; "
          f"front = {sorted(front)}")


def main() -> None:
    fig, ax, tab, notes = build()
    out = ps.finish(fig, STEM) + ps.finish(fig, ALIAS)

    cols = ["method", "harness", "n_runs", "n_eff", "epi", "epi_sd",
            "viol", "viol_sd", "truncated", "on_front"]
    print(tab[cols].to_string(index=False,
                              float_format=lambda v: f"{v:10.4f}"))
    fr = tab[tab["on_front"]].sort_values("viol")
    print("\nfront (by violation steps):")
    print(fr[["method", "epi", "viol"]].to_string(
        index=False, float_format=lambda v: f"{v:10.4f}"))
    print(f"\ndense vs low thr.: {abs(notes['gap_epi']):.4f} EUR/m2, "
          f"{abs(notes['gap_viol']):.1f} steps apart")
    print(f"dense + re-ident.: {notes['caveat']['truncated_dagger']} of "
          f"{notes['caveat']['n_dagger']} truncated, violation lead "
          f"{notes['caveat']['lead_all']:.1f} -> "
          f"{notes['caveat']['lead_completed']:.1f} steps over completed runs")

    if "--check" in sys.argv:
        verify(fig, ax, tab)
    for p in out:
        print(f"wrote {p}  ({p.stat().st_size / 1024:.1f} kB)")


if __name__ == "__main__":
    main()
