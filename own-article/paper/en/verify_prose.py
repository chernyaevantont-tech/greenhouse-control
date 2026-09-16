"""Recompute the numbers the manuscript states in running text, not in table cells.

`verify_tables.py` covers the sixteen tables. This covers the prose: every sentence in the
body that asserts a quantity is anchored by a short piece of its own wording, the quantity
is recomputed from `regen/results/`, and the two are compared at half a unit in the last
printed digit -- the same standard the table verifier applies.

    python verify_prose.py                 # every implemented passage
    python verify_prose.py ladder holdout  # only these

Anchoring on the sentence rather than on a bare number matters: the same value often
appears in several places for different reasons, and a check that matched any occurrence
would pass while the claim it belongs to had drifted.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "figures"))
sys.path.insert(0, str(HERE))
import _plotstyle as ps  # noqa: E402
from verify_tables import TEX, cmp, digits_tol, full_pool, nums  # noqa: E402
import verify_tables as vt  # noqa: E402

CHECKS: dict[str, callable] = {}


def passage(name):
    def deco(fn):
        CHECKS[name] = fn
        return fn
    return deco


# ---------------------------------------------------------------------------
# Reading the prose
# ---------------------------------------------------------------------------

def body() -> str:
    """The manuscript's running text: tables and provenance comments removed."""
    tex = re.sub(r"(?m)^%%.*$", "", TEX.read_text(encoding="utf-8"))
    tex = re.sub(r"\\begin\{table\}.*?\\end\{table\}", " ", tex, flags=re.S)
    return tex.split(r"\begin{thebibliography}")[0]


_BODY: str | None = None


def sentence(anchor: str) -> str:
    """The sentence containing `anchor`, which must occur exactly once.

    A missing or duplicated anchor is itself a failure: it means the wording moved and the
    check is no longer pointed at the claim it was written for.
    """
    global _BODY
    if _BODY is None:
        _BODY = " ".join(body().split())
    hits = _BODY.count(anchor)
    if hits != 1:
        raise LookupError(f"anchor occurs {hits} times: {anchor!r}")
    i = _BODY.index(anchor)
    start = max(_BODY.rfind(". ", 0, i), _BODY.rfind("-- ", 0, i)) + 1
    end = _BODY.find(". ", i + len(anchor))
    return _BODY[start:end if end > 0 else len(_BODY)]


def stated(anchor: str, pattern: str, group: int = 1) -> float:
    """One number out of the sentence carrying `anchor`, located by `pattern`."""
    s = sentence(anchor)
    m = re.search(pattern, s)
    if not m:
        raise LookupError(f"pattern {pattern!r} not in: {s[:160]}")
    return float(m.group(group))


def check(name: str, what: str, got, anchor: str, pattern: str, group: int = 1,
          tol: float | None = None, scale: float = 1.0) -> None:
    """Recompute one stated quantity and compare at the printed precision.

    `scale` is for values the manuscript writes in scientific notation: pass the power of
    ten and the mantissa read out of the sentence is multiplied by it, so the comparison
    and the recorded value are both in the quantity's own units. Recording the bare
    mantissa instead would leave the printed number unaccounted for by the coverage gate.
    """
    try:
        want = stated(anchor, pattern, group)
    except LookupError as exc:
        cmp(name, f"{what}: {exc}", float("nan"), float("nan"), 0.0)
        return
    if tol is None:
        text = sentence(anchor)
        mm = re.search(re.escape(f"{want:g}").replace(r"\.", r"\.") + r"\d*", text)
        printed = mm.group(0) if mm else f"{want}"
        tol = digits_tol(printed, want)
    cmp(name, what, got, want * scale, tol * scale)


