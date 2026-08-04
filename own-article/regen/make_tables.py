"""Every number the paper states, derived from the merged regen output. One lineage.

Run after `run_regen.py --merge`. Reads only `<out>/{main,mechanism,parity,ladder,adapt,
guard,faults,design}.csv` and writes `<out>/tables/*.csv` plus `NUMBERS.md`, which maps
each claim in the manuscript to the file, column and row it comes from. That mapping is
the actual deliverable: it is what makes "confidence in the numbers" checkable rather than
asserted.

Statistical choices worth stating, because the 2026-07 analysis got two of them wrong:

* The rule-based reference is DETERMINISTIC on a fixed season (epi_std == 0 in every year).
  A "paired Wilcoxon by seed" against it is arithmetically a ONE-SAMPLE signed-rank test of
  the contender against a constant; pairing removes no variance. This module detects the
  zero-variance case and labels the test accordingly (`test_type` column) instead of
  reporting it as paired.
* Four seasons is a small sample for a season-level claim. The cross-season mean is
  therefore reported with a bootstrap interval over SEASONS, and the headline is the
  per-season win count, not the interval.

Prices: `epi_metrics` reads the simulator's per-step profit, so prices cannot be varied
inside a rollout. They are re-derived exactly from the recorded physical quantities
(revenue scales with the fruit price; heat/electricity/CO2 costs scale with theirs), which
holds the control trajectories fixed at their nominal-price optimum. That measures how
robust the RANKING is to prices -- not re-optimised operation, and the tables say so.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import regen_config as C  # noqa: E402

NOMINAL_FRUIT_PRICE = 1.6      # EUR/kg, as read from the simulator
BOOT = 10000
RNG_SEED = 20260803            # fixed: the bootstrap must be reproducible too


# ── statistics ───────────────────────────────────────────────────────────────

def _boot_ci(x, stat=np.mean, n=BOOT, alpha=0.05):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(RNG_SEED)
    idx = rng.integers(0, len(x), size=(n, len(x)))
    vals = stat(x[idx], axis=1)
    return (float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2)))


def _compare(contender: np.ndarray, reference: np.ndarray) -> dict:
    """Contender vs reference, choosing the test the data actually supports.

    If the reference has no variance (a deterministic controller on a fixed season), the
    paired test degenerates to a one-sample signed-rank test against a constant. Reporting
    it as "paired" overstates what the design bought.
    """
    from scipy import stats

    a = np.asarray(contender, float)
    b = np.asarray(reference, float)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    d = a - b
    ref_const = bool(np.nanstd(b) < 1e-12)
    out = {"n": int(n),
           "test_type": "one_sample_signed_rank_vs_constant" if ref_const else "paired_wilcoxon",
           "delta_mean": float(np.nanmean(d)),
           "delta_median": float(np.nanmedian(d)),
           "n_positive": int(np.nansum(d > 0)),
           "reference_is_constant": ref_const}
    out["delta_ci_lo"], out["delta_ci_hi"] = _boot_ci(d)
    try:
        out["p_raw"] = float(stats.wilcoxon(d, alternative="two-sided").pvalue)
    except Exception:
        out["p_raw"] = np.nan
    sd = np.nanstd(d, ddof=1)
    out["cohens_dz"] = float(np.nanmean(d) / sd) if sd > 0 else np.nan
    # Rank-biserial: robust companion to d_z, meaningful for a signed-rank test.
    pos = np.nansum(d > 0)
    neg = np.nansum(d < 0)
    out["rank_biserial"] = float((pos - neg) / (pos + neg)) if (pos + neg) else np.nan
    return out


def _holm(pvals: list[float]) -> list[float]:
    idx = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(idx):
        val = (m - rank) * pvals[i]
        run = max(run, val)
        adj[i] = min(1.0, run)
    return list(adj)


# ── tables ───────────────────────────────────────────────────────────────────

def table_main(d: pd.DataFrame, tdir: Path, claims: list) -> None:
    valid = d[~d["truncated"].astype(bool)] if "truncated" in d.columns else d
    by_year = (valid.groupby(["test_year", "method"])
               .agg(epi_mean=("epi", "mean"), epi_std=("epi", "std"),
                    epi_median=("epi", "median"),
                    epi_q25=("epi", lambda x: x.quantile(0.25)),
                    epi_q75=("epi", lambda x: x.quantile(0.75)),
                    viol_mean=("violation_steps_total", "mean"),
                    n=("epi", "size"))
               .reset_index().sort_values(["test_year", "epi_mean"], ascending=[True, False]))
    by_year.to_csv(tdir / "main_by_year.csv", index=False)

    pooled = (by_year.groupby("method")
              .agg(mean_over_seasons=("epi_mean", "mean"),
                   worst_season=("epi_mean", "min"), seasons=("epi_mean", "size"))
              .reset_index())
    # Bootstrap over SEASONS (n=4): the honest interval for a cross-season statement.
    cis = {}
    for m, g in by_year.groupby("method"):
        cis[m] = _boot_ci(g.epi_mean.to_numpy())
    pooled["ci_lo"] = pooled.method.map(lambda m: cis.get(m, (np.nan, np.nan))[0])
    pooled["ci_hi"] = pooled.method.map(lambda m: cis.get(m, (np.nan, np.nan))[1])
    # Win count per season -- the statistic the paper actually leans on.
    wins = (by_year.loc[by_year.groupby("test_year").epi_mean.idxmax()]
            .groupby("method").size())
    pooled["seasons_won"] = pooled.method.map(wins).fillna(0).astype(int)
    pooled = pooled.sort_values("mean_over_seasons", ascending=False)
    pooled.to_csv(tdir / "main_pooled.csv", index=False)

    top = pooled.iloc[0]
    claims.append(("Cross-season leader", f"{top.method}: {top.mean_over_seasons:+.2f} EUR/m2, "
                   f"wins {top.seasons_won}/{int(top.seasons)} seasons, "
                   f"season-bootstrap CI [{top.ci_lo:+.2f}, {top.ci_hi:+.2f}]",
                   "tables/main_pooled.csv"))

    # Per-season comparisons against every other controller, Holm-corrected within season.
    rows = []
    for (year, ref) in [(y, "rule_based") for y in sorted(valid.test_year.unique())]:
        sub = valid[valid.test_year == year]
        b = sub[sub.method == ref].sort_values("seed").epi.to_numpy()
        if not len(b):
            continue
        recs = []
        for m, g in sub.groupby("method"):
            if m == ref:
                continue
            r = _compare(g.sort_values("seed").epi.to_numpy(), b)
            r.update({"test_year": year, "method": m, "reference": ref})
            recs.append(r)
        for r, p in zip(recs, _holm([x["p_raw"] for x in recs])):
            r["p_holm"] = p
        rows.extend(recs)
    if rows:
        st = pd.DataFrame(rows)
        st.to_csv(tdir / "main_stats_vs_rule_based.csv", index=False)
        kinds = st.test_type.unique()
        claims.append(("Test used against the rule-based reference", ", ".join(kinds),
                       "tables/main_stats_vs_rule_based.csv"))


def table_prices(d: pd.DataFrame, tdir: Path, claims: list) -> None:
    """Price tornado, re-derived exactly from recorded physical quantities."""
    need = {"revenue", "cost_heat", "cost_co2", "cost_elec"}
    if not need <= set(d.columns):
        return
    valid = d[~d["truncated"].astype(bool)] if "truncated" in d.columns else d
    base = valid[valid.test_year == C.IN_DIST_YEAR]
    if not len(base):
        return
    rows = []
    for pf in C.SENS_FRUIT_PRICE:
        for ke in C.SENS_ENERGY_SCALE:
            j = (base.revenue * (pf / NOMINAL_FRUIT_PRICE)
                 - ke * (base.cost_heat + base.cost_co2 + base.cost_elec))
            g = base.assign(j=j).groupby("method").j.mean().reset_index()
            g["fruit_price"] = pf
            g["energy_scale"] = ke
            rows.append(g)
    t = pd.concat(rows, ignore_index=True)
    t.to_csv(tdir / "sensitivity_prices.csv", index=False)

    span = (t.groupby("method").j.agg(lambda x: x.max() - x.min())
            .reset_index().rename(columns={"j": "span_over_price_grid"}))
    span.to_csv(tdir / "sensitivity_price_span.csv", index=False)

    # Does the ranking survive the price grid? The paper claims it does not.
    winners = t.loc[t.groupby(["fruit_price", "energy_scale"]).j.idxmax()]
    uniq = sorted(winners.method.unique())
    claims.append(("Ranking stability across the price grid",
                   f"{len(uniq)} distinct winner(s): {uniq}", "tables/sensitivity_prices.csv"))


def table_mechanism(d: pd.DataFrame, tdir: Path, claims: list) -> None:
    if d is None or "block" not in d.columns:
        return
    lam = d[d.block == "lambda"]
    if len(lam):
        t = (lam.groupby("lam")
             .agg(nonzero=("nonzero", "mean"), xi_uboil=("xi_uboil", "mean"),
                  rollout_rmse=("rollout_rmse", "mean"), epi_mean=("epi", "mean"),
                  epi_std=("epi", "std"),
                  viol_mean=("violation_steps_total", "mean"), n=("epi", "size"))
             .reset_index().sort_values("lam"))
        t.to_csv(tdir / "lambda_sweep.csv", index=False)
        zero = t[t.xi_uboil.abs() < 1e-12]
        nz = t[t.xi_uboil.abs() > 1e-12]
        if len(zero) and len(nz):
            claims.append(("EPI monotone in the boiler coefficient?",
                           f"min EPI with xi!=0 = {nz.epi_mean.min():+.2f}; "
                           f"mean EPI with xi==0 = {zero.epi_mean.mean():+.2f} -> "
                           f"{'monotone' if zero.epi_mean.mean() <= nz.epi_mean.min() else 'NOT monotone'}",
                           "tables/lambda_sweep.csv"))

    knock = d[d.block == "knock"]
    if len(knock):
        piv = knock.pivot_table(index="seed", columns="condition", values="epi")
        rows = []
        for a, b in (("knockin", "baseline"), ("knockout", "baseline")):
            if {a, b} <= set(piv.columns):
                r = _compare(piv[a].to_numpy(), piv[b].to_numpy())
                r.update({"contrast": f"{a}-{b}"})
                rows.append(r)
        if rows:
            st = pd.DataFrame(rows)
            for r, p in zip(rows, _holm([x["p_raw"] for x in rows])):
                r["p_holm"] = p
            st = pd.DataFrame(rows)
            st.to_csv(tdir / "knock_effect.csv", index=False)
            ki = st[st.contrast == "knockin-baseline"]
            if len(ki):
                r = ki.iloc[0]
                claims.append(("Single-coefficient knock-in effect",
                               f"median {r.delta_median:+.2f} EUR/m2, CI "
                               f"[{r.delta_ci_lo:+.2f}, {r.delta_ci_hi:+.2f}], "
                               f"p={r.p_raw:.2g}, positive {r.n_positive}/{r.n}",
                               "tables/knock_effect.csv"))

    cross = d[d.block == "cross"]
    if len(cross):
        piv = cross.pivot_table(index="seed", columns="condition", values="epi")
        rows = []
        for a, b in (("ko_uboil", "baseline"), ("ko_both", "ko_uboil"), ("ko_cross", "baseline")):
            if {a, b} <= set(piv.columns):
                r = _compare(piv[a].to_numpy(), piv[b].to_numpy())
                r["contrast"] = f"{a}-{b}"
                rows.append(r)
        if rows:
            pd.DataFrame(rows).to_csv(tdir / "cross_interaction.csv", index=False)
            cb = [r for r in rows if r["contrast"] == "ko_both-ko_uboil"]
            if cb:
                r = cb[0]
                claims.append(("Cross-term (t_uBoil) interaction",
                               f"delta {r['delta_median']:+.2f}, p={r['p_raw']:.2g} -> "
                               f"{'adds nothing' if r['p_raw'] > 0.05 else 'ADDS a real effect'}",
                               "tables/cross_interaction.csv"))


def table_simple(d: pd.DataFrame, name: str, tdir: Path, claims: list,
                 group=("block", "condition")) -> None:
    if d is None or not len(d):
        return
    g = [c for c in group if c in d.columns]
    if not g or "epi" not in d.columns:
        d.to_csv(tdir / f"{name}.csv", index=False)
        return
    t = (d.groupby(g).agg(epi_mean=("epi", "mean"), epi_std=("epi", "std"),
                          epi_median=("epi", "median"),
                          viol_mean=("violation_steps_total", "mean"), n=("epi", "size"))
         .reset_index())
    t.to_csv(tdir / f"{name}.csv", index=False)


def table_ladder(d: pd.DataFrame, tdir: Path, claims: list) -> None:
    if d is None or not len(d):
        return
    cols = [c for c in ("condition", "variant", "degree", "optimizer", "denoise", "nonzero",
                        "one_step_rmse_t_in", "rollout_rmse_t_in", "diverged_frac",
                        "sign_pass", "embeddable", "kappa") if c in d.columns]
    agg = {c: "mean" for c in cols if d[c].dtype.kind in "fi"}
    t = d.groupby("condition").agg({**agg, **({"embeddable": "min"} if "embeddable" in d else {})})
    t = t.reset_index().sort_values("rollout_rmse_t_in" if "rollout_rmse_t_in" in t else "condition")
    t.to_csv(tdir / "ladder.csv", index=False)
    frozen = (f"{C.CONFIRMATORY['feature_variant']}/d{C.CONFIRMATORY['library_degree']}"
              f"/{C.CONFIRMATORY['optimizer']}/{C.CONFIRMATORY['denoise']}")
    passing = t
    if "embeddable" in t:
        passing = passing[passing.embeddable.astype(bool)]
    if "diverged_frac" in passing:
        passing = passing[passing.diverged_frac.fillna(1.0) <= 0.05]
    claims.append(("Configurations evaluated / passing the open-loop gates",
                   f"{len(t)} evaluated, {len(passing)} pass; frozen recipe {frozen} "
                   f"{'IS' if frozen in set(passing.condition) else 'is NOT'} among them",
                   "tables/ladder.csv"))


# ── driver ───────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    out = Path(a.out) if a.out else (HERE / "results")
    tdir = out / "tables"
    tdir.mkdir(parents=True, exist_ok=True)

    def load(name):
        p = out / f"{name}.csv"
        return pd.read_csv(p) if p.exists() else None

    claims: list = []
    main_d = load("main")
    if main_d is not None:
        table_main(main_d, tdir, claims)
        table_prices(main_d, tdir, claims)
        if "truncated" in main_d.columns:
            n_tr = int(main_d.truncated.astype(bool).sum())
            claims.append(("Truncated seasons excluded", f"{n_tr} of {len(main_d)}",
                           "main.csv (column `truncated`)"))
    table_mechanism(load("mechanism"), tdir, claims)
    table_ladder(load("ladder"), tdir, claims)
    for nm in ("parity", "adapt", "guard", "faults", "design"):
        table_simple(load(nm), nm, tdir, claims)

    man = out / "regen_manifest.json"
    meta = json.loads(man.read_text(encoding="utf-8")) if man.exists() else {}
    lines = ["# NUMBERS — every stated result and where it comes from", "",
             f"- config_hash: `{meta.get('config_hash', C.config_hash())}`",
             f"- git_sha: `{meta.get('git_sha', C.git_sha())}`",
             f"- env_hash: `{(meta.get('env') or {}).get('env_hash', 'n/a')}`", "",
             "| Claim | Value | Source |", "|---|---|---|"]
    for claim, value, src in claims:
        lines.append(f"| {claim} | {value} | `{src}` |")
    lines += ["", "Regenerate with:", "",
              "```bash", "python run_regen.py --merge --out <out> && python make_tables.py --out <out>",
              "```", ""]
    (out / "NUMBERS.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote {len(list(tdir.glob('*.csv')))} tables -> {tdir}")
    print(f"wrote {out / 'NUMBERS.md'} ({len(claims)} claims)")
    for c, v, s in claims:
        print(f"  - {c}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
