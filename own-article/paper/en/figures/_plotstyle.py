"""Shared plotting layer for the figures of the English *Agronomy* manuscript.

Every figure script in this directory imports this module and nothing else that
touches data.  The point is that the three rules that make the numbers correct
live in exactly one place:

  R1  Every number traces to a file under ``own-article/regen/results``.
      The loaders below take paths only from :data:`RESULTS`; nothing here
      accepts a literal value.

  R2  Deduplicate on the run identity before averaging -- waves were resumed and
      the CSVs overlap -- and drop rows that are *solver aborts*
      (``truncated`` AND ``solver_failures >= max_solver_failures``, or
      ``stop_reason == "solver_aborted"`` where that column exists).
      See :func:`dedup` and :func:`usable`.

  R3  A simulator-terminated season is an OUTCOME, not a defect, and is kept.
      Only a solver abort -- where the controller never produced an action --
      is uninformative.  This mirrors ``regen/make_tables.py:_usable`` exactly;
      if that function ever changes, change this one with it.

House style follows MDPI: serif type at ~8 pt, 8.5 cm single-column and
17.5 cm double-column figure widths, vector PDF plus a 600 dpi PNG, and the
colour-blind-safe Okabe--Ito palette.

Usage
-----
    import _plotstyle as ps
    ps.use_style()
    fig, axes = ps.new_figure(ncols=3, width=ps.W2, height=6.0)
    ...
    ps.finish(fig, "fig1_selection_and_conditioning")

Run this file directly for a self-test that loads every pool and prints the
row counts the manuscript quotes.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent                      # .../paper/en/figures
PAPER_EN = HERE.parent                                       # .../paper/en
REPO = PAPER_EN.parents[2]                                   # .../greenhouse-control
RESULTS = REPO / "own-article" / "regen" / "results"
FIGDIR = HERE

if not RESULTS.is_dir():                                     # pragma: no cover
    raise RuntimeError(f"results tree not found at {RESULTS}")

# ---------------------------------------------------------------------------
# Constants that must agree with regen/regen_config.py
# ---------------------------------------------------------------------------

MAX_SOLVER_FAILURES = 100        # regen_config.MAX_SOLVER_FAILURES
STEPS_EXPECTED = 5760            # 60 days at 900 s
IN_DIST_YEAR = 2020
TEST_YEARS = (2020, 2021, 2022, 2023)
NOMINAL_FRUIT_PRICE = 1.6        # EUR/kg, make_tables.NOMINAL_FRUIT_PRICE
SENS_FRUIT_PRICE = (0.8, 1.6, 3.2)
SENS_ENERGY_SCALE = (0.5, 1.0, 2.0)
DIVERGENCE_GATE = 0.05           # applied threshold; declared only qualitatively

# ---------------------------------------------------------------------------
# House style
# ---------------------------------------------------------------------------

CM = 1.0 / 2.54
W1 = 8.5 * CM                    # MDPI single column, inches
W2 = 17.5 * CM                   # MDPI double column, inches
W15 = 13.0 * CM                  # intermediate, for 2-panel rows

#: Okabe--Ito, safe under deuteranopia, protanopia and tritanopia.
OKABE_ITO = {
    "black":     "#000000",
    "orange":    "#E69F00",
    "skyblue":   "#56B4E9",
    "green":     "#009E73",
    "yellow":    "#F0E442",
    "blue":      "#0072B2",
    "vermilion": "#D55E00",
    "purple":    "#CC79A7",
    "grey":      "#999999",
}
PALETTE = [OKABE_ITO[k] for k in
           ("blue", "vermilion", "green", "orange", "purple", "skyblue", "yellow", "black")]

#: Feature libraries, in the order the ladder ranks them by conditioning.
#:
#: That order is a fact about the FEATURE MATRIX, not about closed-loop economics.
#: Conditioning orders the open-loop rollout cleanly and the closed-loop EPI
#: WRONGLY: the worst-conditioned library (``physics``, kappa 53.4) beats the
#: middle one (``physics_no_cross``, kappa 24.5) roughly tenfold in closed loop.
#: See :func:`library_one_factor`.  Never plot kappa as if it ranked controllers.
LIB_ORDER = ("raw", "physics_no_cross", "physics")
LIB_COLOR = {
    "raw":              OKABE_ITO["blue"],
    "physics_no_cross": OKABE_ITO["orange"],
    "physics":          OKABE_ITO["vermilion"],
}
LIB_LABEL = {
    "raw":              "raw",
    "physics_no_cross": "physics, no cross terms",
    "physics":          "physics",
}
#: Marker per sparse estimator, used wherever the degree-1 block is plotted.
OPT_MARKER = {"stlsq": "o", "ensemble": "s", "constrained": "^", "sr3": "v"}

#: Which library each closed-loop controller was identified on.  ``None`` marks
#: a controller that is not a SINDy-MPC and therefore has no library.
METHOD_LIBRARY = {
    "sindy_mpc_raw":          "raw",
    "sindy_mpc_raw_ens":      "raw",
    "sindy_mpc_conf":         "physics_no_cross",
    "sindy_mpc_conf_dagger":  "physics_no_cross",
    "sindy_mpc_dense":        "physics_no_cross",
    "sindy_mpc_dense_dagger": "physics_no_cross",
    "sindy_mpc_lowthr":       "physics_no_cross",
    "sindy_mpc_phys":         "physics",
    "sindy_mpc_phys_ens":     "physics",
    "nn_mpc":                 None,
    "oracle_mpc":             None,
    "ppo":                    None,
    "sac":                    None,
    "rule_based":             None,
    "rule_based_tuned":       None,
}

#: The ONE-FACTOR library comparison.  Every controller below is
#: ``library_degree = 1``, ``denoise = "none"``, ``threshold = 0.05``; the only
#: thing that differs across a row is ``feature_variant``.  Recipes:
#: ``regen_config.CONFIRMATORY`` (l. 93), ``RAW_ENS`` (l. 155), ``PHYS_ENS``
#: (l. 173), ``RAW_STLSQ`` (l. 148), ``PHYS_STLSQ`` (l. 180).
#:
#: There is NO ``physics_no_cross`` controller at STLSQ/0.05 -- ``dense`` is
#: threshold 1e-3 and ``lowthr`` 1e-6, so neither completes the STLSQ row.  Say
#: "two of three" rather than implying a full replicate.
LIBRARY_ONE_FACTOR = {
    "ensemble": {"raw":              "sindy_mpc_raw_ens",
                 "physics_no_cross": "sindy_mpc_conf",
                 "physics":          "sindy_mpc_phys_ens"},
    "stlsq":    {"raw":              "sindy_mpc_raw",
                 "physics":          "sindy_mpc_phys"},
}

#: Display names.  ``*_dagger`` is a RUN LABEL from the CSVs, never an
#: imitation-learning claim -- the aggregation loop has no expert and no DAgger
#: framing (REVISION_LOG G-6).  Render it as "on-policy re-identification".
METHOD_LABEL = {
    "sindy_mpc_raw":          "SINDy-MPC, raw",
    "sindy_mpc_raw_ens":      "SINDy-MPC, raw (ensemble)",
    "sindy_mpc_conf":         "SINDy-MPC, frozen recipe",
    "sindy_mpc_conf_dagger":  "SINDy-MPC, frozen + re-ident.",
    "sindy_mpc_dense":        "SINDy-MPC, dense",
    "sindy_mpc_dense_dagger": "SINDy-MPC, dense + re-ident.",
    "sindy_mpc_lowthr":       "SINDy-MPC, low threshold",
    "sindy_mpc_phys":         "SINDy-MPC, physics",
    "sindy_mpc_phys_ens":     "SINDy-MPC, physics (ensemble)",
    "nn_mpc":                 "NN-MPC",
    "oracle_mpc":             "oracle MPC",
    "ppo":                    "PPO",
    "sac":                    "SAC",
    "rule_based":             "heuristic (stock)",
    "rule_based_tuned":       "heuristic (tuned)",
}


def use_style() -> None:
    """Apply the manuscript's rcParams.  Call once, before creating figures."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from cycler import cycler

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8,
        "axes.titlesize": 8,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "figure.titlesize": 9,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#DDDDDD",
        "grid.linewidth": 0.4,
        "axes.axisbelow": True,
        "axes.prop_cycle": cycler("color", PALETTE),
        "lines.linewidth": 1.1,
        "lines.markersize": 4.0,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "legend.frameon": False,
        "legend.handlelength": 1.6,
        "figure.dpi": 300,
        "savefig.dpi": 600,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,          # embed TrueType, not Type-3: MDPI requires it
        "ps.fonttype": 42,
    })