def _holm(pvals: dict, family: int) -> dict:
    """Step-down with monotone enforcement over a declared family size."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    out, prev = {}, 0.0
    for i, (k, pv) in enumerate(items):
        adj = min(1.0, max(prev, (family - i) * float(pv)))
        prev = adj
        out[k] = adj
    return out


# ---------------------------------------------------------------------------
# Section 3.1 -- the identification ladder
# ---------------------------------------------------------------------------

@passage("ladder")
def check_ladder_prose():
    """The divergent-realisation artefact, and the dominating comparator."""
    lad = ps.load_ladder(optimizers=None)
    phys = lad[lad["variant"] == "physics"]["rollout_rmse_t_in"]
    check("ladder", "physics mean rollout", float(phys.mean()),
          "is an artefact of divergent realisations", r"\$(\d+\.\d+)\\,\^\\circ")
    check("ladder", "physics rollout q75", float(phys.quantile(0.75)),
          "upper rollout quartile", r"quartile \$(\d+\.\d+)\$")

    # the pre-specified pick against the raw/degree-1/STLSQ comparator, on the three axes
    full = ps.load_ladder(degree=None, denoise=None, optimizers=None)
    a = full[(full["variant"] == "raw") & (full["degree"] == 1)
             & (full["optimizer"] == "stlsq") & (full["denoise"] == "none")]
    b = full[(full["variant"] == "physics_no_cross") & (full["degree"] == 1)
             & (full["optimizer"] == "ensemble") & (full["denoise"] == "none")]
    anchor = "dominates it simultaneously on all three applied open-loop axes"
    check("ladder", "comparator rollout (raw)", float(a["rollout_rmse_t_in"].mean()),
          anchor, r"mean rollout RMSE \$(\d+\.\d+)\$")
    check("ladder", "comparator rollout (selected)", float(b["rollout_rmse_t_in"].mean()),
          anchor, r"vs\.\\? \$(\d+\.\d+)\\,\^\\circ")
    check("ladder", "comparator diverged (raw)", float(a["diverged_frac"].mean()),
          anchor, r"diverged fraction \$(\d+\.\d+)\$")
    check("ladder", "comparator diverged (selected)", float(b["diverged_frac"].mean()),
          anchor, r"diverged fraction \$\d+\.\d+\$ vs\.\\? \$(\d+\.\d+)\$")
    check("ladder", "comparator terms (raw)", float(a["nonzero"].mean()),
          anchor, r"active terms \$(\d+\.\d+)\$")
    check("ladder", "comparator terms (selected)", float(b["nonzero"].mean()),
          anchor, r"active terms \$\d+\.\d+\$ vs\.\\? \$(\d+\.\d+)\$")


# ---------------------------------------------------------------------------
# Section 3.1 -- the held-out identification block
# ---------------------------------------------------------------------------

@passage("holdout")
def check_holdout_prose():
    """Held-out/in-sample median ratios, and the per-fit-year medians."""
    d = pd.read_csv(ps.RESULTS / "holdout" / "holdout_holdout.csv")
    anchor = "reproduces the library ordering in both regimes"
    names = {"raw": "raw", "physics_no_cross": r"physics\\_no\\_cross", "physics": "physics"}
    for lib, tag in names.items():
        sub = d[d["variant"] == lib]
        out = float(sub[~sub["in_sample"].astype(bool)]["rollout_rmse_t_in"].median())
        ins = float(sub[sub["in_sample"].astype(bool)]["rollout_rmse_t_in"].median())
        check("holdout", f"{lib} held-out/in-sample ratio", out / ins, anchor,
              r"\$\\times (\d+\.\d+)\$ \(" + tag + r"\)")

    anchor2 = "median rollout error on 2018 versus 2019 data is"
    for lib, tag in (("raw", "raw"), ("physics_no_cross", r"physics\\_no\\_cross"),
                     ("physics", "physics")):
        sub = d[d["variant"] == lib]
        for year, which in ((2018, 1), (2019, 2)):
            got = float(sub[sub["eval_year"] == year]["rollout_rmse_t_in"].median())
            check("holdout", f"{lib} eval {year}", got, anchor2,
                  r"\$(\d+\.\d+)/(\d+\.\d+)\$ for " + tag + r"(?![\\\w])", group=which)


# ---------------------------------------------------------------------------
# Section 3.2 -- the two harnesses, and the setpoint search
# ---------------------------------------------------------------------------

@passage("harness")
def check_harness_prose():
    """The same deterministic controller under two harnesses, and the tuned setpoints."""
    main = ps.load_default_main()
    tune = ps.load_heuristic_tuning()
    a = main[main["method"] == "rule_based"]
    b = tune[tune["block"] == "stock_test"]
    anchor = "amplify platform-level floating-point differences"
    check("harness", "rule_based in the main harness", -float(a["epi"].mean()), anchor,
          r"evaluates to \$-(\d+\.\d+)\$ EUR", tol=0.00005)
    cmp("harness", "rule_based in the main harness (sign)",
        1.0 if float(a["epi"].mean()) < 0 else 0.0, 1.0, 0.0)
    check("harness", "rule_based in the tuning harness", -float(b["epi"].mean()), anchor,
          r"and \$-(\d+\.\d+)\$ in the tuning harness", tol=0.00005)

    sel = tune[tune["block"] == "tuned_test"].iloc[0]
    anchor2 = "The selected solution is agronomically interpretable"
    check("harness", "selected day setpoint", float(sel["temp_setpoint_day"]), anchor2,
          r"day setpoint \$(\d+\.\d+)\$")
    check("harness", "selected night setpoint", float(sel["temp_setpoint_night"]), anchor2,
          r"night \$(\d+\.\d+)\$")


# ---------------------------------------------------------------------------
# Section 3.3 -- the paired comparisons around Table 7
# ---------------------------------------------------------------------------

@passage("paired")
def check_paired_prose():
    """The fifteenth family member, the two raw variants, and the dense/lowthr pair."""
    from scipy.stats import wilcoxon

    pool = full_pool()
    tune = ps.load_heuristic_tuning()
    tuned = tune[tune["block"] == "tuned_test"].set_index("test_year")["epi"]
    stock = tune[tune["block"] == "stock_test"].set_index("test_year")["epi"]
    years = [2020, 2021, 2022, 2023]
    d = np.array([float(stock[y] - tuned[y]) for y in years])

    anchor = "The fifteenth member of the correction family"
    check("paired", "stock-in-tuning-harness delta mean", -float(d.mean()), anchor,
          r"\$\\Delta\$ mean \$-(\d+\.\d+)\$", tol=0.005)
    cmp("paired", "stock-in-tuning-harness delta sign",
        1.0 if d.mean() < 0 else 0.0, 1.0, 0.0)
    cmp("paired", "stock-in-tuning-harness wins", int((d > 0).sum()), 0.0, 0.0)
    cmp("paired", "stock-in-tuning-harness n", len(d), 4.0, 0.0)
    check("paired", "signed-rank floor at n=4", float(wilcoxon(d)[1]), anchor,
          r"cannot fall below \$p=(\d+\.\d+)\$")

    dd = np.asarray(ps.paired_deltas(pool, "sindy_mpc_raw_ens", "sindy_mpc_raw"), float)
    dd = dd[~np.isnan(dd)]
    anchor2 = "In a separate paired comparison between the two raw variants"
    check("paired", "raw variants delta median", -float(np.median(dd)), anchor2,
          r"median \$-(\d+\.\d+)\$", tol=0.0005)
    cmp("paired", "raw variants delta median sign",
        1.0 if np.median(dd) < 0 else 0.0, 1.0, 0.0)
    check("paired", "raw variants p", float(wilcoxon(dd)[1]), anchor2,
          r"\$p=(\d+\.\d+)\$", tol=0.005)

    de = np.asarray(ps.paired_deltas(pool, "sindy_mpc_dense", "sindy_mpc_lowthr"), float)
    de = de[~np.isnan(de)]
    anchor3 = "are effectively one controller under the priced objective"
    check("paired", "dense/lowthr mean |delta|", float(np.abs(de).mean()), anchor3,
          r"\|\\Delta\|=(\d+\.\d+)\$")
    check("paired", "dense four-season mean", float(pool[pool.method == "sindy_mpc_dense"]["epi"].mean()),
          anchor3, r"means \$(\d+\.\d+)\$", tol=0.00005)
    check("paired", "lowthr four-season mean", float(pool[pool.method == "sindy_mpc_lowthr"]["epi"].mean()),
          anchor3, r"vs\.\\? \$(\d+\.\d+)\$", tol=0.00005)
    check("paired", "dense/lowthr p", float(wilcoxon(de)[1]), anchor3,
          r"returns \$p=(\d+\.\d+)\$", tol=0.0005)


# ---------------------------------------------------------------------------
# Section 3.4 -- the 17-feature library
# ---------------------------------------------------------------------------

@passage("notuboil")
def check_notuboil_prose():
    """The term-deletion library: conditioning, open-loop instability, and its contrasts."""
    from scipy.stats import wilcoxon

    arm_all = pd.read_csv(ps.RESULTS / "notuboil" / "ladder_notuboil.csv")
    # conditioning is a property of the fit and is identical across the two arms; the
    # rollout and divergence figures the sentence quotes are the ensemble arm's.
    arm = arm_all[arm_all["optimizer"] == "ensemble"]
    full = ps.load_ladder(optimizers=None)
    anchor = "It keeps the full library's conditioning"
    check("notuboil", "notuboil kappa", float(arm_all["kappa"].mean()), anchor,
          r"\\kappa = (\d+\.\d+)\$")
    check("notuboil", "physics kappa", float(full[full.variant == "physics"]["kappa"].mean()),
          anchor, r"against \$(\d+\.\d+)\$")
    check("notuboil", "notuboil rollout median",
          float(arm["rollout_rmse_t_in"].median()), anchor,
          r"median rollout \$(\d+\.\d+)\$")
    check("notuboil", "notuboil divergence", float(arm["diverged_frac"].mean()), anchor,
          r"divergence \$(\d+\.\d+)\$")

    pool = pd.concat([ps.load_library_pool(), ps.load_notuboil_pool()], ignore_index=True)
    d = np.asarray(ps.paired_deltas(pool, "sindy_mpc_notuboil_ens", "sindy_mpc_conf"), float)
    d = d[~np.isnan(d)]
    anchor2 = "That is significantly above the middle library"
    check("notuboil", "vs middle: mean paired difference", float(d.mean()), anchor2,
          r"difference \$\+(\d+\.\d+)\$")
    cmp("notuboil", "vs middle: wins", int((d > 0).sum()), 62.0, 0.0)
    cmp("notuboil", "vs middle: n", len(d), 80.0, 0.0)

    e = np.asarray(ps.paired_deltas(pool, "sindy_mpc_notuboil_ens", "sindy_mpc_phys_ens"),
                   float)
    e = e[~np.isnan(e)]
    check("notuboil", "vs full: median", -float(np.median(e)), anchor2,
          r"median \$-(\d+\.\d+)\$", tol=0.005)
    f = np.asarray(ps.paired_deltas(pool, "sindy_mpc_notuboil", "sindy_mpc_phys"), float)
    f = f[~np.isnan(f)]
    check("notuboil", "STLSQ arm not separable", float(wilcoxon(f)[1]), anchor2,
          r"not separable, \$p = (\d+\.\d+)\$")

    # The four contrasts of this block, as the deposited analysis names them: the
    # term-deletion library against the full physics library and against the middle one,
    # under each estimator, with the STLSQ arm's second comparison made against RAW.
    family = {}
    for a, b in (("sindy_mpc_notuboil_ens", "sindy_mpc_phys_ens"),
                 ("sindy_mpc_notuboil_ens", "sindy_mpc_conf"),
                 ("sindy_mpc_notuboil", "sindy_mpc_phys"),
                 ("sindy_mpc_notuboil", "sindy_mpc_raw")):
        x = np.asarray(ps.paired_deltas(pool, a, b), float)
        x = x[~np.isnan(x)]
        family[(a, b)] = float(wilcoxon(x)[1])
    adj = ps.holm(family)
    check("notuboil", "vs middle: p_Holm over the four contrasts",
          adj[("sindy_mpc_notuboil_ens", "sindy_mpc_conf")], anchor2,
          r"p_\{\\text\{Holm\}\} = (\d+\.\d+)\\times10\^\{-6\}", scale=1e-6)
    check("notuboil", "vs full: p_Holm over the four contrasts",
          adj[("sindy_mpc_notuboil_ens", "sindy_mpc_phys_ens")], anchor2,
          r"p_\{\\text\{Holm\}\} = (\d+\.\d+)\\times10\^\{-3\}", scale=1e-3)


# ---------------------------------------------------------------------------
# Section 3.3 -- what repricing the stage cost bought
# ---------------------------------------------------------------------------

@passage("repricing")
def check_repricing_prose():
    """Per-controller gain from the price-aligned stage cost, and the library-effect gap."""
    priced = ps.load_library_pool()
    default = pd.concat([ps.load_default_main(), ps.load_raw_library_default()],
                        ignore_index=True)

    def gain(method):
        a = priced[priced["method"] == method]["epi"]
        b = default[default["method"] == method]["epi"]
        return float(a.mean() - b.mean())

    anchor = "with violations falling from"
    check("repricing", "repricing gain, dense", gain("sindy_mpc_dense"), anchor,
          r"\$\+(\d+\.\d+)\$ and \$\+\d+\.\d+\$ EUR")
    check("repricing", "repricing gain, lowthr", gain("sindy_mpc_lowthr"), anchor,
          r"and \$\+(\d+\.\d+)\$ EUR")
    check("repricing", "repricing gain, raw_ens", gain("sindy_mpc_raw_ens"), anchor,
          r"against \$\+(\d+\.\d+)\$ and")
    check("repricing", "repricing gain, raw", gain("sindy_mpc_raw"), anchor,
          r"and \$\+(\d+\.\d+)\$ for the raw-library")

    ratios = [gain(a) / gain(b)
              for a in ("sindy_mpc_dense", "sindy_mpc_lowthr")
              for b in ("sindy_mpc_raw_ens", "sindy_mpc_raw")]
    check("repricing", "smallest gain ratio", min(ratios), anchor,
          r"ratio of \$(\d+\.\d+)\$ to")
    check("repricing", "largest gain ratio", max(ratios), anchor,
          r"to \$(\d+\.\d+)\$ depending")

    # the same two controllers' violation means, before and after repricing
    five = ["sindy_mpc_dense", "sindy_mpc_lowthr"]
    before = default[default["method"].isin(five)]["violation_steps_total"].mean()
    after = priced[priced["method"].isin(five)]["violation_steps_total"].mean()
    check("repricing", "violations before repricing", float(before), anchor,
          r"falling from \$\\sim\$(\d+) to", tol=0.5)
    check("repricing", "violations after repricing", float(after), anchor,
          r"to \$\\sim\$(\d+), against", tol=0.5)

    anchor2 = "Against the full"
    a = float(priced[priced["method"] == "sindy_mpc_raw_ens"]["epi"].mean())
    b = float(priced[priced["method"] == "sindy_mpc_phys_ens"]["epi"].mean())
    check("repricing", "priced gap vs full physics", a - b, anchor2,
          r"priced gap is \$\+(\d+\.\d+)\$")
    check("repricing", "raw_ens priced mean", a, anchor2,
          r"\(\$(\d+\.\d+)\$ against", tol=0.00005)
    check("repricing", "phys_ens priced mean", b, anchor2,
          r"against \$(\d+\.\d+)\$\)", tol=0.00005)


# ---------------------------------------------------------------------------
# Section 3.4 -- the like-for-like comparison on the original objective
# ---------------------------------------------------------------------------

@passage("likeforlike")
def check_likeforlike_prose():
    """The same four controllers on 2020--2023 under the original objective."""
    d = ps.load_default_main()
    anchor = "Compared like for like"
    for method, pat, sign in (
            ("sindy_mpc_dense", r"dense variant scores \$\+(\d+\.\d+)\$", +1),
            ("sindy_mpc_conf", r"the frozen recipe \$-(\d+\.\d+)\$", -1),
            ("rule_based", r"the heuristic \$-(\d+\.\d+)\$", -1)):
        sub = d[d["method"] == method]["epi"]
        check("likeforlike", method, sign * float(sub.mean()), anchor, pat)


# ---------------------------------------------------------------------------
# Section 3.5 -- the sparsity levels that retain the boiler term
# ---------------------------------------------------------------------------

@passage("levels")
def check_levels_prose():
    """Levels at which at least one seed keeps the boiler coefficient, against the rest."""
    anchor = "Levels at which at least one seed retains the term average"
    spec = [
        ("priced retaining", r"average \$\+(\d+\.\d+)\$ EUR", "priced", True),
        ("priced not retaining", r"against \$\+(\d+\.\d+)\$ for levels", "priced", False),
        ("original retaining", r"objective \(\$\+(\d+\.\d+)\$", "default", True),
        ("original not retaining", r"vs\.\\ \$\+(\d+\.\d+)\$ under the default",
         "default", False),
    ]
    for what, pat, objective, retaining in spec:
        sweep = ps.lambda_sweep(objective)
        sel = sweep[sweep["survival"] > 0] if retaining else sweep[sweep["survival"] == 0]
        check("levels", what, float(sel["epi_mean"].mean()), anchor, pat)


# ---------------------------------------------------------------------------
# Section 3.7 -- the full-model planner's solver budget
# ---------------------------------------------------------------------------

@passage("oracle")
def check_oracle_prose():
    """The 2022 season the planner never finished, and what a raised budget shows."""
    main = ps.load_default_main()
    # every one of the twenty 2022 runs exhausted the budget, so the abort rule takes them
    # out of the pool; the sentence is about those runs and must read the wave file itself.
    raw_main = pd.read_csv(ps.RESULTS / "final" / "main.csv")
    orc = raw_main[(raw_main["method"] == "oracle_mpc") & (raw_main["test_year"] == 2022)]
    anchor = "runs hit the common solver-failure budget"
    check("oracle", "oracle 2022 min season fraction", float(orc["season_fraction"].min()),
          anchor, r"season fraction \$(\d+\.\d+)\$--")
    check("oracle", "oracle 2022 max season fraction", float(orc["season_fraction"].max()),
          anchor, r"--\$(\d+\.\d+)\$, mean")
    check("oracle", "oracle 2022 mean season fraction",
          float(orc["season_fraction"].mean()), anchor, r"mean \$(\d+\.\d+)\$")
    cmp("oracle", "oracle 2022 runs", len(orc), 20.0, 0.0)

    b = pd.read_csv(ps.RESULTS / "oracle_budget" / "main_orcbudget.csv")
    anchor2 = "with the budget raised to"
    v = sorted(float(x) for x in b["epi"])
    check("oracle", "raised-budget worse seed", -v[0], anchor2,
          r"yielding \$-(\d+\.\d+)\$ and")
    check("oracle", "raised-budget better seed", -v[1], anchor2,
          r"and \$-(\d+\.\d+)\$ \(mean")
    check("oracle", "raised-budget mean", -float(np.mean(v)), anchor2,
          r"\(mean \$-(\d+\.\d+)\$\)")
    f = sorted(int(x) for x in b["solver_failures"])
    check("oracle", "raised-budget failures (high)", f[1], anchor2,
          r"requiring (\d+) and", tol=0.0)
    check("oracle", "raised-budget failures (low)", f[0], anchor2,
          r"and (\d+) failures", tol=0.0)

    anchor3 = "Imputing that mean gives a four-season figure"
    per = [float(main[(main.method == "oracle_mpc") & (main.test_year == y)]["epi"].mean())
           for y in (2020, 2021, 2023)]
    check("oracle", "imputed four-season mean", -float(np.mean(per + [np.mean(v)])),
          anchor3, r"about \$-(\d+\.\d+)\$")
    check("oracle", "three-season mean", -float(np.mean(per)), anchor3,
          r"instead of \$-(\d+\.\d+)\$")


# ---------------------------------------------------------------------------
# Section 3.7 -- replaying the surrogates along the planner's own trajectory
# ---------------------------------------------------------------------------

@passage("replay")
def check_replay_prose():
    """One-step and 24 h rollout error of the two surrogates on the planner's trajectory."""
    d = pd.read_csv(ps.RESULTS / "v3_parity" / "parity_v3.csv")
    d = d[d["state"] == "t_in"]
    one = d[d["metric_scope"] == "one_step"]
    roll = d[(d["metric_scope"] == "rollout") & (d["horizon"] == 96)]
    anchor = "gives one-step temperature RMSE of"

    # the sentence quotes the two physics_no_cross recipes in the order they are named
    for rec, pats in (
        ("confirmatory", (r"RMSE of \$(\d+\.\d+)\\pm", r"RMSE of \$\d+\.\d+\\pm(\d+\.\d+)\$",
                          r"R\^2 = (\d+\.\d+)\$", r"rollout RMSE of \$(\d+\.\d+)\$")),
        ("lowthr", (r"and \$(\d+\.\d+)\\pm\d+\.\d+\\,\^", r"\\pm(\d+\.\d+)\\,\^",
                    r"and \$(\d+\.\d+)\$\)", r"rollout RMSE of \$\d+\.\d+\$ and \$(\d+\.\d+)\\,")),
    ):
        o = one[one["recipe"] == rec]
        r_ = roll[roll["recipe"] == rec]
        check("replay", f"{rec} one-step RMSE", float(o["rmse"].mean()), anchor, pats[0])
        check("replay", f"{rec} one-step SD", float(o["rmse"].std(ddof=1)), anchor, pats[1])
        check("replay", f"{rec} R2", float(o["r2"].mean()), anchor, pats[2])
        check("replay", f"{rec} rollout RMSE", float(r_["rmse"].mean()), anchor, pats[3])
        cmp("replay", f"{rec} seeds", o["seed"].nunique(), 5.0, 0.0)


# ---------------------------------------------------------------------------
# Section 3.7 -- the horizon
# ---------------------------------------------------------------------------

@passage("horizon")
def check_horizon_prose():
    """Horizon 8 against horizon 20 on matched seeds and seasons, controller by controller."""
    h8 = pd.read_csv(ps.RESULTS / "ec_h8" / "main_ec_h8.csv")
    # horizon 20 here is the ORIGINAL-objective wave: final/main.csv for the three
    # physics_no_cross controllers and n7 for the raw-library one.
    pool = pd.concat([ps.load_default_main(), ps.load_raw_library_default()],
                     ignore_index=True)
    anchor = "At horizon 8 every MPC improves over horizon 20"
    spec = {
        "sindy_mpc_raw_ens": r"raw\\_ens\} \$\+(\d+\.\d+)\$ vs\.\\ \$\+(\d+\.\d+)\$, \$\\Delta=\+(\d+\.\d+)\$, (\d+)/(\d+)",
        "sindy_mpc_lowthr": r"lowthr\} \$\+(\d+\.\d+)\$ vs\.\\ \$\+(\d+\.\d+)\$, \$\\Delta=\+(\d+\.\d+)\$, (\d+)/(\d+)",
        "sindy_mpc_dense": r"dense\} \$\+(\d+\.\d+)\$ vs\.\\ \$\+(\d+\.\d+)\$, \$\\Delta=\+(\d+\.\d+)\$, (\d+)/(\d+)",
        "sindy_mpc_conf": r"conf\} \$\+(\d+\.\d+)\$ vs\.\\ \$-(\d+\.\d+)\$, \$\\Delta=\+(\d+\.\d+)\$, (\d+)/(\d+)",
    }
    for method, pat in spec.items():
        a = h8[h8["method"] == method]
        b = pool[pool["method"] == method]
        m = a.merge(b, on=["seed", "test_year"], suffixes=("_8", "_20"))
        if m.empty:
            cmp("horizon", f"{method}: no matched runs", 0.0, 1.0, 0.0)
            continue
        sign = -1.0 if method == "sindy_mpc_conf" else 1.0
        check("horizon", f"{method} at h=8", float(m["epi_8"].mean()), anchor, pat, group=1)
        check("horizon", f"{method} at h=20", sign * float(m["epi_20"].mean()), anchor,
              pat, group=2)
        check("horizon", f"{method} delta", float((m["epi_8"] - m["epi_20"]).mean()),
              anchor, pat, group=3)
        check("horizon", f"{method} wins", float((m["epi_8"] > m["epi_20"]).sum()), anchor,
              pat, group=4, tol=0.0)
        check("horizon", f"{method} n", float(len(m)), anchor, pat, group=5, tol=0.0)