def new_figure(ncols: int = 1, nrows: int = 1, width: float = W1,
               height: float | None = None, **kw):
    """Create a figure sized in MDPI column units.  ``height`` is centimetres."""
    import matplotlib.pyplot as plt
    h = (height * CM) if height is not None else (width * 0.72 * nrows)
    fig, axes = plt.subplots(nrows, ncols, figsize=(width, h), **kw)
    return fig, axes


def panel_label(ax, letter: str, dx: float = -0.16, dy: float = 1.04) -> None:
    """Bold lower-case panel tag, matching the ``\\textbf{a}`` in the captions."""
    ax.text(dx, dy, f"({letter})", transform=ax.transAxes,
            fontsize=9, fontweight="bold", va="bottom", ha="left")


def finish(fig, stem: str, formats=("pdf", "png")) -> list[Path]:
    """Save under :data:`FIGDIR` as ``stem.pdf`` (vector) and ``stem.png`` (600 dpi)."""
    out = []
    for ext in formats:
        p = FIGDIR / f"{stem}.{ext}"
        fig.savefig(p, format=ext)
        out.append(p)
    return out


# ---------------------------------------------------------------------------
# Rule 2: dedup and the abort filter
# ---------------------------------------------------------------------------

def usable(d: pd.DataFrame) -> pd.DataFrame:
    """Drop solver aborts, keep simulator-terminated seasons.

    Mirrors ``regen/make_tables.py:_usable``.  A truncated season where the
    solver still produced actions is a real economic outcome -- excluding it
    would flatter precisely the controllers that wreck the greenhouse.
    """
    if "stop_reason" in d.columns:
        return d[d["stop_reason"] != "solver_aborted"].copy()
    if "truncated" not in d.columns:
        return d.copy()
    tr = d["truncated"].astype(bool)
    thr = d["max_solver_failures"] if "max_solver_failures" in d.columns else MAX_SOLVER_FAILURES
    sf = d.get("solver_failures", pd.Series(0, index=d.index)).fillna(0)
    return d[~(tr & (sf >= thr))].copy()


def dedup(d: pd.DataFrame, keys) -> pd.DataFrame:
    """Deduplicate on the run identity, keeping the first occurrence.

    Resumed waves rewrite whole rows, so duplicates are exact repeats of the
    same (config_hash, seed) cell; ``keep="first"`` is the convention used by
    every table in the manuscript.
    """
    keys = [k for k in keys if k in d.columns]
    return d.drop_duplicates(subset=keys, keep="first").copy()


def _read_many(patterns) -> pd.DataFrame:
    """Concatenate every CSV matching the glob patterns, relative to RESULTS."""
    if isinstance(patterns, (str, os.PathLike)):
        patterns = [patterns]
    files: list[str] = []
    for pat in patterns:
        hits = sorted(glob.glob(str(RESULTS / pat)))
        if not hits:
            raise FileNotFoundError(f"no CSV matched {RESULTS / pat}")
        files.extend(hits)
    frames = [pd.read_csv(f) for f in files]
    out = pd.concat(frames, ignore_index=True)
    out.attrs["source_files"] = [str(Path(f).relative_to(RESULTS)) for f in files]
    out.attrs["rows_before_dedup"] = len(out)
    return out


def load_runs(patterns, keys=("method", "seed", "test_year"),
              drop_aborts: bool = True) -> pd.DataFrame:
    """Generic closed-loop loader: read, dedup on ``keys``, drop solver aborts."""
    raw = _read_many(patterns)
    n_raw = len(raw)
    d = dedup(raw, keys)
    n_ded = len(d)
    if drop_aborts:
        d = usable(d)
    d.attrs.update(raw.attrs)
    d.attrs["rows_before_dedup"] = n_raw
    d.attrs["rows_after_dedup"] = n_ded
    d.attrs["rows_after_abort_filter"] = len(d)
    return d


# ---------------------------------------------------------------------------
# Named pools -- one function per block the manuscript cites
# ---------------------------------------------------------------------------

def load_priced_pool() -> pd.DataFrame:
    """Main closed-loop comparison under the PRICED stage cost.

    Eight files: ``priced_main/*.csv`` (six) and ``priced_dagger/*.csv`` (two).
    707 rows -> 600 after dedup on (method, seed, test_year); the abort rule
    removes none.  ``main_priced_seeds0-3.csv`` is a strict subset after dedup.
    Eight controllers: 20 seeds x 4 seasons each, except ``nn_mpc`` at 10 seeds
    (40 runs) -- replication is NOT equal, state it wherever it matters.
    """
    d = load_runs(["priced_main/*.csv", "priced_dagger/*.csv"])
    d.attrs["objective"] = "priced"
    return d


def load_default_main() -> pd.DataFrame:
    """Canonical wave under the DEFAULT objective (``final/main.csv``).

    Ten controllers.  Supplies PPO, SAC, oracle MPC and the stock heuristic to
    the Pareto plane -- the SINDy rows here are default-objective and must NOT
    be mixed with the priced pool for the same controller.
    """
    d = load_runs("final/main.csv")
    d.attrs["objective"] = "default"
    return d


def load_heuristic_tuning() -> pd.DataFrame:
    """16-trial tuning wave of the rule-based reference (``n2_tune``).

    Blocks ``stock_test`` and ``tuned_test`` hold the four-season test scores.
    Both are DETERMINISTIC: n = 4, no run-to-run variance, so every comparison
    against them is a one-sample signed-rank test against a constant, whose
    minimum attainable two-sided p at n = 4 is 0.125.  Never label it "paired".

    The stock heuristic appears in TWO harnesses: -1.2264 here and -1.2061 in
    ``final/main.csv``.  Use this file at both ends of the tuning waterfall so
    it closes exactly; the 0.02 difference is cross-environment drift.
    """
    d = load_runs("n2_tune/tune_rb_n2.csv", keys=("block", "seed", "test_year"))
    d.attrs["objective"] = "default"
    return d


def load_raw_library_default() -> pd.DataFrame:
    """Raw-library controllers under the DEFAULT objective (``n7/main_n7.csv``).

    The default-objective end of the library-effect waterfall.  Two methods,
    20 seeds x 4 seasons.
    """
    d = load_runs("n7/main_n7.csv")
    d.attrs["objective"] = "default"
    return d


def load_physlib_pool() -> pd.DataFrame:
    """Closed-loop runs on the FULL ``physics`` library (``phys_lib/``).

    ``sindy_mpc_phys`` (STLSQ) and ``sindy_mpc_phys_ens`` (ensemble), both at
    threshold 0.05, 20 seeds x 4 seasons = 160 rows, priced objective, zero
    truncated runs and zero solver aborts.  Measured 2026-08-13, after the
    English draft was written.

    ``phys_lib/main_physchk.csv`` is deliberately NOT loaded: it is a 288-step
    smoke check at horizon 8 (a season is 5760 steps at horizon 20) and pooling
    it would mix two experiments.  The glob ``main_physlib*.csv`` excludes it.

    PROVENANCE.  Same ``config_hash`` (637c6b535a9e), objective and horizon as
    :func:`load_priced_pool`, but a later ``git_sha`` (97b66f9).  The two pools
    are comparable by configuration; the commit difference is worth a caption
    line, not a caveat.

    WHAT THIS POOL KILLED.  It closes the conditioning series, and the closed-loop
    EPI turns out to be NON-MONOTONE in kappa (+4.32 / +0.28 / +2.75 for
    kappa 8.2 / 24.5 / 53.4).  Any figure that presents conditioning as the
    closed-loop mechanism is wrong (REVISION_LOG 2026-08-13).
    """
    d = load_runs(["phys_lib/main_physlib*.csv"])
    d.attrs["objective"] = "priced"
    return d


def load_library_pool() -> pd.DataFrame:
    """:func:`load_priced_pool` and :func:`load_physlib_pool`, concatenated.

    Adds ``library`` (from :data:`METHOD_LIBRARY`) and ``boiler_alive``
    (``xi_uboil != 0``).  Both halves are the priced objective, horizon 20,
    config 637c6b535a9e; the schemas are identical column for column.
    """
    a, b = load_priced_pool(), load_physlib_pool()
    d = pd.concat([a, b], ignore_index=True)
    d["library"] = d["method"].map(METHOD_LIBRARY)
    d["boiler_alive"] = (d["xi_uboil"].fillna(0.0).abs() > 0).astype(float)
    d.attrs["source_files"] = list(a.attrs["source_files"]) + list(b.attrs["source_files"])
    d.attrs["rows_before_dedup"] = a.attrs["rows_before_dedup"] + b.attrs["rows_before_dedup"]
    d.attrs["rows_after_dedup"] = a.attrs["rows_after_dedup"] + b.attrs["rows_after_dedup"]
    d.attrs["objective"] = "priced"
    return d