# ---------------------------------------------------------------------------
# Section 3.7 -- the bootstrap draw of the ensemble optimizer
# ---------------------------------------------------------------------------

@passage("draws")
def check_draws_prose():
    """Leadership across seed x draw cells, and the spread within a seed."""
    d = pd.concat([pd.read_csv(ps.RESULTS / "ea_draws" / f)
                   for f in ("draws_ea.csv", "draws_ea2.csv")], ignore_index=True)
    per = d.groupby(["method", "seed", "draw"])["epi"].mean().reset_index()
    cells = per.pivot_table(index=["seed", "draw"], columns="method", values="epi")
    wins = int((cells["sindy_mpc_raw_ens"] == cells.max(axis=1)).sum())

    anchor = "leaves the raw-library controller leading in"
    check("draws", "raw leads in cells", float(wins), anchor,
          r"leading in (\d+) of", tol=0.0)
    check("draws", "seed x draw cells", float(len(cells)), anchor,
          r"of (\d+) seed", tol=0.0)
    check("draws", "leadership fraction", wins / len(cells), anchor,
          r"cells \(\$(\d+\.\d+)\$\)")

    anchor2 = "Its spread across draws within a seed averages"
    per_seed = per.groupby(["method", "seed"])["epi"].std(ddof=1)
    for method, pat in (
            ("sindy_mpc_raw_ens", r"averages \$(\d+\.\d+)\$ EUR"),
            ("sindy_mpc_conf", r"against \$(\d+\.\d+)\$ for the frozen"),
            ("sindy_mpc_conf_dagger", r"and \$(\d+\.\d+)\$ for the re-identified")):
        check("draws", f"{method} spread across draws",
              float(per_seed.loc[method].mean()), anchor2, pat)
    raw = per_seed.loc["sindy_mpc_raw_ens"]
    # "five of the six seeds lie at or below": the second largest is the threshold
    cmp("draws", "five seeds below the threshold",
        float((raw <= 0.25).sum()), 5.0, 0.0)
    check("draws", "threshold the five lie below", float(raw.nlargest(2).min()),
          anchor2, r"at or below \$(\d+\.\d+)\$", tol=0.005)
    check("draws", "the one contributing seed", float(raw.max()), anchor2,
          r"contributes \$(\d+\.\d+)\$")


# ---------------------------------------------------------------------------
# Section 3.8 -- on-policy re-identification and the EKF arm
# ---------------------------------------------------------------------------

def _paired(d, a, b, keys=("seed", "draw", "test_year")):
    """Per-run differences between two conditions of the same wave, matched on the keys."""
    ka = d[d["condition"] == a].set_index(list(keys))["epi"]
    kb = d[d["condition"] == b].set_index(list(keys))["epi"]
    common = ka.index.intersection(kb.index)
    return np.asarray(ka.loc[common] - kb.loc[common], float)


@passage("adapt")
def check_adapt_prose():
    """The on-policy arm against the static model, and the EKF arm against both."""
    from scipy.stats import wilcoxon

    d = pd.read_csv(ps.RESULTS / "final" / "adapt.csv")
    dag = d[d["condition"] == "dagger"]
    sta = d[d["condition"] == "static"]
    ekf = d[d["condition"] == "ekf"]

    anchor = "and reduces violations from"
    check("adapt", "on-policy mean", -float(dag["epi"].mean()), anchor,
          r"gives \$-(\d+\.\d+)\$ EUR")
    check("adapt", "static mean", -float(sta["epi"].mean()), anchor,
          r"against \$-(\d+\.\d+)\$ for the static")
    delta = _paired(d, "dagger", "static")
    check("adapt", "on-policy paired delta", float(delta.mean()), anchor,
          r"\\Delta = \+(\d+\.\d+)\$")
    check("adapt", "on-policy paired median", float(np.median(delta)), anchor,
          r"median \$\+(\d+\.\d+)\$")
    check("adapt", "on-policy wins", float((delta > 0).sum()), anchor,
          r"(\d+)/600", tol=0.0)
    cmp("adapt", "on-policy pairs", len(delta), 600.0, 0.0)
    check("adapt", "static violations", float(sta["violation_steps_total"].mean()),
          anchor, r"violations from (\d+) to", tol=0.5)
    check("adapt", "on-policy violations", float(dag["violation_steps_total"].mean()),
          anchor, r"violations from \d+ to (\d+)", tol=0.5)

    anchor2 = "against static"
    check("adapt", "EKF mean", -float(ekf["epi"].mean()), anchor2,
          r"\$-(\d+\.\d+)\$ EUR")
    dekf = _paired(d, "ekf", "static")
    check("adapt", "EKF paired delta", -float(dekf.mean()), anchor2,
          r"\\Delta = -(\d+\.\d+)\$")
    check("adapt", "EKF early terminations",
          float(np.asarray(ekf["truncated"], bool).sum()), anchor2,
          r"with (\d+) of 600 seasons", tol=0.0)


# ---------------------------------------------------------------------------
# Section 3.8 -- the residual-based guard and its detector
# ---------------------------------------------------------------------------

@passage("guard")
def check_guard_prose():
    """Margin and violations under the guard, and the detector's area under the ROC."""
    from scipy.stats import wilcoxon

    d = pd.read_csv(ps.RESULTS / "final" / "guard.csv")
    g = d[d["condition"] == "guarded"]
    pl = d[d["condition"] == "plain"]

    anchor0 = "Guarded runs average"
    check("guard", "guarded mean", -float(g["epi"].mean()), anchor0,
          r"average \$-(\d+\.\d+)\$ EUR")
    check("guard", "unguarded mean", -float(pl["epi"].mean()), anchor0,
          r"against \$-(\d+\.\d+)\$ unguarded")
    anchor = "The paired mean difference is"
    delta = _paired(d, "guarded", "plain")
    check("guard", "guard paired mean", -float(delta.mean()), anchor,
          r"difference is \$-(\d+\.\d+)\$")
    check("guard", "guard paired median", float(np.median(delta)), anchor,
          r"median is \$\+(\d+\.\d+)\$")
    check("guard", "guard wins", float((delta > 0).sum()), anchor,
          r"better in (\d+) of 600", tol=0.0)
    check("guard", "guard p", float(wilcoxon(delta)[1]), anchor,
          r"pairs \(\$p=(\d+\.\d+)\$\)")

    anchor2 = "Violations are worse under the guard"
    dv = _paired(d.rename(columns={"epi": "_e", "violation_steps_total": "epi"}),
                 "guarded", "plain")
    check("guard", "extra violation steps", float(dv.mean()), anchor2,
          r"\(\$\+(\d+)\$ steps", tol=0.5)
    check("guard", "violations worse in", float((dv > 0).sum()), anchor2,
          r"worse in (\d+) of 600", tol=0.0)
    check("guard", "guarded early terminations",
          float(np.asarray(g["truncated"], bool).sum()), anchor2,
          r"and (\d+) of 600 guarded", tol=0.0)

    keys = ["seed", "draw", "test_year"]
    ok = (d[(d.condition == "guarded") & ~d["truncated"].astype(bool)].set_index(keys).index
          .intersection(
              d[(d.condition == "plain") & ~d["truncated"].astype(bool)].set_index(keys).index))
    ka = d[d.condition == "guarded"].set_index(keys)["epi"].loc[ok]
    kb = d[d.condition == "plain"].set_index(keys)["epi"].loc[ok]
    comp = np.asarray(ka - kb, float)
    anchor2b = "Restricted to completed seasons"
    check("guard", "completed-season difference", -float(comp.mean()), anchor2b,
          r"difference is \$-(\d+\.\d+)\$")
    check("guard", "completed-season p", float(wilcoxon(comp)[1]), anchor2b,
          r"significant \(\$p=(\d+\.\d+)\$\)")

    sig = d[d["block"] == "signal"]
    anchor3 = "the area under the ROC curve is"
    check("guard", "AUC distance", float(sig["auc_dist"].mean()), anchor3,
          r"is \$(\d+\.\d+)\\pm")
    check("guard", "AUC distance SD", float(sig["auc_dist"].std(ddof=1)), anchor3,
          r"is \$\d+\.\d+\\pm(\d+\.\d+)\$")
    check("guard", "AUC spread", float(sig["auc_std"].mean()), anchor3,
          r"and \$(\d+\.\d+)\\pm")
    check("guard", "AUC spread SD", float(sig["auc_std"].std(ddof=1)), anchor3,
          r"and \$\d+\.\d+\\pm(\d+\.\d+)\$")


# ---------------------------------------------------------------------------
# Section 3.9 -- the sensitivity grids
# ---------------------------------------------------------------------------

@passage("sens")
def check_sens_prose():
    """Perturbation significance, the canonical coarse grid, and the two other factors."""
    from scipy.stats import wilcoxon

    fine = ps.coef_perturbation()
    anchor = "Only the two largest levels are significant against the smallest"
    base = (fine[np.isclose(fine["value"], 0.02)].groupby("seed")["epi"].mean())
    for level, pat in ((0.15, r"\$p=(\d+\.\d+)\$ at \$15"), (0.20, r"\$p=(\d+\.\d+)\$ at \$20")):
        other = fine[np.isclose(fine["value"], level)].groupby("seed")["epi"].mean()
        # per-seed means, paired across levels: a signed-rank test, not a rank-sum
        check("sens", f"perturbation p at {level:.0%}",
              float(wilcoxon(base, other)[1]), anchor, pat)

    coarse = pd.read_csv(ps.RESULTS / "final" / "design.csv")
    cp = coarse[coarse["factor"] == "coef_perturb"]
    anchor2 = "The canonical coarser grid"
    means = {}
    for level, pat in ((0.1, r"gives \$\+(\d+\.\d+)\$"), (0.2, r"\$-(\d+\.\d+)\$, \$-"),
                       (0.3, r", \$-(\d+\.\d+)\$ at")):
        sub = cp[np.isclose(cp["value"], level)]
        means[level] = float(sub["epi"].mean())
        sign = 1.0 if level == 0.1 else -1.0
        check("sens", f"coarse grid at {level:.0%}", sign * means[level], anchor2, pat)
    check("sens", "coarse grid span", max(means.values()) - min(means.values()), anchor2,
          r"a span of \$(\d+\.\d+)\$")

    anchor3 = "Varying the sparsity threshold of the same controller spans"
    ft = fine if "stlsq_threshold" not in set(fine.get("factor", [])) else fine
    d = ps.load_design()
    thr_fine = d[d["factor"] == "stlsq_threshold"]
    thr_coarse = coarse[coarse["factor"] == "stlsq_threshold"]
    for name, frame, pat in (("fine", thr_fine, r"spans \$(\d+\.\d+)\$ EUR"),
                             ("canonical", thr_coarse, r"only \$(\d+\.\d+)\$ on the canonical")):
        g = frame.groupby("value")["epi"].mean()
        check("sens", f"threshold span ({name})", float(g.max() - g.min()), anchor3, pat)

    # the two numbers are two SPANS -- the finer rerun's and the canonical grid's --
    # not two horizon levels
    anchor4 = "Varying the horizon spans"
    for name, frame, pat in (("fine", d, r"spans \$(\d+\.\d+)\$--"),
                             ("canonical", coarse, r"--\$(\d+\.\d+)\$")):
        hz = frame[frame["factor"] == "mpc_horizon"].groupby("value")["epi"].mean()
        check("sens", f"horizon span ({name})", float(hz.max() - hz.min()), anchor4, pat)

    # the canonical horizon sweep, level by level, and its growing dispersion
    anchor6 = "A single-controller horizon sweep confirms the direction"
    hz = coarse[coarse["factor"] == "mpc_horizon"]
    for i, h in enumerate((8, 12, 20, 30)):
        sub = hz[np.isclose(hz["value"], h)]
        pat = (r"\(\$(\d+\.\d+)\$" if i == 0
               else r"\$\d+\.\d+\$" + r", \$\d+\.\d+\$" * (i - 1) + r", \$(\d+\.\d+)\$")
        check("sens", f"horizon sweep h={h}", float(sub["epi"].mean()), anchor6, pat)
    lo = hz[np.isclose(hz["value"], 8)]["epi"].std(ddof=1)
    hi = hz[np.isclose(hz["value"], 30)]["epi"].std(ddof=1)
    check("sens", "sweep SD at h=8", float(lo), anchor6, r"SD\}=(\d+\.\d+)\$")
    check("sens", "sweep SD at h=30", float(hi), anchor6, r"to \$(\d+\.\d+)\$")

    span = pd.read_csv(ps.RESULTS / "final" / "tables" / "sensitivity_price_span.csv")
    anchor5 = "yields per-controller spans of"
    col = span.columns[-1]
    check("sens", "price span min", float(span[col].min()), anchor5,
          r"spans of \$(\d+\.\d+)\$ to")
    check("sens", "price span max", float(span[col].max()), anchor5,
          r"to \$(\d+\.\d+)\$ EUR")
    check("sens", "price span median", float(span[col].median()), anchor5,
          r"median \$(\d+\.\d+)\$")


# ---------------------------------------------------------------------------
# Section 3.7 -- where the two draw waves disagree
# ---------------------------------------------------------------------------

@passage("survivaldiff")
def check_survival_disagreement():
    """The frozen recipe's boiler survival differs between the 6x6 and canonical waves."""
    ea = pd.concat([pd.read_csv(ps.RESULTS / "ea_draws" / f)
                    for f in ("draws_ea.csv", "draws_ea2.csv")], ignore_index=True)
    anchor = "on the frozen recipe's boiler survival"
    conf = ea[ea["method"] == "sindy_mpc_conf"]
    got = float((conf["xi_uboil"].fillna(0.0).abs() > 0).mean())
    check("survivaldiff", "6x6 wave survival", got, anchor, r"\(\$(\d+\.\d+)\$ vs")

    # the canonical wave is the 20-seed x 10-draw draws block, not the priced main pool,
    # which is a different set of fits and gives 0.15
    canon = pd.read_csv(ps.RESULTS / "final" / "draws.csv")
    canon = canon[canon["method"] == "sindy_mpc_conf"]
    check("survivaldiff", "canonical wave survival",
          float((canon["xi_uboil"].fillna(0.0).abs() > 0).mean()), anchor,
          r"vs\.\\ \$(\d+\.\d+)\$\)")
    cmp("survivaldiff", "canonical wave fits", len(canon), 800.0, 0.0)
    cmp("survivaldiff", "canonical wave seeds", canon["seed"].nunique(), 20.0, 0.0)
    cmp("survivaldiff", "canonical wave draws", canon["draw"].nunique(), 10.0, 0.0)


# ---------------------------------------------------------------------------
# Section 4.2 -- the open-loop series, restated
# ---------------------------------------------------------------------------

@passage("disc-ladder")
def check_disc_ladder():
    """The three-library open-loop series and the one-step ordering."""
    lad = ps.load_ladder(optimizers=None)
    summ = ps.ladder_summary(lad).set_index("variant")
    LIBS = ["raw", "physics_no_cross", "physics"]

    anchor = "Over the ladder's degree-one undenoised block"
    arrow = r" \\\\rightarrow "
    for i, lib in enumerate(LIBS):
        head = r"\\kappa = " + r"\d+\.\d+" .join([""] * 1) if False else None
        pat = r"\\kappa = " + (r"\d+\.\d+ \\rightarrow " * i) + r"(\d+\.\d+)"
        check("disc-ladder", f"{lib} kappa", float(summ.loc[lib, "kappa"]), anchor, pat)
        pat = r"rollout error \$" + (r"\d+\.\d+ \\rightarrow " * i) + r"(\d+\.\d+)"
        check("disc-ladder", f"{lib} rollout", float(summ.loc[lib, "rollout_median"]),
              anchor, pat)
        pat = r"divergence \$" + (r"\d+\.\d+ \\rightarrow " * i) + r"(\d+\.\d+)"
        check("disc-ladder", f"{lib} divergence", float(summ.loc[lib, "diverged"]),
              anchor, pat)

    anchor2 = "One-step error does not order the libraries along that direction at all"
    check("disc-ladder", "physics one-step", float(summ.loc["physics", "one_step"]),
          anchor2, r"library \(\$(\d+\.\d+)\$")
    check("disc-ladder", "physics_no_cross one-step",
          float(summ.loc["physics_no_cross", "one_step"]), anchor2,
          r"worse than raw \(\$(\d+\.\d+)\$")
    check("disc-ladder", "raw one-step", float(summ.loc["raw", "one_step"]), anchor2,
          r"against \$(\d+\.\d+)\$\)")

    # the pair quoted here is the Section 3.1 comparator: raw under STLSQ against the
    # frozen recipe under the ensemble, both degree 1 with no denoising
    anchor3 = "The winner is the sparser model on both counts"
    full = ps.load_ladder(degree=None, denoise=None, optimizers=None)
    a = full[(full["variant"] == "raw") & (full["degree"] == 1)
             & (full["optimizer"] == "stlsq") & (full["denoise"] == "none")]
    b = full[(full["variant"] == "physics_no_cross") & (full["degree"] == 1)
             & (full["optimizer"] == "ensemble") & (full["denoise"] == "none")]
    check("disc-ladder", "raw retained terms", float(a["nonzero"].mean()), anchor3,
          r"and \$(\d+\.\d+)\$ retained terms")
    check("disc-ladder", "no_cross retained terms", float(b["nonzero"].mean()), anchor3,
          r"retained terms against \$(\d+\.\d+)\$")


# ---------------------------------------------------------------------------
# Section 4.3 -- the non-monotone series and the survivors
# ---------------------------------------------------------------------------

@passage("disc-mechanism")
def check_disc_mechanism():
    """The worst-conditioned library against the middle one, and the two survivors."""
    from scipy.stats import wilcoxon

    pool = ps.load_library_pool()
    anchor = "The series is"
    d = np.asarray(ps.paired_deltas(pool, "sindy_mpc_phys_ens", "sindy_mpc_conf"), float)
    d = d[~np.isnan(d)]
    check("disc-mechanism", "phys_ens over conf, mean", float(d.mean()), anchor,
          r"middle one by \$\+(\d+\.\d+)\$")
    check("disc-mechanism", "phys_ens over conf, median", float(np.median(d)), anchor,
          r"median \$\+(\d+\.\d+)\$")
    check("disc-mechanism", "phys_ens over conf, wins", float((d > 0).sum()), anchor,
          r"(\d+) of 80 paired runs", tol=0.0)

    anchor2 = "Among the two libraries that keep the term, the raw one"
    e = np.asarray(ps.paired_deltas(pool, "sindy_mpc_raw_ens", "sindy_mpc_phys_ens"), float)
    e = e[~np.isnan(e)]
    check("disc-mechanism", "raw over phys_ens, mean", float(e.mean()), anchor2,
          r"ahead by \$\+(\d+\.\d+)\$")
    check("disc-mechanism", "raw over phys_ens, median", float(np.median(e)), anchor2,
          r"median \$\+(\d+\.\d+)\$")
    check("disc-mechanism", "raw over phys_ens, wins", float((e > 0).sum()), anchor2,
          r"(\d+) of 80", tol=0.0)

    anchor3 = "The two raw-library variants"
    f = np.asarray(ps.paired_deltas(pool, "sindy_mpc_raw_ens", "sindy_mpc_raw"), float)
    f = f[~np.isnan(f)]
    check("disc-mechanism", "raw variants median", -float(np.median(f)), anchor3,
          r"\\Delta=-(\d+\.\d+)\$")
    check("disc-mechanism", "raw variants mean", float(f.mean()), anchor3,
          r"mean \$\+(\d+\.\d+)\$")
    check("disc-mechanism", "raw variants wins", float((f > 0).sum()), anchor3,
          r"\$(\d+)/80\$ wins", tol=0.0)
    check("disc-mechanism", "raw variants p", float(wilcoxon(f)[1]), anchor3,
          r"\$p=(\d+\.\d+)\$")

    anchor4 = "Bagged ensembling"
    g = np.asarray(ps.paired_deltas(pool, "sindy_mpc_phys_ens", "sindy_mpc_phys"), float)
    g = g[~np.isnan(g)]
    check("disc-mechanism", "ensembling on physics", float(wilcoxon(g)[1]), anchor4,
          r"physics library \(\$p=(\d+\.\d+)\$\)")


# ---------------------------------------------------------------------------
# Section 4.3 -- the observational splits and the term-deletion test
# ---------------------------------------------------------------------------

@passage("disc-splits")
def check_disc_splits():
    """The two non-significant observational splits, and the 17-feature library."""
    from scipy.stats import mannwhitneyu

    pool = ps.load_library_pool()
    anchor = "Two observational figures were consistent with it"
    # one controller per library, and the comparison is on per-seed means
    for method, pats in (
        ("sindy_mpc_phys_ens",
         (r"\(\$\+(\d+\.\d+)\$ against", r"against \$\+(\d+\.\d+)\$~EUR",
          r"(\d+) and \d+ replicates", r"and (\d+) replicates, \$p=0\.25",
          r"replicates, \$p=(\d+\.\d+)\$\), whereas")),
        ("sindy_mpc_conf",
         (r"\(\$\+(\d+\.\d+)\$ against \$-", r"against \$-(\d+\.\d+)\$",
          r"(\d+) and \d+ replicates, \$p=0\.18", r"and (\d+) replicates, \$p=0\.18",
          r"\$-0\.06\$, \d+ and \d+ replicates, \$p=(\d+\.\d+)\$")),
    ):
        d = pool[pool["method"] == method]
        per = d.groupby("seed")["boiler_alive"].max()
        keep = d[d["seed"].isin(per[per > 0].index)].groupby("seed")["epi"].mean()
        drop = d[d["seed"].isin(per[per == 0].index)].groupby("seed")["epi"].mean()
        if method == "sindy_mpc_phys_ens":
            first, second, n1, n2 = drop.mean(), keep.mean(), len(drop), len(keep)
        else:
            first, second, n1, n2 = keep.mean(), -drop.mean(), len(keep), len(drop)
        check("disc-splits", f"{method} first figure", float(first), anchor, pats[0])
        check("disc-splits", f"{method} second figure", float(second), anchor, pats[1])
        check("disc-splits", f"{method} first count", float(n1), anchor, pats[2], tol=0.0)
        check("disc-splits", f"{method} second count", float(n2), anchor, pats[3], tol=0.0)
        check("disc-splits", f"{method} split p", float(mannwhitneyu(keep, drop)[1]),
              anchor, pats[4])

    anchor1b = "whereas inside the library without cross terms losing it costs"
    d = pool[pool["method"] == "sindy_mpc_conf"]
    per = d.groupby("seed")["boiler_alive"].max()
    keep = d[d["seed"].isin(per[per > 0].index)].groupby("seed")["epi"].mean()
    drop = d[d["seed"].isin(per[per == 0].index)].groupby("seed")["epi"].mean()
    check("disc-splits", "no-cross cost of losing the term",
          float(keep.mean() - drop.mean()), anchor1b, r"costs \$\+(\d+\.\d+)\$")

    ntb = ps.load_notuboil_pool()
    anchor2 = "It scores"
    for method, pat in (("sindy_mpc_notuboil_ens", r"scores \$\+(\d+\.\d+)\$"),
                        ("sindy_mpc_notuboil", r"and \$\+(\d+\.\d+)\$ under STLSQ")):
        sub = ntb[ntb["method"] == method]
        check("disc-splits", f"{method} margin", float(sub["epi"].mean()), anchor2, pat)
    ens = ntb[ntb["method"] == "sindy_mpc_notuboil_ens"]
    k = int(ens.groupby("seed")["xi_uboil"].max().pipe(lambda x: (x.fillna(0).abs() > 0)).sum())
    n = int(ens["seed"].nunique())
    check("disc-splits", "notuboil survival", k / n, anchor2, r"survival \$(\d+\.\d+)\$")
    check("disc-splits", "notuboil survivors", float(k), anchor2, r"\((\d+) of 20", tol=0.0)
    lo, hi = ps.wilson(k, n)
    check("disc-splits", "Wilson lower", lo, anchor2, r"\[(\d+\.\d+),")
    check("disc-splits", "Wilson upper", hi, anchor2, r",\\,(\d+\.\d+)\]")


# ---------------------------------------------------------------------------
# Section 4.5 -- benchmarking safeguards, restated
# ---------------------------------------------------------------------------

@passage("disc-safeguards")
def check_disc_safeguards():
    """PPO's trade, the single-replicate pairing, and the two-variant separation."""
    from scipy.stats import wilcoxon

    pool = full_pool()
    anchor = "PPO incurs"
    ppo = pool[pool["method"] == "ppo"]
    raw = pool[pool["method"] == "sindy_mpc_raw_ens"]
    check("disc-safeguards", "ppo violations",
          float(ppo["violation_steps_total"].mean()), anchor, r"incurs \$(\d+)\$", tol=0.5)
    check("disc-safeguards", "raw violations",
          float(raw["violation_steps_total"].mean()), anchor,
          r"library's \$(\d+)\$", tol=0.5)
    check("disc-safeguards", "ppo margin shortfall",
          float(raw["epi"].mean() - ppo["epi"].mean()), anchor, r"at \$(\d+\.\d+)\$~EUR")

    anchor2 = "paired test collapses to one replicate's four seasons"
    tune = ps.load_heuristic_tuning()
    tuned = tune[tune["block"] == "tuned_test"].set_index("test_year")["epi"]
    r0 = raw[raw["seed"] == 0].set_index("test_year")["epi"]
    years = [2020, 2021, 2022, 2023]
    d = np.array([float(r0[y] - tuned[y]) for y in years])
    check("disc-safeguards", "single-replicate contrast", float(d.mean()), anchor2,
          r"\(\$\+(\d+\.\d+)\$")
    check("disc-safeguards", "signed-rank floor", float(wilcoxon(d)[1]), anchor2,
          r"minimum attainable \$p\$ is \$(\d+\.\d+)\$")

    anchor3 = "Two physics-informed variants differ by"
    a = float(pool[pool.method == "sindy_mpc_lowthr"]["epi"].mean())
    b = float(pool[pool.method == "sindy_mpc_dense"]["epi"].mean())
    check("disc-safeguards", "front-pair difference", a - b, anchor3,
          r"differ by \$(\d+\.\d+)\$")
    e = np.asarray(ps.paired_deltas(pool, "sindy_mpc_dense", "sindy_mpc_lowthr"), float)
    e = e[~np.isnan(e)]
    check("disc-safeguards", "front-pair p", float(wilcoxon(e)[1]), anchor3,
          r"separate at \$p=(\d+\.\d+)\$")


# ---------------------------------------------------------------------------
# Section 4.6 -- the caveats
# ---------------------------------------------------------------------------