def library_one_factor(optimizer: str = "ensemble") -> pd.DataFrame:
    """The one-factor library comparison: only ``feature_variant`` changes.

    One row per library, in :data:`LIB_ORDER`.  ``epi_se_seed`` is the standard
    error over SEED MEANS, not over runs: the identified model -- and therefore
    ``xi_uboil`` -- is a property of the seed, and the four seasons of one seed
    are not independent replicates of it.  Quote the seed-level error.

    ``survival`` is the fraction of the 20 SEEDS whose fit kept the direct
    boiler coefficient, with a Wilson 95% interval (:func:`wilson`).

    CAVEAT THAT MUST TRAVEL WITH THIS TABLE.  Survival orders these three
    libraries because they differ in nothing else.  It is NOT a general
    predictor across the wider controller pool: ``sindy_mpc_conf_dagger``
    survives at 0.85 and scores +1.66, below ``sindy_mpc_raw_ens`` at 0.55.
    """
    pool = load_library_pool()
    mapping = LIBRARY_ONE_FACTOR[optimizer]
    rows = []
    for lib in LIB_ORDER:
        method = mapping.get(lib)
        if method is None:
            continue
        g = pool[pool["method"] == method]
        seed_mean = g.groupby("seed")["epi"].mean()
        seed_alive = g.groupby("seed")["boiler_alive"].first()
        k = int(seed_alive.sum())
        lo, hi = wilson(k, len(seed_alive))
        rows.append({
            "library": lib, "method": method, "optimizer": optimizer,
            "n_runs": int(len(g)), "n_seeds": int(len(seed_mean)),
            "n_years": int(g["test_year"].nunique()),
            "epi": float(g["epi"].mean()), "epi_sd": float(g["epi"].std()),
            "epi_median": float(g["epi"].median()),
            "epi_se_seed": float(seed_mean.std(ddof=1) / np.sqrt(len(seed_mean))),
            "survival": float(seed_alive.mean()),
            "survival_k": k, "survival_lo": lo, "survival_hi": hi,
            "heat_kwh_m2": float(g["energy_heat_kwh_m2"].mean()),
            "truncated": int(np.asarray(g["truncated"], bool).sum()),
        })
    t = pd.DataFrame(rows)
    t.attrs["objective"] = "priced"
    t.attrs["source_files"] = pool.attrs["source_files"]
    return t


def boiler_coefficients(optimizer: str = "ensemble") -> pd.DataFrame:
    """Per-seed identified boiler coefficient for the one-factor library set.

    One row per (library, seed): ``xi_uboil`` as written by the fit, and
    ``alive`` = it survived the 0.05 threshold.

    ONLY SURVIVORS ARE OBSERVABLE.  A coefficient the threshold cut is recorded
    as exactly 0.0, so the pre-threshold magnitude of a cut term does not exist
    in these files.  A panel drawn from this table may show how far the
    SURVIVING coefficients sit above the cut; it may not claim anything about
    how far the cut ones sat below it.
    """
    pool = load_library_pool()
    mapping = LIBRARY_ONE_FACTOR[optimizer]
    rows = []
    for lib in LIB_ORDER:
        method = mapping.get(lib)
        if method is None:
            continue
        g = pool[pool["method"] == method]
        per_seed = g.groupby("seed").agg(xi_uboil=("xi_uboil", "first"),
                                         n_runs=("epi", "size"),
                                         epi=("epi", "mean"))
        # the model is fitted once per seed: guard the assumption rather than trust it
        spread = g.groupby("seed")["xi_uboil"].nunique().max()
        if spread > 1:                                       # pragma: no cover
            raise AssertionError(f"{method}: xi_uboil varies within a seed")
        per_seed = per_seed.reset_index()
        per_seed["library"], per_seed["method"] = lib, method
        rows.append(per_seed)
    t = pd.concat(rows, ignore_index=True)
    t["abs_xi"] = t["xi_uboil"].abs()
    t["alive"] = (t["abs_xi"] > 0).astype(bool)
    return t