@passage("disc-caveats")
def check_disc_caveats():
    """The perturbation span, the horizon gains, the harness gap and the EKF arm."""
    anchor = "perturbing identified coefficients by"
    coarse = pd.read_csv(ps.RESULTS / "final" / "design.csv")
    cp = coarse[coarse["factor"] == "coef_perturb"]
    means = {float(v): float(cp[np.isclose(cp["value"], v)]["epi"].mean())
             for v in (0.1, 0.2, 0.3)}
    fine = ps.coef_perturbation()
    fmeans = {float(v): float(fine[np.isclose(fine["value"], v)]["epi"].mean())
              for v in sorted(fine["value"].unique())}
    check("disc-caveats", "span of means (default objective)",
          max(fmeans.values()) - min(fmeans.values()), anchor,
          r"span of means \$(\d+\.\d+)\$")
    check("disc-caveats", "median at 20 per cent",
          -float(fine[np.isclose(fine["value"], 0.20)]["epi"].median()), anchor,
          r"is only \$-(\d+\.\d+)\$")

    anchor2 = "Every MPC improves at horizon 8 over horizon 20"
    h8 = pd.read_csv(ps.RESULTS / "ec_h8" / "main_ec_h8.csv")
    base = pd.concat([ps.load_default_main(), ps.load_raw_library_default()],
                     ignore_index=True)
    gains = {}
    for m in ("sindy_mpc_raw_ens", "sindy_mpc_lowthr", "sindy_mpc_dense", "sindy_mpc_conf"):
        mm = h8[h8.method == m].merge(base[base.method == m], on=["seed", "test_year"],
                                      suffixes=("_8", "_20"))
        gains[m] = float((mm["epi_8"] - mm["epi_20"]).mean())
    check("disc-caveats", "raw-library horizon gain", gains["sindy_mpc_raw_ens"], anchor2,
          r"by \$\+(\d+\.\d+)\$ for the raw")
    others = [gains[m] for m in ("sindy_mpc_lowthr", "sindy_mpc_dense", "sindy_mpc_conf")]
    check("disc-caveats", "physics-informed gain, low", min(others), anchor2,
          r"and \$\+(\d+\.\d+)\\ldots")
    check("disc-caveats", "physics-informed gain, high", max(others), anchor2,
          r"\\ldots\+(\d+\.\d+)\$")

    anchor3 = "the two harnesses score the"
    main = ps.load_default_main()
    tune = ps.load_heuristic_tuning()
    a = main[main["method"] == "rule_based"].groupby("test_year")["epi"].mean()
    b = tune[tune["block"] == "stock_test"].set_index("test_year")["epi"]
    years = sorted(set(a.index) & set(b.index))
    gap = float(max(abs(a[y] - b[y]) for y in years))
    check("disc-caveats", "largest harness gap", gap, anchor3, r"by up to \$(\d+\.\d+)\$")

    anchor4 = "The extended Kalman filter observer scores below the static model"
    ad = pd.read_csv(ps.RESULTS / "final" / "adapt.csv")
    ekf = ad[ad["condition"] == "ekf"]
    sta = ad[ad["condition"] == "static"]
    check("disc-caveats", "EKF margin", -float(ekf["epi"].mean()), anchor4,
          r"\(\$-(\d+\.\d+)\$ against")
    check("disc-caveats", "static margin", -float(sta["epi"].mean()), anchor4,
          r"against \$-(\d+\.\d+)\$")
    check("disc-caveats", "EKF early-termination share",
          100 * float(np.asarray(ekf["truncated"], bool).mean()), anchor4,
          r"\$(\d+)\\,\\%\$ of its seasons", tol=0.5)


# ---------------------------------------------------------------------------
# Section 1 -- the framing claims
# ---------------------------------------------------------------------------

@passage("intro")
def check_intro_prose():
    """The dispersion around the headline gap, the season that reverses it, and the
    two cross-library survival averages."""
    pool = ps.load_library_pool()
    raw = pool[pool["method"] == "sindy_mpc_raw_ens"]
    low = pool[pool["method"] == "sindy_mpc_lowthr"]

    anchor = "The gap is small against the run-to-run spread"
    check("intro", "raw_ens SD", float(raw["epi"].std(ddof=1)), anchor,
          r"deviations \$(\d+\.\d+)\$ and")
    check("intro", "lowthr SD", float(low["epi"].std(ddof=1)), anchor,
          r"and \$(\d+\.\d+)\$ for a difference")
    check("intro", "the difference", float(raw["epi"].mean() - low["epi"].mean()),
          anchor, r"difference of \$(\d+\.\d+)\$")
    a21 = float(raw[raw["test_year"] == 2021]["epi"].mean())
    b21 = float(low[low["test_year"] == 2021]["epi"].mean())
    check("intro", "raw_ens in 2021", -a21, anchor, r"\(\$-(\d+\.\d+)\$ against")
    check("intro", "lowthr in 2021", b21, anchor, r"against \$\+(\d+\.\d+)\$ in 2021")

    anchor2 = "Among the two libraries that keep the term the raw one"
    e = np.asarray(ps.paired_deltas(pool, "sindy_mpc_raw_ens", "sindy_mpc_phys_ens"), float)
    e = e[~np.isnan(e)]
    check("intro", "raw over phys_ens", float(e.mean()), anchor2,
          r"still ahead by \$\+(\d+\.\d+)\$")

    rawlib = pool[pool["library"] == "raw"]
    physlib = pool[pool["library"] == "physics"]
    lost = rawlib[rawlib["boiler_alive"] == 0]["epi"]
    kept = physlib[physlib["boiler_alive"] > 0]["epi"]
    check("intro", "raw runs that lost the term", float(lost.mean()), anchor2,
          r"still average \$\+(\d+\.\d+)\$")
    check("intro", "physics runs that kept it", float(kept.mean()), anchor2,
          r"kept it \(\$\+(\d+\.\d+)\$\)")


# ---------------------------------------------------------------------------
# Section 5 -- the conclusions
# ---------------------------------------------------------------------------

@passage("conclusions")
def check_conclusions_prose():
    """The survival stratification of the frozen recipe, and the priced perturbation."""
    from scipy.stats import mannwhitneyu, wilcoxon

    pool = ps.load_library_pool()
    conf = pool[pool["method"] == "sindy_mpc_conf"]
    # survival is a property of the fit, so the unit is the seed: per-seed four-season
    # means, 3 replicates that kept the term against 17 that lost it (the run-level split
    # of 12 against 68 runs is the same 3 and 17 seeds counted four times over)
    per = conf.groupby("seed").agg(epi=("epi", "mean"), alive=("boiler_alive", "max"))
    keep = per[per["alive"] > 0]["epi"]
    drop = per[per["alive"] == 0]["epi"]
    anchor = "points the same way but is not significant at the level"
    check("conclusions", "survival stratification p (seed level)",
          float(mannwhitneyu(keep, drop)[1]), anchor,
          r"replicates \(\$p=(\d+\.\d+)\$, \d+ against \d+\)")
    check("conclusions", "replicates that kept the term", float(len(keep)), anchor,
          r"\$p=\d+\.\d+\$, (\d+) against \d+\)", tol=0.0)
    check("conclusions", "replicates that lost the term", float(len(drop)), anchor,
          r"\$p=\d+\.\d+\$, \d+ against (\d+)\)", tol=0.0)
    cmp("conclusions", "stratification points the same way (kept > lost)",
        1.0 if float(keep.mean()) > float(drop.mean()) else 0.0, 1.0, 0.0)

    # Finding 2: the two headline contrasts on per-seed means
    full = full_pool()
    d = ps.paired_deltas(full, "sindy_mpc_raw_ens", "sindy_mpc_lowthr").groupby(level="seed").mean()
    tuned = full[full.method == "rule_based_tuned"].groupby("test_year")["epi"].mean()
    g = full[full.method == "sindy_mpc_raw_ens"]
    dt = (g["epi"] - g["test_year"].map(tuned)).groupby(g["seed"]).mean()
    anchor_f2 = "both contrasts hold on per-seed"
    check("conclusions", "raw vs physics-informed, seeds won", float((d > 0).sum()), anchor_f2,
          r"\((\d+) of 20 and \d+ of 20", tol=0.0)
    check("conclusions", "raw vs tuned heuristic, seeds won", float((dt > 0).sum()), anchor_f2,
          r"\(\d+ of 20 and (\d+) of 20", tol=0.0)
    cmp("conclusions", "seed counts", float(len(d)), 20.0, 0.0)

    d = pd.read_csv(ps.RESULTS / "design_priced_real" / "design_designPriced.csv")
    cp = d[d["factor"] == "coef_perturb"]
    base = cp[np.isclose(cp["value"], 0.02)].groupby("seed")["epi"].mean()
    hit = cp[np.isclose(cp["value"], 0.15)].groupby("seed")["epi"].mean()
    anchor2 = "coefficient perturbation costs"
    check("conclusions", "priced perturbation cost, mean",
          float(base.mean() - hit.mean()), anchor2, r"costs \$(\d+\.\d+)\$ on the mean")
    b_all = cp[np.isclose(cp["value"], 0.02)]["epi"]
    h_all = cp[np.isclose(cp["value"], 0.15)]["epi"]
    check("conclusions", "priced perturbation cost, median",
          float(b_all.median() - h_all.median()), anchor2,
          r"against \$(\d+\.\d+)\$ on the median")

    # the significance of that cost is a rank-sum over all forty runs per level
    check("conclusions", "priced perturbation p",
          float(mannwhitneyu(b_all, h_all)[1]), anchor2,
          r"\(\$p=(\d+\.\d+)\\times10\^\{-3\}\$\)", scale=1e-3)

    g = pd.read_csv(ps.RESULTS / "final" / "guard.csv")
    delta = _paired(g, "guarded", "plain")
    anchor2 = "The out-of-distribution guard is a negative result"
    check("conclusions", "guard paired mean", -float(delta.mean()), anchor2,
          r"paired mean \$-(\d+\.\d+)\$")
    dv = _paired(g.rename(columns={"epi": "_e", "violation_steps_total": "epi"}),
                 "guarded", "plain")
    check("conclusions", "guard extra violations", float(dv.mean()), anchor2,
          r"\$\+(\d+)\$ violation steps", tol=0.5)


# ---------------------------------------------------------------------------
# Section 2 -- the measured constants of the method
# ---------------------------------------------------------------------------

@passage("methods")
def check_methods_prose():
    """The marginal costs read off the logged columns, the re-weighted stage cost, and
    the per-season discrepancy between the two harnesses."""
    main = pd.read_csv(ps.RESULTS / "final" / "main.csv")

    anchor = "Dividing the logged cost columns by the logged actuator sums"
    pairs = {
        "boiler": ("cost_heat", "boiler_sum", r"of (\d+\.\d+), \d+\.\d+ and"),
        "lamps": ("cost_elec", "lamp_sum", r"of \d+\.\d+, (\d+\.\d+) and"),
        "CO2": ("cost_co2", "co2_injection_sum", r"and (\d+\.\d+)~EUR"),
    }
    unit = {}
    for name, (cost, amount, pat) in pairs.items():
        got = float(main[cost].sum() / main[amount].sum())
        unit[name] = got
        check("methods", f"marginal cost, {name}", got, anchor, pat)
    check("methods", "cost ratio, lamps", unit["lamps"] / unit["boiler"], anchor,
          r"or \$1:(\d+\.\d+):")
    check("methods", "cost ratio, CO2", unit["CO2"] / unit["boiler"], anchor,
          r"or \$1:\d+\.\d+:(\d+\.\d+)\$")

    anchor2 = "The primary"
    w = {}
    for name, pat in (("boil", r"uses \$(\d+\.\d+)u_"), ("lamp", r"\+(\d+\.\d+)u_\{\\mathrm\{lamp"),
                      ("co2", r"\+(\d+\.\d+)u_\{\\mathrm\{CO")):
        w[name] = stated(anchor2, pat)
    check("methods", "priced weights sum at u=(1,1,1)", sum(w.values()), anchor2,
          r"is (\d+\.\d+) against")
    check("methods", "weight ratio, lamps", w["lamp"] / w["boil"], anchor,
          r"or \$1:(\d+\.\d+):")
    check("methods", "weight ratio, CO2", w["co2"] / w["boil"], anchor,
          r"or \$1:\d+\.\d+:(\d+\.\d+)\$")

    anchor3 = "The hard-coded heuristic returns a four-season mean of"
    pool = ps.load_default_main()
    tune = ps.load_heuristic_tuning()
    a = pool[pool["method"] == "rule_based"]
    b = tune[tune["block"] == "stock_test"]
    check("methods", "main-harness mean", -float(a["epi"].mean()), anchor3,
          r"mean of \$-(\d+\.\d+)\$", tol=0.00005)
    check("methods", "tuning-harness mean", -float(b["epi"].mean()), anchor3,
          r"and \$-(\d+\.\d+)\$ in the tuning", tol=0.00005)
    pa = a.groupby("test_year")["epi"].mean()
    pb = b.set_index("test_year")["epi"]
    years = [2020, 2021, 2022, 2023]
    for i, y in enumerate(years):
        pat = r"\(" + r"\$\d+\.\d+\$, " * i + r"\$(\d+\.\d+)\$"
        check("methods", f"harness discrepancy {y}", float(abs(pa[y] - pb[y])), anchor3,
              pat)
    diffs = [float(abs(pa[y] - pb[y])) for y in years]
    cmp("methods", "discrepancy grows monotonically",
        1.0 if all(x < y for x, y in zip(diffs, diffs[1:])) else 0.0, 1.0, 0.0)

    anchor4 = "the data contain a contrast significant at"
    pl = ps.load_library_pool()
    from scipy.stats import wilcoxon
    e = np.asarray(ps.paired_deltas(pl, "sindy_mpc_dense", "sindy_mpc_lowthr"), float)
    e = e[~np.isnan(e)]
    check("methods", "front-pair p", float(wilcoxon(e)[1]), anchor4,
          r"at \$p=(\d+\.\d+)\$")
    check("methods", "front-pair difference",
          float(abs(pl[pl.method == "sindy_mpc_lowthr"]["epi"].mean()
                    - pl[pl.method == "sindy_mpc_dense"]["epi"].mean())),
          anchor4, r"difference of (\d+\.\d+)~EUR")


# ---------------------------------------------------------------------------
# Section 2 -- the constants the method states
# ---------------------------------------------------------------------------

@passage("constants")
def check_constants_prose():
    """Site coordinates, the Magnus--Tetens coefficients, and the two reward constants.

    These are configuration rather than measurement, so each is read from the file that
    defines it: the weather builder, the experiment module, and the environment's own YAML
    inside the pinned interpreter. A constant edited there without the manuscript following
    fails here.
    """
    root = HERE.parent.parent          # own-article/
    weather = (root / "make_weather.py").read_text(encoding="utf-8")
    m = re.search(r"LAT, LON = ([\d.]+), ([\d.]+)", weather)
    anchor = "The simulated house is at Rostov-on-Don"
    if m:
        check("constants", "latitude", float(m.group(1)), anchor,
              r"\$(\d+\.\d+)\^\{\\circ\}\$~N")
        check("constants", "longitude", float(m.group(2)), anchor,
              r"\$(\d+\.\d+)\^\{\\circ\}\$~E")

    utils = (root / "article_experiment_utils.py").read_text(encoding="utf-8")
    m = re.search(r"psat = ([\d.]+) \* np\.exp\(([\d.]+) \* t_in / \(t_in \+ ([\d.]+)\)\)",
                  utils)
    anchor2 = "by the Magnus--Tetens relation"
    if m:
        for i, (what, pat) in enumerate((
                ("Magnus coefficient", r"e_s\(T_\{\\mathrm\{in\}\}\)=(\d+\.\d+)"),
                ("Magnus numerator", r"\\exp\\bigl\((\d+\.\d+)\\,"),
                ("Magnus offset", r"\+(\d+\.\d+)\)\\bigr\)"))):
            check("constants", what, float(m.group(i + 1)), anchor2, pat)

    # the reward constants live in the environment's own configuration
    # Ask the active interpreter where gl_gym is installed, so the check runs wherever
    # the pipeline can run; the literal path below is the one it was first written
    # against and is kept as a fallback.
    import importlib.util

    cands = []
    spec = importlib.util.find_spec("gl_gym")
    if spec is not None and spec.submodule_search_locations:
        cands += [Path(p) / "configs" / "envs" / "GreenLightEnv.yml"
                  for p in spec.submodule_search_locations]
    cands.append(Path(r"C:\Users\zergu\repos\greenlight\sindylom\.venv\Lib\site-packages"
                      r"\gl_gym\configs\envs\GreenLightEnv.yml"))
    cfg = None
    for cand in cands:
        if cand.exists():
            cfg = cand.read_text(encoding="utf-8")
            break
    anchor3 = "where $g_k$ is income from modelled fruit dry-matter growth"
    if cfg:
        m = re.search(r"fruit_price:\s*([\d.]+)", cfg)
        check("constants", "fruit price", float(m.group(1)), anchor3,
              r"valued at (\d+\.\d+)~EUR/kg")
        m = re.search(r"dmfm:\s*([\d.]+)", cfg)
        check("constants", "dry-to-fresh ratio", float(m.group(1)), anchor3,
              r"ratio of (\d+\.\d+)")
    else:
        cmp("constants", "environment configuration not found", 0.0, 1.0, 0.0)


# ---------------------------------------------------------------------------
# The last four statistics
# ---------------------------------------------------------------------------

@passage("tail")
def check_tail_prose():
    """The one fit-to-evaluate direction that reverses, the ensemble triple's term counts,
    the family-of-13 levels, and the EKF arm's p-value."""
    from scipy.stats import wilcoxon

    d = pd.read_csv(ps.RESULTS / "holdout" / "holdout_holdout.csv")
    anchor = "in one of the four fit$\\rightarrow$evaluate directions it narrowly beats"
    rows = {}
    for lib in ("physics_no_cross", "raw"):
        # the direction that reverses is fit 2018 -> evaluate 2019, the only one of the
        # four in which the no-cross library leads
        sub = d[(d["variant"] == lib) & (d["fit_year"] == 2018) & (d["eval_year"] == 2019)]
        rows[lib] = float(sub["rollout_rmse_t_in"].median())
    check("tail", "no_cross in the reversing direction", rows["physics_no_cross"], anchor,
          r"\(\$(\d+\.\d+)\$ against")
    check("tail", "raw in the reversing direction", rows["raw"], anchor,
          r"against \$(\d+\.\d+)\$\)")

    anchor2 = "across the ensemble triple, in which the library is the only thing"
    lad = ps.load_ladder(optimizers=("ensemble",)).groupby("variant")["nonzero"].mean()
    for i, lib in enumerate(("raw", "physics_no_cross", "physics")):
        pat = (r"retained terms run \$" + r"\d+\.\d+ \\rightarrow " * i
               + r"(\d+\.\d+)")
        check("tail", f"{lib} ensemble terms", float(lad[lib]), anchor2, pat)

    # the family-of-13 levels the Discussion quotes as the "before"
    pool = full_pool()
    const = pool[pool.method == "rule_based_tuned"].groupby("test_year")["epi"].mean()
    EX = {"sindy_mpc_phys", "sindy_mpc_phys_ens"}
    raw_p = {}
    for m in pool["method"].unique():
        if m == "rule_based_tuned" or m in EX:
            continue
        x = np.asarray(ps.deltas_vs_constant(pool, m, const), float)
        x = x[~np.isnan(x)]
        raw_p[m] = wilcoxon(x)[1] if len(x) > 1 and np.any(x != 0) else 1.0
    adj13 = _holm(raw_p, 13)
    anchor3 = "enlarged the family from 13 to 15"
    check("tail", "raw_ens under the family of 13",
          adj13["sindy_mpc_raw_ens"], anchor3,
          r"tuned heuristic from \$(\d+\.\d+)\\times10\^\{-11\}", scale=1e-11)
    check("tail", "lowthr under the family of 13", adj13["sindy_mpc_lowthr"],
          anchor3, r"against it from \$(\d+\.\d+)\\times10\^\{-4\}", scale=1e-4)

    ad = pd.read_csv(ps.RESULTS / "final" / "adapt.csv")
    delta = _paired(ad, "ekf", "static")
    anchor4 = "against static"
    check("tail", "EKF p-value", float(wilcoxon(delta)[1]), anchor4,
          r"\$p=(\d+\.\d+)\\times10\^\{-14\}\$", scale=1e-14)


# ---------------------------------------------------------------------------
# Section 4.3 -- the knock-in ablation, in full
# ---------------------------------------------------------------------------

@passage("knockin")
def check_knockin_prose():
    """The only randomised manipulation in the mechanism block: wins, three p-values at
    three declared families, and the median, quartiles and mean of the effect."""
    from scipy.stats import wilcoxon

    kn = ps.knock_effects(objective="priced")
    d = np.asarray(kn["knockin"], float)
    d = d[~np.isnan(d)]
    ko = np.asarray(kn["knockout"], float)
    ko = ko[~np.isnan(ko)]

    anchor = "Under the priced objective the effect is significant and"
    check("knockin", "positive replicates", float((d > 0).sum()), anchor,
          r"positive in (\d+) of 20", tol=0.0)
    p_raw = float(wilcoxon(d)[1])
    check("knockin", "uncorrected p", p_raw, anchor,
          r"\$p=(\d+\.\d+)\\times10\^\{-4\}\$", scale=1e-4)
    two = _holm({"knockin": p_raw, "knockout": float(wilcoxon(ko)[1])}, 2)["knockin"]
    check("knockin", "Holm over the two knock tests", two, anchor,
          r"\(\$(\d+\.\d+)\\times10\^\{-3\}\$ after Holm", scale=1e-3)
    # the widened family is the four contrasts of the mechanism block -- knock-in and
    # knock-out under each stage cost -- which is what Figure 3 declares and adjusts over
    four = {}
    for obj in ("priced", "default"):
        k2 = ps.knock_effects(objective=obj)
        for eff in ("knockin", "knockout"):
            x = np.asarray(k2[eff], float)
            x = x[~np.isnan(x)]
            try:
                four[(obj, eff)] = float(wilcoxon(x).pvalue)
            except ValueError:
                four[(obj, eff)] = float("nan")
    check("knockin", "Holm over the four mechanism contrasts",
          float(ps.holm(four)[("priced", "knockin")]), anchor,
          r"; \$(\d+\.\d+)\\times10\^\{-3\}\$", scale=1e-3)
    check("knockin", "effect median", float(np.median(d)), anchor,
          r"median \$\+(\d+\.\d+)\$")
    check("knockin", "effect lower quartile", float(np.quantile(d, 0.25)), anchor,
          r"range \$\[\+(\d+\.\d+),")
    check("knockin", "effect upper quartile", float(np.quantile(d, 0.75)), anchor,
          r",\\,\+(\d+\.\d+)\]\$")
    check("knockin", "effect mean", float(d.mean()), anchor, r"mean \$\+(\d+\.\d+)\$")


# ---------------------------------------------------------------------------
# Integer-valued claims: violation counts
# ---------------------------------------------------------------------------

@passage("violations")
def check_violation_counts():
    """Violation totals quoted as bare integers, which carry one of the paper's two axes."""
    f = pd.read_csv(ps.RESULTS / "final" / "tables" / "faults.csv").set_index("condition")
    anchor = "Violations fall sharply"
    for fault, pats in (("uVent_dead", (r"\((\d+) to \d+ under a dead vent",
                                        r"\(\d+ to (\d+) under a dead vent")),
                        ("uBoil_stuck", (r"vent; (\d+) to \d+ under a", r"; \d+ to (\d+) under a"))):
        check("violations", f"{fault} unsupervised",
              float(f.loc[f"{fault}/raw", "viol_mean"]), anchor, pats[0], tol=0.5)
        check("violations", f"{fault} supervised",
              float(f.loc[f"{fault}/sup", "viol_mean"]), anchor, pats[1], tol=0.5)

    # the threshold sweep, on the finer rerun and on the canonical grid
    anchor2 = "Violations rise by half between the extreme levels"
    fine = ps.load_design()
    thr = fine[fine["factor"] == "stlsq_threshold"]
    for level, pat in ((0.01, r"\((\d+) at threshold"),
                       (0.20, r"against (\d+) at \$0\.20"),
                       (0.05, r"of the four \((\d+)\)")):
        sub = thr[np.isclose(thr["value"], level)]
        check("violations", f"threshold {level} (finer rerun)",
              float(sub["violation_steps_total"].mean()), anchor2, pat, tol=0.5)

    coarse = pd.read_csv(ps.RESULTS / "final" / "design.csv")
    ct = coarse[coarse["factor"] == "stlsq_threshold"]
    levels = sorted(ct["value"].unique())
    for i, level in enumerate(levels):
        sub = ct[np.isclose(ct["value"], level)]
        pat = r"reproduces that dip \(" + r"\d+, " * i + r"(\d+)"
        check("violations", f"threshold {level} (canonical)",
              float(sub["violation_steps_total"].mean()), anchor2, pat, tol=0.5)

    anchor3 = "violation steps rise with it, from about"
    sweep = ps.load_mechanism("priced")
    lam = sweep[(sweep["block"] == "lambda") & (sweep["test_year"] == ps.IN_DIST_YEAR)]
    g = lam.groupby("lam")["violation_steps_total"].mean()
    check("violations", "lambda sweep, lowest level", float(g.iloc[0]), anchor3,
          r"about \$(\d+)\$ to", tol=5.0)
    check("violations", "lambda sweep, highest level", float(g.iloc[-1]), anchor3,
          r"to \$(\d+)\$ between", tol=5.0)


# ---------------------------------------------------------------------------
# Integer-valued claims: the structural counts of the grids
# ---------------------------------------------------------------------------