def library_feature_names() -> dict[str, list[str]]:
    """Feature-name list of each library, parsed out of the experiment module.

    This is the one STRUCTURAL fact the figures need that is not in a results
    CSV: which library contains the bilinear ``t_uBoil`` term.  Rather than
    retyping it, the three module-level constants of
    ``own-article/article_experiment_utils.py`` are read with :mod:`ast` and
    resolved, so the figure cannot drift from the code that built the fits.

    ``compute_feature_matrix`` (l. 516) maps
    ``raw -> RAW_FEATURE_NAMES``, ``physics -> PHYSICS_FEATURE_NAMES``,
    ``physics_no_cross -> PHYSICS_NO_CROSS_NAMES``; the CasADi mirror used
    inside the MPC (l. 840) builds the same three vectors.
    """
    import ast

    src = REPO / "own-article" / "article_experiment_utils.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    env: dict[str, list[str]] = {}

    def ev(node):
        if isinstance(node, ast.List):
            vals = [n.value for n in node.elts
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            return vals if len(vals) == len(node.elts) else None
        if isinstance(node, ast.Name):
            return list(env[node.id]) if node.id in env else None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            a, b = ev(node.left), ev(node.right)
            return None if a is None or b is None else a + b
        return None

    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            v = ev(node.value)
            if v is not None:
                env[node.targets[0].id] = v

    out = {"raw": env["RAW_FEATURE_NAMES"],
           "physics_no_cross": env["PHYSICS_NO_CROSS_NAMES"],
           "physics": env["PHYSICS_FEATURE_NAMES"]}
    for lib, names in out.items():
        if not names:                                        # pragma: no cover
            raise AssertionError(f"could not resolve feature names for {lib}")
    return out


#: Name of the bilinear temperature x boiler term inside the ``physics``
#: library.  ``run_regen.CROSS_TERM`` (l. 469) -- it is ``t_uBoil``, NOT
#: ``t_in*uBoil``.
CROSS_TERM = "t_uBoil"
#: Name of the direct boiler feature; ``xi_uboil`` in every results CSV is its
#: identified coefficient.
DIRECT_TERM = "uBoil"


def library_structure() -> pd.DataFrame:
    """Per-library structure: size, direct boiler term, bilinear detour."""
    names = library_feature_names()
    return pd.DataFrame([{
        "library": lib,
        "n_features": len(names[lib]),
        "has_direct": DIRECT_TERM in names[lib],
        "has_cross": CROSS_TERM in names[lib],
        "features": names[lib],
    } for lib in LIB_ORDER])


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval for a proportion.  Correct at k = 0 and k = n."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (float(max(0.0, c - h)), float(min(1.0, c + h)))


def holm(pvalues: dict) -> dict:
    """Holm-Bonferroni step-down adjustment over a NAMED family of tests.

    The family must be stated wherever the adjusted values are quoted: the same
    raw p becomes 6.4e-4 in a family of two and 1.3e-3 in a family of four.
    """
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m, out, prev = len(items), {}, 0.0
    for i, (key, p) in enumerate(items):
        adj = min(1.0, max(prev, (m - i) * float(p)))
        prev = adj
        out[key] = adj
    return out


def load_ladder(degree: int | None = 1, denoise: str | None = "none",
                optimizers=None) -> pd.DataFrame:
    """Identification ladder, 72 labels x 20 seeds = 1440 rows.

    Defaults select the degree-1, undenoised block (240 rows).  Pass
    ``optimizers=("stlsq", "ensemble")`` for the sparse-estimator block the
    headline reversal is stated over (120 rows, 40 per library).

    SCOPE WARNING.  The reversal holds in the degree-1 undenoised sparse block.
    Pooled over all 72 labels the RAW library has the best mean one-step RMSE
    (2.7035 vs 2.9750 vs 3.4544) and there is no reversal.  Do not plot the
    whole grid under a caption that claims one.

    ``sign_pass`` is NaN in all 1440 rows: the declared transparency gate was
    never evaluated.  Do not encode it.
    """
    d = _read_many(["ladder_rerun/ladder_rerun.csv", "ladder_rerun/ladder_rerun2.csv"])
    n_raw = len(d)
    d = dedup(d, ("variant", "degree", "optimizer", "denoise", "seed"))
    if degree is not None:
        d = d[d["degree"] == degree]
    if denoise is not None:
        d = d[d["denoise"] == denoise]
    if optimizers is not None:
        d = d[d["optimizer"].isin(list(optimizers))]
    d = d.copy()
    d["variant"] = pd.Categorical(d["variant"], categories=list(LIB_ORDER), ordered=True)
    d["passes_gate"] = (d["diverged_frac"].fillna(1.0) <= DIVERGENCE_GATE) & \
                       d["embeddable"].fillna(False).astype(bool)
    d.attrs["rows_before_dedup"] = n_raw
    return d


def ladder_summary(d: pd.DataFrame) -> pd.DataFrame:
    """Per-library ladder statistics, in the exact reductions the paper quotes.

    One-step and kappa as MEANS, rollout as a MEDIAN -- the rollout
    distribution is heavy-tailed and its mean is not the quoted statistic.
    """
    g = (d.groupby("variant", observed=True)
           .agg(n=("kappa", "size"),
                kappa=("kappa", "mean"),
                kappa_sd=("kappa", "std"),
                one_step=("one_step_rmse_t_in", "mean"),
                one_step_sd=("one_step_rmse_t_in", "std"),
                rollout_median=("rollout_rmse_t_in", "median"),
                rollout_q25=("rollout_rmse_t_in", lambda x: x.quantile(0.25)),
                rollout_q75=("rollout_rmse_t_in", lambda x: x.quantile(0.75)),
                diverged=("diverged_frac", "mean"))
           .reset_index())
    return g


def load_mechanism(objective: str = "priced") -> pd.DataFrame:
    """Mechanism block, season 2020, 20 replicates per condition.

    ``objective="priced"``  -> ``priced_mech/mechanism_pricedMech*.csv``
                               (405 rows -> 400 after dedup)
    ``objective="default"`` -> ``final/mechanism*.csv`` (400 rows, no dupes)

    Blocks: ``lambda`` (13 levels), ``knock`` (baseline/knockin/knockout),
    ``cross``.  ``xi_uboil`` carries the boiler coefficient, so survival is
    ``xi_uboil != 0``.
    """
    if objective == "priced":
        pats = ["priced_mech/mechanism_pricedMech.csv",
                "priced_mech/mechanism_pricedMech2.csv"]
    elif objective == "default":
        pats = ["final/mechanism.csv"]
    else:
        raise ValueError(f"objective must be 'priced' or 'default', got {objective!r}")
    raw = _read_many(pats)
    n_raw = len(raw)
    d = usable(dedup(raw, ("block", "condition", "seed", "test_year")))
    d["boiler_alive"] = (d["xi_uboil"].fillna(0.0).abs() > 0).astype(float)
    d.attrs.update(raw.attrs)
    d.attrs["rows_before_dedup"] = n_raw
    d.attrs["objective"] = objective
    return d


def lambda_sweep(objective: str = "priced", test_year: int = IN_DIST_YEAR) -> pd.DataFrame:
    """EPI and boiler-term survival against the sparsity threshold lambda."""
    d = load_mechanism(objective)
    L = d[(d["block"] == "lambda") & (d["test_year"] == test_year)]
    g = (L.groupby("lam")
           .agg(n=("epi", "size"), epi_mean=("epi", "mean"), epi_sd=("epi", "std"),
                epi_median=("epi", "median"), survival=("boiler_alive", "mean"))
           .reset_index().sort_values("lam"))
    g["objective"] = objective
    return g


def knock_effects(objective: str = "priced", test_year: int = IN_DIST_YEAR) -> pd.DataFrame:
    """Per-replicate knock-in and knock-out effects, paired on the seed.

    Returns one row per seed with ``knockin`` and ``knockout`` deltas against
    the same replicate's baseline.

    The knock-in MEDIAN is the reported statistic: +3.05 EUR/m2 under the
    defective objective, +0.21 under the priced one.  +3.05 is a RETRACTED
    magnitude (REVISION_LOG G-6) and may appear only beside its replacement.
    Under the priced objective the mean (+1.92) is nine times the median, so
    quoting the mean restates the retracted number in disguise.
    """
    d = load_mechanism(objective)
    k = d[(d["block"] == "knock") & (d["test_year"] == test_year)]
    piv = k.pivot_table(index="seed", columns="condition", values="epi")
    out = pd.DataFrame({
        "baseline": piv["baseline"],
        "knockin_epi": piv["knockin"],
        "knockout_epi": piv["knockout"],
        "knockin": piv["knockin"] - piv["baseline"],
        "knockout": piv["knockout"] - piv["baseline"],
    }).reset_index()
    out.attrs["objective"] = objective
    return out


def load_design() -> pd.DataFrame:
    """Design / sensitivity block: ``priced_design/design_pricedDesign*.csv``.

    307 rows -> 280 after dedup on (factor, value, seed, test_year, rep).
    Factors: ``coef_perturb`` (200 rows, 5 levels x 40), ``mpc_horizon``,
    ``stlsq_threshold``.

    MISLABELLED DIRECTORY.  Despite the name, these runs use the ORIGINAL
    objective -- ``experiments_support.py`` hard-codes ``objective="full"`` in
    every supporting block.  Never caption them as priced.
    """
    raw = _read_many(["priced_design/design_pricedDesign.csv",
                      "priced_design/design_pricedDesign2.csv"])
    n_raw = len(raw)
    d = usable(dedup(raw, ("factor", "value", "seed", "test_year", "rep")))
    d.attrs.update(raw.attrs)
    d.attrs["rows_before_dedup"] = n_raw
    d.attrs["objective"] = "default (directory name is wrong)"
    return d


def coef_perturbation() -> pd.DataFrame:
    """Run-level EPI per coefficient-perturbation level, plus early terminations."""
    d = load_design()
    return d[d["factor"] == "coef_perturb"].copy()


def price_grid(recompute: bool = True) -> pd.DataFrame:
    """Price-sensitivity grid: 10 controllers x 3 fruit prices x 3 energy scales.

    Recomputed here from ``final/main.csv`` by the same formula
    ``make_tables.table_prices`` uses, then cross-checked against the derived
    ``final/tables/sensitivity_prices.csv``.

    TWO RESTRICTIONS, both of which belong in any caption that uses this:
    it RE-SCORES fixed trajectories rather than re-optimising, and NEITHER
    raw-library controller is in it -- so it says nothing about the ranking the
    paper actually reports.
    """
    base = load_default_main()
    base = base[base["test_year"] == IN_DIST_YEAR]
    rows = []
    for pf in SENS_FRUIT_PRICE:
        for ke in SENS_ENERGY_SCALE:
            j = (base["revenue"] * (pf / NOMINAL_FRUIT_PRICE)
                 - ke * (base["cost_heat"] + base["cost_co2"] + base["cost_elec"]))
            g = base.assign(j=j).groupby("method")["j"].mean().reset_index()
            g["fruit_price"], g["energy_scale"] = pf, ke
            rows.append(g)
    t = pd.concat(rows, ignore_index=True)
    if recompute:
        ref = RESULTS / "final" / "tables" / "sensitivity_prices.csv"
        if ref.exists():
            r = pd.read_csv(ref)
            m = t.merge(r, on=["method", "fruit_price", "energy_scale"],
                        suffixes=("", "_ref"))
            delta = float(np.nanmax(np.abs(m["j"] - m["j_ref"]))) if len(m) else np.nan
            t.attrs["max_abs_delta_vs_derived_csv"] = delta
            if np.isfinite(delta) and delta > 1e-6:      # pragma: no cover
                raise AssertionError(
                    f"price grid disagrees with {ref} by {delta:.3e}")
    t.attrs["excluded_controllers"] = ["sindy_mpc_raw", "sindy_mpc_raw_ens"]
    return t


# ---------------------------------------------------------------------------
# Recurring panel helpers
# ---------------------------------------------------------------------------

def controller_summary(pool: pd.DataFrame, value: str = "epi",
                       cost: str = "violation_steps_total",
                       group: str = "method") -> pd.DataFrame:
    """Per-controller mean/SD/n of the value and cost axes of the Pareto plane."""
    g = (pool.groupby(group)
              .agg(n=(value, "size"),
                   epi=(value, "mean"), epi_sd=(value, "std"),
                   epi_se=(value, lambda x: x.std(ddof=1) / max(np.sqrt(len(x)), 1)),
                   viol=(cost, "mean"), viol_sd=(cost, "std"),
                   truncated=("truncated", lambda x: int(np.asarray(x, bool).sum()))
                   if "truncated" in pool.columns else (value, "size"))
              .reset_index().sort_values("epi", ascending=False))
    g["label"] = g[group].map(lambda m: METHOD_LABEL.get(m, m))
    return g


def pareto_front(t: pd.DataFrame, value: str = "epi",
                 cost: str = "viol") -> pd.Series:
    """Boolean mask of the non-dominated set: maximise ``value``, minimise ``cost``.

    On the assembled comparison pool this returns exactly five members.  Two of
    them, ``sindy_mpc_dense`` and ``sindy_mpc_lowthr``, are ONE controller under
    two thresholds and differ by 0.0066 EUR/m2 and 5 violation steps -- say so
    rather than letting "five controllers" stand unqualified.
    """
    v, c = t[value].to_numpy(float), t[cost].to_numpy(float)
    dominated = np.zeros(len(t), dtype=bool)
    for i in range(len(t)):
        dominated[i] = bool(np.any((v >= v[i]) & (c <= c[i]) &
                                   ((v > v[i]) | (c < c[i]))))
    return pd.Series(~dominated, index=t.index, name="on_front")


def paired_deltas(pool: pd.DataFrame, a: str, b: str,
                  keys=("seed", "test_year"), value: str = "epi") -> pd.Series:
    """EPI(a) - EPI(b) paired on (seed, test_year).  Both must be stochastic.

    Do NOT use this against either rule-based reference: they are deterministic
    and the correct test is one-sample against a constant (see
    :func:`deltas_vs_constant`).
    """
    keys = list(keys)
    sa = pool[pool["method"] == a].set_index(keys)[value]
    sb = pool[pool["method"] == b].set_index(keys)[value]
    return (sa - sb).dropna()


def deltas_vs_constant(pool: pd.DataFrame, method: str,
                       constant_by_year: pd.Series, value: str = "epi") -> pd.Series:
    """Run-level margin of ``method`` over a DETERMINISTIC per-season constant.

    Returns one value per run.  Any win count derived from this is a one-sample
    comparison against a constant, not a paired test -- label it that way.
    """
    g = pool[pool["method"] == method]
    return (g[value].to_numpy()
            - g["test_year"].map(constant_by_year).to_numpy())


def boiler_survival(pool: pd.DataFrame) -> pd.DataFrame:
    """Fraction of runs whose identified model retained the boiler coefficient."""
    d = pool.copy()
    d["boiler_alive"] = (d["xi_uboil"].fillna(0.0).abs() > 0).astype(float)
    return (d.groupby("method")
              .agg(survival=("boiler_alive", "mean"), n=("boiler_alive", "size"))
              .reset_index().sort_values("survival"))


def scatter_by_library(ax, d: pd.DataFrame, x: str, y: str, size=None,
                       gate_col: str = "passes_gate", legend: bool = True):
    """Ladder scatter coloured by feature library, marker by optimizer.

    Open faces mark configurations that FAIL the divergence gate
    (``diverged_frac > 0.05``).  That threshold was applied as a hard cut in
    ``make_tables.py:318`` but declared only qualitatively in the protocol --
    a pre-registration deviation the manuscript reports honestly.
    """
    for lib in LIB_ORDER:
        sub = d[d["variant"] == lib]
        if not len(sub):
            continue
        for opt, mk in OPT_MARKER.items():
            s2 = sub[sub["optimizer"] == opt]
            if not len(s2):
                continue
            passes = s2[gate_col].astype(bool) if gate_col in s2 else np.ones(len(s2), bool)
            area = (size(s2) if callable(size) else 18.0)
            ax.scatter(s2[x][passes], s2[y][passes], s=area if np.isscalar(area) else np.asarray(area)[np.asarray(passes)],
                       marker=mk, facecolors=LIB_COLOR[lib], edgecolors=LIB_COLOR[lib],
                       linewidths=0.5, alpha=0.85, zorder=3)
            ax.scatter(s2[x][~passes], s2[y][~passes],
                       s=area if np.isscalar(area) else np.asarray(area)[~np.asarray(passes)],
                       marker=mk, facecolors="none", edgecolors=LIB_COLOR[lib],
                       linewidths=0.6, alpha=0.85, zorder=3)
    if legend:
        from matplotlib.lines import Line2D
        handles = [Line2D([], [], marker="o", ls="", color=LIB_COLOR[l],
                          label=LIB_LABEL[l], markersize=4) for l in LIB_ORDER]
        ax.legend(handles=handles, loc="best")
    return ax


def strip_with_median_and_mean(ax, groups, values, positions=None, color=None,
                              jitter: float = 0.06, rng_seed: int = 0):
    """Per-run strip plot with a heavy median tick and an OPEN mean symbol.

    The two markers are the point: wherever a mean sits far from its median the
    effect is a tail, not a shift.  Both the perturbation grid and the knock-in
    contrast are read this way.
    """
    rng = np.random.default_rng(rng_seed)
    positions = list(range(len(groups))) if positions is None else list(positions)
    color = color or OKABE_ITO["blue"]
    for pos, g in zip(positions, groups):
        v = np.asarray(values[g], float)
        v = v[np.isfinite(v)]
        xs = pos + rng.uniform(-jitter, jitter, size=len(v))
        ax.scatter(xs, v, s=6, color=color, alpha=0.45, linewidths=0, zorder=2)
        med, mean = np.median(v), np.mean(v)
        ax.hlines(med, pos - 0.22, pos + 0.22, color=color, lw=2.0, zorder=4)
        ax.scatter([pos], [mean], s=26, facecolors="none", edgecolors=color,
                   linewidths=1.0, zorder=5)
    return ax


def annotate_n(ax, text: str, loc: str = "lower right") -> None:
    """Small corner note for replication counts and scope limits."""
    xy = {"lower right": (0.98, 0.03, "right", "bottom"),
          "lower left": (0.02, 0.03, "left", "bottom"),
          "upper right": (0.98, 0.97, "right", "top"),
          "upper left": (0.02, 0.97, "left", "top")}[loc]
    ax.text(xy[0], xy[1], text, transform=ax.transAxes, fontsize=6.5,
            color="#444444", ha=xy[2], va=xy[3])


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _selftest() -> None:
    use_style()
    print(f"results root : {RESULTS}")

    lad = load_ladder(optimizers=("stlsq", "ensemble"))
    print(f"\nladder      : {lad.attrs['rows_before_dedup']} raw -> "
          f"{len(lad)} in the degree-1 undenoised sparse block")
    print(ladder_summary(lad)[["variant", "n", "kappa", "one_step",
                               "rollout_median", "diverged"]].to_string(index=False))

    p = load_priced_pool()
    print(f"\npriced pool : {p.attrs['rows_before_dedup']} raw -> "
          f"{p.attrs['rows_after_dedup']} dedup -> {len(p)} usable")
    t = controller_summary(p)
    t["on_front"] = pareto_front(t).values
    print(t[["method", "n", "epi", "epi_sd", "viol"]].head(4).to_string(index=False))

    fin = load_default_main()
    tune = load_heuristic_tuning()
    stock = tune[tune["block"] == "stock_test"]["epi"].mean()
    tuned = tune[tune["block"] == "tuned_test"]["epi"].mean()
    raw_ens = p[p["method"] == "sindy_mpc_raw_ens"]["epi"].mean()
    print(f"\nwaterfall a : {raw_ens - stock:+.4f} - {tuned - stock:+.4f} = "
          f"{raw_ens - tuned:+.4f}  (closes exactly, both ends from n2_tune)")
    n7 = load_raw_library_default()
    gap_d = (n7[n7["method"] == "sindy_mpc_raw_ens"]["epi"].mean()
             - fin[fin["method"] == "sindy_mpc_lowthr"]["epi"].mean())
    gap_p = raw_ens - p[p["method"] == "sindy_mpc_lowthr"]["epi"].mean()
    print(f"waterfall b : {gap_d:+.4f} default -> {gap_p:+.4f} priced "
          f"(step {gap_p - gap_d:+.4f})")

    # Pareto over the assembled pool
    rows = controller_summary(p)[["method", "n", "epi", "epi_sd", "viol"]]
    others = controller_summary(fin[fin["method"].isin(
        ["ppo", "sac", "oracle_mpc", "rule_based"])])[["method", "n", "epi", "epi_sd", "viol"]]
    tt = tune[tune["block"] == "tuned_test"]
    trow = pd.DataFrame([{"method": "rule_based_tuned", "n": len(tt),
                          "epi": tt["epi"].mean(), "epi_sd": tt["epi"].std(),
                          "viol": tt["violation_steps_total"].mean()}])
    allc = pd.concat([rows, others, trow], ignore_index=True)
    allc["on_front"] = pareto_front(allc).values
    print(f"\npareto      : {int(allc.on_front.sum())} non-dominated -> "
          f"{sorted(allc.loc[allc.on_front, 'method'])}")

    for obj in ("default", "priced"):
        k = knock_effects(obj)
        print(f"knock-in {obj:<7}: n={len(k)} median={k.knockin.median():+.4f} "
              f"mean={k.knockin.mean():+.4f} positive={int((k.knockin > 0).sum())}/{len(k)}")
        s = lambda_sweep(obj)
        alive = s[s.survival > 0].lam.max()
        dead = s[s.survival == 0].lam.min()
        print(f"lambda   {obj:<7}: {len(s)} levels, survival falls to 0 between "
              f"{alive:g} and {dead:g}")

    cp = coef_perturbation()
    print(f"\ndesign      : {cp.attrs['rows_before_dedup']} raw -> "
          f"{len(load_design())} dedup, {len(cp)} coef_perturb rows")
    print(cp.groupby("value").agg(n=("epi", "size"), mean=("epi", "mean"),
                                  median=("epi", "median")).to_string())

    pg = price_grid()
    print(f"\nprice grid  : {len(pg)} cells, "
          f"max |delta| vs derived CSV = {pg.attrs.get('max_abs_delta_vs_derived_csv'):.2e}; "
          f"excluded: {pg.attrs['excluded_controllers']}")

    surv = boiler_survival(p)
    print("\nboiler survival (priced pool):",
          ", ".join(f"{r.method.replace('sindy_mpc_', '')}={r.survival:.2f}"
                    for r in surv.itertuples()))

    # smoke-test the drawing helpers
    fig, axes = new_figure(ncols=2, width=W2, height=6.0)
    scatter_by_library(axes[0], lad, "one_step_rmse_t_in", "rollout_rmse_t_in")
    axes[0].set_yscale("log")
    panel_label(axes[0], "a")
    k = knock_effects("priced")
    strip_with_median_and_mean(axes[1], ["knockin", "knockout"],
                               {"knockin": k.knockin, "knockout": k.knockout})
    panel_label(axes[1], "b")
    annotate_n(axes[1], "n = 20")
    out = finish(fig, "_selftest")
    print(f"\nwrote {[str(o.name) for o in out]}")
    for o in out:
        o.unlink()
    print("self-test OK")


if __name__ == "__main__":
    _selftest()