@passage("counts")
def check_structural_counts():
    """How many labels, fits, seed-cells and retained runs each block actually holds."""
    lad = ps.load_ladder(degree=None, denoise=None, optimizers=None)
    labels = lad.groupby(["variant", "degree", "optimizer", "denoise"]).ngroups

    anchor = "labelled configurations, covering"
    check("counts", "ladder labels", float(labels), anchor,
          r"evaluated (\d+) labelled configurations", tol=0.0)
    # constrained and sr3 are bit-identical, so two of the labels are one fit
    cols = ["nonzero", "kappa", "rollout_rmse_t_in", "diverged_frac", "one_step_rmse_t_in"]
    a = lad[lad["optimizer"] == "constrained"].sort_values(["variant", "degree",
                                                            "denoise", "seed"])
    b = lad[lad["optimizer"] == "sr3"].sort_values(["variant", "degree", "denoise", "seed"])
    identical = bool(len(a) == len(b) and np.allclose(a[cols].to_numpy(float),
                                                      b[cols].to_numpy(float)))
    distinct = labels - (len(a) // max(a["seed"].nunique(), 1) if identical else 0)
    check("counts", "distinct fits", float(distinct), anchor,
          r"covering (\d+) distinct fits", tol=0.0)

    anchor2 = "estimators produce bit-identical fits in all"
    cmp("counts", "constrained and sr3 are bit-identical", 1.0 if identical else 0.0, 1.0, 0.0)
    check("counts", "seed-cells compared", float(len(a)), anchor2,
          r"in all (\d+) seed-cells", tol=0.0)

    anchor3 = "configuration labels, each fitted on 20 seeds"
    check("counts", "ladder fits", float(len(lad)), anchor3, r"for (\d+) fits", tol=0.0)
    check("counts", "ladder seeds", float(lad["seed"].nunique()), anchor3,
          r"each fitted on (\d+) seeds", tol=0.0)

    hold = pd.read_csv(ps.RESULTS / "holdout" / "holdout_holdout.csv")
    anchor4 = "a separate held-out block"
    check("counts", "held-out fits", float(len(hold)), anchor4, r"\((\d+) fits", tol=0.0)
    check("counts", "held-out seeds", float(hold["seed"].nunique()), anchor4,
          r"(\d+) seeds \$\\times\$", tol=0.0)

    anchor5 = "returns exactly these three prices across all"
    main = ps.load_default_main()
    check("counts", "retained runs in the canonical wave", float(len(main)), anchor5,
          r"across all (\d+) retained runs", tol=0.0)

    anchor6 = "at about"
    orc = pd.read_csv(ps.RESULTS / "final" / "main.csv")
    orc = orc[(orc["method"] == "oracle_mpc") & (orc["test_year"] == 2022)]
    check("counts", "oracle season completion per cent",
          100 * float(orc["season_fraction"].mean()), anchor6,
          r"at about \$(\d+)\\,\\%\$", tol=0.5)

    # Section 2.9: how many wave manifests the tree holds, and how many distinct commits.
    # These counts collide with other claimed values (20 seeds, 11 features), so the
    # coverage walk cannot catch them drifting -- a wave added to the tree once moved
    # both without any check noticing.
    manifests = sorted(ps.RESULTS.rglob("regen_manifest.json"))
    shas = {str(json.loads(m.read_text(encoding="utf-8")).get("git_sha")) for m in manifests}
    anchor7 = "run manifests under"
    check("counts", "wave manifests in the tree", float(len(manifests)), anchor7,
          r"absent from all (\d+) run manifests", tol=0.0)
    anchor8 = "distinct values across those"
    check("counts", "distinct git_sha across manifests", float(len(shas)), anchor8,
          r"(\d+) distinct values across those", tol=0.0)
    check("counts", "manifests counted with the git_sha", float(len(manifests)), anchor8,
          r"distinct values across those (\d+) manifests", tol=0.0)
    cmp("counts", "no manifest carries an environment block",
        float(sum(1 for m in manifests
                  if {"env", "env_hash", "environment"}
                  & set(json.loads(m.read_text(encoding="utf-8"))))), 0.0, 0.0)


# ---------------------------------------------------------------------------
# Integer-valued claims: the configuration constants
# ---------------------------------------------------------------------------

@passage("config")
def check_config_constants():
    """Step length, season length, corridor bounds and the search generator's seed."""
    import importlib.util

    regen = HERE.parent.parent / "regen" / "regen_config.py"
    spec = importlib.util.spec_from_file_location("regen_config_ints", regen)
    C = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(C)

    anchor = "i.e.\\ 5760 control steps per season"
    check("config", "control step (s)", float(getattr(C, "PERIOD", float("nan"))) * 60
          if getattr(C, "PERIOD", 0) and C.PERIOD < 100 else float(getattr(C, "PERIOD", 0)),
          anchor, r"T_s=(\d+)\$~s", tol=0.0)

    main = ps.load_default_main()
    check("config", "control steps per season", float(main["steps_expected"].max()),
          anchor, r"i\.e\.\\? (\d+) control steps", tol=0.0)

    support = (HERE.parent.parent / "regen" / "experiments_support.py")
    if support.exists():
        txt = support.read_text(encoding="utf-8")
        m = re.search(r"default_rng\((\d+)\)", txt)
        if m:
            check("config", "search generator seed", float(m.group(1)),
                  "drawn i.i.d.\\ uniformly from a fixed generator",
                  r"default\\_rng\((\d+)\)", tol=0.0)

    # Section 2.1: the excitation applied while collecting identification data. The
    # amplitudes are regen_config constants; the two periods are defaults of the collector
    # (prbs_period) and of the protocol dataclass (noise_period).
    utils_src = (HERE.parent.parent / "article_experiment_utils.py").read_text(encoding="utf-8")
    proto_src = (HERE.parent.parent / "protocol_config.py").read_text(encoding="utf-8")
    anchor_x = "pseudo-random binary excitation of amplitude"
    check("config", "PRBS amplitude", float(getattr(C, "PRBS_SCALE", float("nan"))), anchor_x,
          r"excitation of amplitude (\d+\.\d+)")
    m = re.search(r"prbs_period: int = (\d+)", utils_src)
    check("config", "PRBS switching period (steps)", float(m.group(1)) if m else float("nan"),
          anchor_x, r"redrawn every (\d+) steps \(", tol=0.0)
    check("config", "PRBS switching period (hours)",
          float(m.group(1)) * float(C.PERIOD) / 3600 if m else float("nan"),
          anchor_x, r"steps \((\d+)~h\)", tol=0.0)
    check("config", "noise amplitude", float(getattr(C, "NOISE_SCALE", float("nan"))), anchor_x,
          r"standard deviation (\d+\.\d+)")
    m = re.search(r"noise_period: int = (\d+)", proto_src)
    check("config", "noise refresh period (steps)", float(m.group(1)) if m else float("nan"),
          anchor_x, r"redrawn every (\d+) steps, the sum", tol=0.0)
    check("config", "training steps per season", float(main["steps_expected"].max()),
          anchor_x, r"trajectories of (\d+) control steps", tol=0.0)

    # Section 2.3: the reinforcement-learning budget, and the reference budget it is set
    # against -- Table 2 of van Laatum, van Henten & Boersma, GreenLight-Gym
    # (arXiv:2410.05336): total timesteps 2M for PPO and SAC. The reference value is an
    # external constant and is recorded here, not derived.
    anchor_rl = "The training budget of the two agents is also modest"
    rl_steps = float(getattr(C, "RL_TRAIN_STEPS", float("nan")))
    s = sentence(anchor_rl)
    m1 = re.search(r"\$(\d)\\cdot10\^\{(\d)\}\$ environment steps", s)
    m2 = re.search(r"against the \$(\d)\\cdot10\^\{(\d)\}\$ steps", s)
    cmp("config", "RL training steps", rl_steps,
        float(m1.group(1)) * 10 ** float(m1.group(2)) if m1 else float("nan"), 0.0)
    cmp("config", "GreenLight-Gym reference RL budget (external constant)", 2e6,
        float(m2.group(1)) * 10 ** float(m2.group(2)) if m2 else float("nan"), 0.0)
    check("config", "RL budget in seasons", rl_steps / float(main["steps_expected"].max()),
          anchor_rl, r"about (\d+)\s+seasons", tol=0.5)

    # Section 2.4: the size of the degree-1 candidate set per state equation and in Xi
    names = ps.library_feature_names()
    n_feat = {lib: len(v) for lib, v in names.items()}
    n_feat.setdefault("physics_no_tuboil", n_feat["physics"] - 1)
    anchor_lib = "each state equation selects from"
    for i, lib in enumerate(("raw", "physics_no_cross", "physics")):
        pat = (r"selects from (\d+), \d+ and \d+ columns", r"selects from \d+, (\d+) and \d+ columns",
               r"selects from \d+, \d+ and (\d+) columns")[i]
        check("config", f"candidate columns, {lib}", float(1 + 3 + n_feat[lib]), anchor_lib,
              pat, tol=0.0)
    check("config", "candidate columns, deletion library",
          float(1 + 3 + n_feat["physics_no_tuboil"]), anchor_lib,
          r"\((\d+) for the deletion library\)", tol=0.0)
    for i, lib in enumerate(("raw", "physics_no_cross", "physics", "physics_no_tuboil")):
        pat = (r"that is (\d+), \d+, \d+ and \d+ candidate", r"that is \d+, (\d+), \d+ and \d+ candidate",
               r"that is \d+, \d+, (\d+) and \d+ candidate", r"that is \d+, \d+, \d+ and (\d+) candidate")[i]
        check("config", f"candidate coefficients, {lib}", float(3 * (1 + 3 + n_feat[lib])),
              anchor_lib, pat, tol=0.0)


# ---------------------------------------------------------------------------
# The corridors, the horizons, and the abstract's percentages
# ---------------------------------------------------------------------------

@passage("bounds")
def check_bounds_prose():
    """Corridor limits and rollout horizons, against the modules that define them, and the
    abstract's survival triple, against the one-factor library comparison."""
    import importlib.util

    utils = (HERE.parent.parent / "article_experiment_utils.py").read_text(encoding="utf-8")
    m = re.search(r'DEFAULT_CORRIDORS = \{"co2": \(([\d.]+), ([\d.]+)\), '
                  r'"t_in": \(([\d.]+), ([\d.]+)\), "rh": \(([\d.]+), ([\d.]+)\)\}', utils)
    anchor = "The simulator's productive band is"
    if m:
        for i, (what, pat) in enumerate((
                ("CO2 corridor lower", r"CO\$_2\\in\[(\d+),"),
                ("CO2 corridor upper", r"CO\$_2\\in\[\d+,(\d+)\]"),
                ("temperature corridor lower", r"temperature \$\[(\d+),"),
                ("temperature corridor upper", r"temperature \$\[\d+,(\d+)\]"),
                ("humidity corridor lower", r"humidity \$\[(\d+),"),
                ("humidity corridor upper", r"humidity \$\[\d+,(\d+)\]"))):
            check("bounds", what, float(m.group(i + 1)), anchor, pat, tol=0.0)
    else:
        cmp("bounds", "corridor definition not found", 0.0, 1.0, 0.0)

    regen = HERE.parent.parent / "regen" / "regen_config.py"
    spec = importlib.util.spec_from_file_location("regen_config_bounds", regen)
    C = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(C)
    anchor2 = "divergence fraction at horizons of"
    for i, h in enumerate(C.LADDER_ROLLOUT_HORIZONS_STEPS):
        pat = (r"horizons of (\d+)", r"horizons of \d+, (\d+)", r"horizons of \d+, \d+ and (\d+)")[i]
        check("bounds", f"rollout horizon {i + 1}", float(h), anchor2, pat, tol=0.0)

    # the abstract states boiler-term survival as whole percentages
    one = ps.library_one_factor("ensemble").set_index("library")
    anchor3 = "performance instead tracked survival of the direct boiler coefficient"
    for i, lib in enumerate(("raw", "physics_no_cross", "physics")):
        pat = (r"\((\d+), \d+, \d+~", r"\(\d+, (\d+), \d+~", r"\(\d+, \d+, (\d+)~")[i]
        check("bounds", f"{lib} survival per cent",
              100 * float(one.loc[lib, "survival"]), anchor3, pat, tol=0.5)

    # the MPC's own hard bounds, which are tighter at the bottom and looser at the top
    # than the simulator's productive corridor and must not be confused with it
    anchor5 = "the temperature bounds"
    lo = re.search(r'mpc\.bounds\["lower", "_x", "t_in"\] = ([\d.]+)', utils)
    hi = re.search(r'mpc\.bounds\["upper", "_x", "t_in"\] = ([\d.]+)', utils)
    vent = re.search(r'mpc\.bounds\["upper", "_u", "uVent"\] = ([\d.]+)', utils)
    if lo and hi and vent:
        check("bounds", "MPC temperature lower bound", float(lo.group(1)), anchor5,
              r"temperature bounds \$\[(\d+),", tol=0.0)
        check("bounds", "MPC temperature upper bound", float(hi.group(1)), anchor5,
              r"temperature bounds \$\[\d+,(\d+)\]", tol=0.0)
        check("bounds", "MPC ventilation upper bound", float(vent.group(1)), anchor5,
              r"ventilation bound \$(\d+\.\d+)\$")
    else:
        cmp("bounds", "MPC bounds not found", 0.0, 1.0, 0.0)

    # the move-suppression weights of Equation (3), read from do-mpc's set_rterm call in
    # the order the equation states them (boiler, CO2, thermal screen, vent, lamps, blackout)
    rterm = re.search(r"set_rterm\((.*?)\)", utils, re.S)
    if rterm:
        got = {k: float(v) for k, v in re.findall(r"(\w+)=([\d.]+)", rterm.group(1))}
        order = ("uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr")
        anchor6 = "in the actuator order of"
        for i, name in enumerate(order):
            pat = r"diag\}\(" + r"\d+," * i + r"(\d+)"
            check("bounds", f"move-suppression weight {name}", got.get(name, float("nan")),
                  anchor6, pat, tol=0.0)
    else:
        cmp("bounds", "set_rterm block not found", 0.0, 1.0, 0.0)

    # outdoor CO2 is a fixed weather column, not a corridor
    weather = (HERE.parent.parent / "make_weather.py").read_text(encoding="utf-8")
    m = re.search(r'"CO2 concentration": ([\d.]+)', weather)
    anchor4 = "Outdoor CO$_2$ was held at"
    if m:
        check("bounds", "outdoor CO2", float(m.group(1)), anchor4, r"held at (\d+)~ppm",
              tol=0.0)
    else:
        cmp("bounds", "outdoor CO2 constant not found in make_weather", 0.0, 1.0, 0.0)


# ---------------------------------------------------------------------------
# Section 3.5 -- the observational association, library by library
# ---------------------------------------------------------------------------

@passage("association")
def check_association_prose():
    """Whether boiler survival tracks margin inside each library, under each objective.

    Three of the five tests are null, which is the point of the sentence: the association
    is significant only inside the middle library, and the causal estimate is the knock-in.
    """
    from scipy.stats import mannwhitneyu

    priced = ps.load_library_pool()
    default = pd.concat([ps.load_default_main(), ps.load_raw_library_default()],
                        ignore_index=True)
    default["library"] = default["method"].map(ps.METHOD_LIBRARY)
    default["boiler_alive"] = (default["xi_uboil"].fillna(0.0).abs() > 0).astype(float)

    def association(pool, lib):
        d = pool[pool["library"] == lib]
        per = d.groupby(["method", "seed"]).agg(alive=("boiler_alive", "max"),
                                                epi=("epi", "mean")).reset_index()
        keep = per[per["alive"] > 0]["epi"]
        drop = per[per["alive"] == 0]["epi"]
        return float(mannwhitneyu(keep, drop)[1])

    anchor = "association is significant only inside"
    check("association", "physics_no_cross, priced",
          association(priced, "physics_no_cross"), anchor, r"\$p=(\d+\.\d+)\$ priced")
    check("association", "physics_no_cross, original",
          association(default, "physics_no_cross"), anchor, r"\$p=(\d+\.\d+)\$ default")
    check("association", "raw, priced", association(priced, "raw"), anchor,
          r"raw\} \(\$p=(\d+\.\d+)\$")
    check("association", "raw, original", association(default, "raw"), anchor,
          r"raw\} \(\$p=\d+\.\d+\$, \$p=(\d+\.\d+)\$")
    check("association", "physics, priced", association(priced, "physics"), anchor,
          r"physics\} \(\$p=(\d+\.\d+)\$")


# ---------------------------------------------------------------------------
# The figure 3 caption: the knock-in under both stage costs, and the knock-out
# ---------------------------------------------------------------------------

@passage("knockcaption")
def check_knock_caption():
    """What the panel used to print inside its axes, now stated in the caption."""
    from scipy.stats import wilcoxon

    raw, eff = {}, {}
    for obj in ("priced", "default"):
        k = ps.knock_effects(objective=obj)
        for name in ("knockin", "knockout"):
            v = np.asarray(k[name], float)
            v = v[~np.isnan(v)]
            eff[(obj, name)] = v
            try:
                raw[(obj, name)] = float(wilcoxon(v).pvalue)
            except ValueError:
                raw[(obj, name)] = float("nan")
    adj = ps.holm(raw)

    anchor = "The knock-in is positive in"
    d = eff[("default", "knockin")]
    check("knockcaption", "default knock-in wins", float((d > 0).sum()), anchor,
          r"positive in (\d+) of 20", tol=0.0)
    check("knockcaption", "default knock-in p", raw[("default", "knockin")], anchor,
          r"\$p=(\d+\.\d+)\\times10\^\{-4\}\$", scale=1e-4)
    check("knockcaption", "default knock-in mean", float(d.mean()), anchor,
          r"mean \$\+(\d+\.\d+)\$\)")
    pr = eff[("priced", "knockin")]
    check("knockcaption", "priced knock-in wins", float((pr > 0).sum()), anchor,
          r"and in (\d+) of 20", tol=0.0)
    check("knockcaption", "priced knock-in p", raw[("priced", "knockin")], anchor,
          r"one \(\$p=(\d+\.\d+)\\times10\^\{-4\}\$", scale=1e-4)
    check("knockcaption", "priced knock-in mean", float(pr.mean()), anchor,
          r"mean \$\+(\d+\.\d+)\$\);")
    check("knockcaption", "default knock-in, Holm over four",
          adj[("default", "knockin")], anchor,
          r"gives \$(\d+\.\d+)\\times10\^\{-3\}\$", scale=1e-3)
    check("knockcaption", "priced knock-in, Holm over four",
          adj[("priced", "knockin")], anchor,
          r"and \$(\d+\.\d+)\\times10\^\{-3\}\$", scale=1e-3)

    anchor2 = "The complementary knock-out is null"
    for obj in ("default", "priced"):
        v = eff[(obj, "knockout")]
        cmp("knockcaption", f"{obj} knock-out median", float(np.median(v)), 0.0, 0.005)
        cmp("knockcaption", f"{obj} knock-out wins", float((v > 0).sum()), 1.0, 0.0)
    check("knockcaption", "knock-out median as printed", 0.0, anchor2,
          r"median \$\+(\d+\.\d+)\$")
    check("knockcaption", "knock-out positives as printed",
          float((eff[("priced", "knockout")] > 0).sum()), anchor2,
          r"one positive replicate of (\d+)", group=1, tol=19.5)


# ---------------------------------------------------------------------------
# Section 3.3 -- the headline contrast by season and at seed level, and the seed-level
# count of controllers separable from the tuned heuristic
# ---------------------------------------------------------------------------

@passage("seedlevel")
def check_seed_level_prose():
    """The seed is the unit at which the surrogates are independent; these sentences
    restate the run-level results on per-seed four-season means, Holm over the family of
    15 with monotone enforcement, exactly as the two tables do."""
    from scipy.stats import wilcoxon

    pool = full_pool()

    def p_of(d):
        d = np.asarray(d, float)
        d = d[~np.isnan(d)]
        return wilcoxon(d)[1] if len(d) > 1 and np.any(d != 0) else 1.0

    # (a) the headline paired contrast raw_ens - lowthr
    anchor = "is paired on (seed, season)"
    d = ps.paired_deltas(pool, "sindy_mpc_raw_ens", "sindy_mpc_lowthr")
    check("seedlevel", "headline paired mean", float(d.mean()), anchor, r"mean \$\+(\d+\.\d+)\$")
    check("seedlevel", "headline paired median", float(d.median()), anchor,
          r"median \$\+(\d+\.\d+)\$")
    check("seedlevel", "headline paired wins", float((d > 0).sum()), anchor,
          r"ahead in (\d+) of 80 pairs", tol=0.0)
    check("seedlevel", "headline paired n", float(len(d)), anchor,
          r"ahead in \d+ of (\d+) pairs", tol=0.0)
    rp = {}
    for m in pool["method"].unique():
        if m != "sindy_mpc_raw_ens":
            rp[m] = p_of(ps.paired_deltas(pool, "sindy_mpc_raw_ens", m))
    check("seedlevel", "headline paired p_Holm(15)", _holm(rp, 15)["sindy_mpc_lowthr"],
          anchor, r"p_\{\\text\{Holm\}\}=(\d+\.\d+)\\times10\^\{-4\}", scale=1e-4)

    anchor2 = "It is not uniform across seasons"
    by_year = {}
    for yr in (2020, 2021, 2022, 2023):
        a = pool[(pool.method == "sindy_mpc_raw_ens") & (pool.test_year == yr)].set_index("seed")["epi"]
        b = pool[(pool.method == "sindy_mpc_lowthr") & (pool.test_year == yr)].set_index("seed")["epi"]
        by_year[yr] = (a - b).dropna()
    check("seedlevel", "2020 wins", float((by_year[2020] > 0).sum()), anchor2,
          r"leads in all (\d+) replicates in 2020", tol=0.0)
    cmp("seedlevel", "2023 wins equal 2020 wins", float((by_year[2023] > 0).sum()),
        float((by_year[2020] > 0).sum()), 0.0)
    check("seedlevel", "2022 wins", float((by_year[2022] > 0).sum()), anchor2,
          r"and in (\d+) in 2022", tol=0.0)
    check("seedlevel", "2021 wins", float((by_year[2021] > 0).sum()), anchor2,
          r"trails in 2021 \((\d+) of 20", tol=0.0)
    check("seedlevel", "2021 p", p_of(by_year[2021]), anchor2,
          r"\$p=(\d+\.\d+)\\times10\^\{-3\}", scale=1e-3)

    anchor3 = "it holds in 16 of 20 replicates"
    ds = d.groupby(level="seed").mean()
    rs = {}
    for m in pool["method"].unique():
        if m != "sindy_mpc_raw_ens":
            rs[m] = p_of(ps.paired_deltas(pool, "sindy_mpc_raw_ens", m).groupby(level="seed").mean())
    check("seedlevel", "headline seed-level wins", float((ds > 0).sum()), anchor3,
          r"holds in (\d+) of 20 replicates", tol=0.0)
    check("seedlevel", "headline seed-level n", float(len(ds)), anchor3,
          r"holds in \d+ of (\d+) replicates", tol=0.0)
    check("seedlevel", "headline seed-level p_Holm(15)", _holm(rs, 15)["sindy_mpc_lowthr"],
          anchor3, r"p_\{\\text\{Holm\}\}=(\d+\.\d+)\\times10\^\{-3\}", scale=1e-3)

    # (b) the seed-level count against the tuned heuristic
    tuned = pool[pool.method == "rule_based_tuned"].groupby("test_year")["epi"].mean()
    seed_d, seed_p = {}, {}
    for m in pool["method"].unique():
        if m == "rule_based_tuned":
            continue
        g = pool[pool.method == m]
        per = (g["epi"] - g["test_year"].map(tuned)).groupby(g["seed"]).mean()
        seed_d[m] = np.asarray(per, float)
        seed_p[m] = p_of(per)
    adj = _holm(seed_p, 15)
    anchor4 = "On per-seed means the count"
    check("seedlevel", "raw_ens seed wins", float((seed_d["sindy_mpc_raw_ens"] > 0).sum()),
          anchor4, r"\((\d+) of 20 and \d+ of 20 seeds", tol=0.0)
    check("seedlevel", "raw seed wins", float((seed_d["sindy_mpc_raw"] > 0).sum()),
          anchor4, r"\(\d+ of 20 and (\d+) of 20 seeds", tol=0.0)
    check("seedlevel", "raw_ens seed p_Holm", adj["sindy_mpc_raw_ens"], anchor4,
          r"p_\{\\text\{Holm\}\}=(\d+\.\d+)\\times10\^\{-5\}", scale=1e-5)
    check("seedlevel", "raw seed p_Holm", adj["sindy_mpc_raw"], anchor4,
          r"10\^\{-5\}\$ and \$(\d+\.\d+)\$\)")
    check("seedlevel", "lowthr seed wins", float((seed_d["sindy_mpc_lowthr"] > 0).sum()),
          anchor4, r"\((\d+) of 20 each", tol=0.0)
    cmp("seedlevel", "dense seed wins equal lowthr's", float((seed_d["sindy_mpc_dense"] > 0).sum()),
        float((seed_d["sindy_mpc_lowthr"] > 0).sum()), 0.0)
    check("seedlevel", "lowthr seed p_Holm", adj["sindy_mpc_lowthr"], anchor4,
          r"of 20 each, \$p_\{\\text\{Holm\}\}=(\d+\.\d+)\$\)")
    cmp("seedlevel", "dense seed p_Holm equals lowthr's", adj["sindy_mpc_dense"],
        adj["sindy_mpc_lowthr"], 1e-9)
    # the two that lose significance below the reference
    cmp("seedlevel", "conf not significant at seed level",
        1.0 if adj["sindy_mpc_conf"] > 0.05 else 0.0, 1.0, 0.0)
    cmp("seedlevel", "dense_dagger not significant at seed level",
        1.0 if adj["sindy_mpc_dense_dagger"] > 0.05 else 0.0, 1.0, 0.0)
    cmp("seedlevel", "phys_ens, phys, conf_dagger not significant at seed level",
        float(sum(adj[m] > 0.05 for m in ("sindy_mpc_phys_ens", "sindy_mpc_phys",
                                          "sindy_mpc_conf_dagger"))), 3.0, 0.0)


# ---------------------------------------------------------------------------
# Section 3.5 -- Figure 1d: how far the surviving boiler coefficients sit above the cut
# ---------------------------------------------------------------------------

@passage("paneld")
def check_panel_d_prose():
    """Surviving |xi_uBoil| per library, ensemble arm of the one-factor set. Only survivors
    are observable: a cut coefficient is stored as exactly zero."""
    coef = ps.boiler_coefficients("ensemble")
    alive = {lib: np.sort(coef[(coef["library"] == lib) & coef["alive"]]["abs_xi"].to_numpy(float))
             for lib in ("raw", "physics_no_cross", "physics")}
    total = {lib: int((coef["library"] == lib).sum()) for lib in alive}
    anchor = "Where the direct boiler coefficient survives"
    check("paneld", "raw survivors, low", float(alive["raw"].min()), anchor,
          r"lies between \$(\d+\.\d+)\$ and \$\d+\.\d+\$ in the raw")
    check("paneld", "raw survivors, high", float(alive["raw"].max()), anchor,
          r"lies between \$\d+\.\d+\$ and \$(\d+\.\d+)\$ in the raw")
    check("paneld", "raw survivors, median", float(np.median(alive["raw"])), anchor,
          r"in the raw library \(median \$(\d+\.\d+)\$")
    check("paneld", "raw survivors, count", float(len(alive["raw"])), anchor,
          r"in the raw library \(median \$\d+\.\d+\$, (\d+) of 20", tol=0.0)
    cmp("paneld", "raw replicates", float(total["raw"]), 20.0, 0.0)
    check("paneld", "no-cross survivors, low", float(alive["physics_no_cross"].min()), anchor,
          r"and between \$(\d+\.\d+)\$ and \$\d+\.\d+\$ in the library without")
    check("paneld", "no-cross survivors, high", float(alive["physics_no_cross"].max()), anchor,
          r"and between \$\d+\.\d+\$ and \$(\d+\.\d+)\$ in the library without")
    check("paneld", "no-cross survivors, median", float(np.median(alive["physics_no_cross"])),
          anchor, r"without cross terms \(median \$(\d+\.\d+)\$")
    check("paneld", "no-cross survivors, count", float(len(alive["physics_no_cross"])), anchor,
          r"without cross terms \(median \$\d+\.\d+\$, (\d+) of 20", tol=0.0)
    ph = alive["physics"]
    check("paneld", "physics survivors, count", float(len(ph)), anchor,
          r"\d+ of its (\d+) survivors", tol=0.0)
    check("paneld", "physics survivors, low group", float(((ph >= 0.05) & (ph < 0.07)).sum()),
          anchor, r"(\d+) of its \d+ survivors lie between \$0\.05\$ and \$0\.07\$", tol=0.0)
    check("paneld", "physics survivors, high group", float(((ph >= 0.14) & (ph < 0.20)).sum()),
          anchor, r"and (\d+) between \$0\.14\$ and \$0\.19\$", tol=0.0)
    check("paneld", "physics survivors, high group ceiling", float(ph.max()), anchor,
          r"between \$0\.14\$ and \$(\d+\.\d+)\$")
    check("paneld", "physics survivors, median", float(np.median(ph)), anchor,
          r"\$0\.19\$ \(median \$(\d+\.\d+)\$\)")
    anchor2 = "so the survival gap between them"
    check("paneld", "raw survivors restated", float(len(alive["raw"])), anchor2,
          r"\((\d+) against \d+ of 20\)", tol=0.0)
    check("paneld", "no-cross survivors restated", float(len(alive["physics_no_cross"])), anchor2,
          r"\(\d+ against (\d+) of 20\)", tol=0.0)
    cmp("paneld", "every raw and no-cross survivor is below 0.10",
        float(max(alive["raw"].max(), alive["physics_no_cross"].max()) < 0.10), 1.0, 0.0)


def main() -> int:
    wanted = sys.argv[1:]
    names = [k for k in CHECKS if not wanted or k in wanted]
    for name in names:
        print(f"\n=== {name}")
        try:
            CHECKS[name]()
        except Exception as exc:  # noqa: BLE001
            print(f"    checker failed: {type(exc).__name__}: {exc}")
            vt.RESULTS.append((name, f"checker error: {exc}", float("nan"),
                               float("nan"), False))
        for lab, what, got, want, ok in vt.RESULTS:
            if lab == name:
                mark = "ok  " if ok else "MISMATCH"
                print(f"  [{mark}] {what:<46s} tree {got:>11.4g}  paper {want:>11.4g}")

    bad = [r for r in vt.RESULTS if not r[4]]
    print("\n" + "=" * 96)
    print(f"checked {len(vt.RESULTS)} prose values, mismatched {len(bad)}")
    for lab, what, got, want, _ in bad:
        print(f"   ! {lab} {what}: tree {got:.6g} vs paper {want:.6g}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
