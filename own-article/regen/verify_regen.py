"""Acceptance gates for the regeneration. Run BEFORE any number reaches the paper.

Each gate below exists because its absence produced a real defect in the 2026-06/07 state
(see README "Defect register"). A BLOCKING failure means the run is not publishable; a
WARNING means a claim in the text has to change, not the data.

    python verify_regen.py --out /results          # or ./results

Exit code 0 = every blocking gate passed.
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

FAILURES: list[str] = []
WARNINGS: list[str] = []

# Smoke runs (2 seeds, --fast, truncated grids) cannot satisfy the coverage gates by
# construction. In smoke mode those are downgraded to warnings so the job's exit code still
# means what it should: "the plumbing works". Correctness gates stay blocking in both modes.
SMOKE = False
COVERAGE_GATES = {"G1 grid complete", "G7 lambda sweep resolves xi==0 region",
                  "G7 lambda dispersion reported", "G10 oracle horizon sweep",
                  # A partial smoke legitimately has fewer sweep seeds, and the k8s smoke
                  # Job chains verify with `&&` -- leaving this blocking would fail the Job
                  # and stop the documented run order before the real waves start.
                  "G10 sweep seed subset complete"}


def gate(name: str, ok: bool, detail: str, blocking: bool = True) -> None:
    if SMOKE and name in COVERAGE_GATES:
        blocking = False
        detail = f"{detail}  [coverage gate, not blocking in --smoke]"
    tag = "PASS" if ok else ("FAIL" if blocking else "WARN")
    print(f"[{tag}] {name}: {detail}")
    if not ok:
        (FAILURES if blocking else WARNINGS).append(f"{name}: {detail}")


def _load(out: Path, name: str) -> pd.DataFrame | None:
    p = out / f"{name}.csv"
    if not p.exists():
        gate(f"{name}.csv exists", False, f"missing {p}")
        return None
    return _with_stop_reason(pd.read_csv(p))


def _with_stop_reason(d: pd.DataFrame) -> pd.DataFrame:
    """Derive `stop_reason` for runs produced before run_regen.score() recorded it.

    The break fires on failure MAX+1 while the last written row still carries MAX, hence
    `>=`. Keeps the 2026-08-04 output analysable without recomputing 356 CPU-hours.
    """
    if "stop_reason" in d.columns or "truncated" not in d.columns:
        return d
    tr = d["truncated"].astype(bool)
    sf = d.get("solver_failures", pd.Series(0, index=d.index)).fillna(0)
    d = d.copy()
    d["stop_reason"] = np.where(~tr, "complete",
                                np.where(sf >= C.MAX_SOLVER_FAILURES,
                                         "solver_aborted", "env_terminated"))
    return d


def check_provenance(out: Path, frames: dict[str, pd.DataFrame]) -> None:
    """G0 -- one config, one lineage. The old tree had four headline tables from three runs."""
    mp = out / "regen_manifest.json"
    if not mp.exists():
        gate("G0 manifest", False, f"missing {mp}")
        return
    man = json.loads(mp.read_text(encoding="utf-8"))
    cur = C.config_hash()
    gate("G0 manifest matches current config", man.get("config_hash") == cur,
         f"manifest={man.get('config_hash')} current={cur}")
    for name, d in frames.items():
        if d is None or "config_hash" not in d:
            gate(f"G0 {name} stamped", False, "no config_hash column")
            continue
        uniq = sorted(d.config_hash.dropna().unique())
        gate(f"G0 {name} single config", len(uniq) == 1 and uniq[0] == cur,
             f"{len(uniq)} distinct hash(es): {uniq[:3]}")


def check_main(d: pd.DataFrame) -> None:
    if d is None:
        return
    keys = ["method", "test_year", "seed"]

    # G1 completeness -- the old multiseason grid was complete; the single-season one was
    # not (SAC n=10, oracle/nn missing from the 20-seed table).
    dup = int(d.duplicated(keys).sum())
    gate("G1 no duplicate (method,year,seed)", dup == 0, f"{dup} duplicates")
    have = set(map(tuple, d[keys].values))
    want = {(m, y, s) for m in C.ALL_CONTROLLERS for y in C.TEST_YEARS for s in C.SEEDS}
    missing = want - have
    gate("G1 grid complete", not missing,
         f"{len(have)}/{len(want)} cells; missing e.g. {sorted(missing)[:4]}")

    # G2 truncation -- an aborted season forgoes revenue AND cost, so its EPI is measured on
    # a different horizon. Previously silent: oracle truncated 40/80, nn_mpc 34/80.
    # G2 short seasons. Only a SOLVER ABORT is disqualifying: the controller never produced
    # an action, so the season says nothing about its economics. A simulator-terminated
    # season is an outcome -- the controller drove the greenhouse somewhere GreenLight will
    # not continue from, and the grower loses the rest of the year. Blocking on those would
    # have thrown away 31 of nn_mpc's 80 seasons and flattered exactly the controller that
    # wrecks the house, which is the survivorship bias this paper criticises elsewhere.
    if "stop_reason" in d.columns:
        ab = d[d.stop_reason == "solver_aborted"]
        env = d[d.stop_reason == "env_terminated"]
        gate("G2 no solver aborts", len(ab) == 0,
             f"{len(ab)} solver aborts {ab.groupby('method').size().to_dict() if len(ab) else {}}")
        gate("G2 simulator-terminated seasons (kept, reported)", True,
             f"{len(env)} kept as outcomes "
             f"{env.groupby('method').size().to_dict() if len(env) else {}}", blocking=False)
    elif "truncated" in d.columns:
        gate("G2 stop_reason recorded", False,
             "no `stop_reason` column -- rerun with the current run_regen.score()")
    else:
        gate("G2 truncation recorded", False, "no `truncated` column")

    # G3 one horizon, one solver budget for everyone (D4/D5).
    for col in ("horizon", "max_solver_failures"):
        if col in d:
            u = sorted(d[col].dropna().unique())
            gate(f"G3 uniform {col}", len(u) == 1, f"values={u}")

    # G4 the boiler coefficient must be recorded for every surrogate controller, since the
    # paper's mechanism is stated in terms of it.
    sind = d[d.method.astype(str).str.startswith("sindy_")]
    if len(sind):
        miss = int(sind.xi_uboil.isna().sum()) if "xi_uboil" in sind else len(sind)
        gate("G4 xi_uboil recorded for SINDy rows", miss == 0, f"{miss} NaN")

    # G5 the rule-based reference is deterministic on a fixed season, so a "paired
    # Wilcoxon by seed" against it is a ONE-SAMPLE test. Not a data defect -- a wording one.
    rb = d[d.method == "rule_based"]
    if len(rb):
        stds = rb.groupby("test_year").epi.std().fillna(0.0)
        zero = bool((stds.abs() < 1e-12).all())
        gate("G5 rule_based variance", not zero,
             "rule_based EPI std == 0 in every year -> the vs-baseline test is one-sample, "
             "not paired; the Methods wording must say so", blocking=False)

    # G6 the single-season ranking must not be reported as if it were the finding.
    if "test_year" in d.columns and d.test_year.nunique() > 1:
        valid = d[~d["truncated"].astype(bool)] if "truncated" in d.columns else d
        piv = valid.groupby(["test_year", "method"]).epi.mean().reset_index()
        win = piv.loc[piv.groupby("test_year").epi.idxmax()][["test_year", "method"]]
        winners = dict(zip(win.test_year, win.method))
        gate("G6 ranking stable across years",
             len(set(winners.values())) == 1,
             f"per-year winners: {winners}", blocking=False)


def check_mechanism(d: pd.DataFrame) -> None:
    if d is None:
        return
    lam = d[d.block == "lambda"] if "block" in d else d.iloc[0:0]
    knock = d[d.block == "knock"] if "block" in d else d.iloc[0:0]
    cross = d[d.block == "cross"] if "block" in d else d.iloc[0:0]

    # G7 the sweep must resolve the region where the coefficient is already exactly zero.
    # The 2026-07 grid ENDED at the first such point (lam=0.1) and EPI there was HIGHER than
    # at lam=0.05, which contradicts the monotonicity the text asserts.
    if len(lam):
        zero = lam[lam.xi_uboil.abs() < 1e-12]
        gate("G7 lambda sweep resolves xi==0 region", zero.lam.nunique() >= 2,
             f"{zero.lam.nunique()} grid point(s) with xi_uboil==0")
        g = lam.groupby("lam").epi.agg(["mean", "std", "size"]).reset_index()
        gate("G7 lambda dispersion reported", g["std"].notna().all(),
             "per-lambda std present (the paper's table omitted it)")
        if len(zero) and len(lam[lam.xi_uboil.abs() > 1e-12]):
            e0 = zero.epi.mean()
            worst = lam[lam.xi_uboil.abs() > 1e-12].epi.min()
            gate("G7 EPI monotone in boiler presence", e0 <= worst,
                 f"mean EPI with xi==0 is {e0:.2f}; worst EPI with xi!=0 is {worst:.2f} "
                 "-> 'EPI is monotone in the presence of the boiler coefficient' is false "
                 "as written and must be replaced by the knock-in result", blocking=False)

    # G8 the causal claim rests on the single-coefficient intervention, not the sweep.
    if len(knock):
        per = knock.groupby("seed").condition.nunique()
        gate("G8 knock block complete", bool((per >= 3).all()),
             f"{int((per < 3).sum())} seed(s) missing a condition")
        piv = knock.pivot_table(index="seed", columns="condition", values="epi")
        if {"baseline", "knockin"} <= set(piv.columns):
            eff = (piv["knockin"] - piv["baseline"]).dropna()
            gate("G8 knock-in effect", len(eff) > 0,
                 f"mean {eff.mean():+.3f} EUR/m2, improved {int((eff > 0).sum())}/{len(eff)} seeds")

    # G9 the cross term is not a nuisance: the 2026-07 run showed removing uBoil alone was
    # WORSE than removing uBoil and t_in*uBoil together.
    if len(cross):
        piv = cross.pivot_table(index="seed", columns="condition", values="epi")
        if {"ko_uboil", "ko_both"} <= set(piv.columns):
            d2 = (piv["ko_both"] - piv["ko_uboil"]).dropna()
            gate("G9 uBoil/cross interaction", len(d2) > 0,
                 f"ko_both - ko_uboil = {d2.mean():+.3f} "
                 f"(positive in {int((d2 > 0).sum())}/{len(d2)} seeds -> the heating pathway "
                 "is not one-dimensional)", blocking=False)


def check_parity(d: pd.DataFrame) -> None:
    if d is None:
        return
    hz = d[d.block == "horizon"] if "block" in d else d.iloc[0:0]
    if len(hz):
        u = sorted(hz.oracle_horizon.dropna().unique()) if "oracle_horizon" in hz else []
        gate("G10 oracle horizon sweep", len(u) >= 3, f"horizons={u}")
        if "seed" in hz.columns:
            got = set(hz.seed.unique())
            want = set(C.ORACLE_SWEEP_SEEDS)
            gate("G10 sweep seed subset complete", want <= got,
                 f"{len(got & want)}/{len(want)} of the declared sweep seeds present")
        if C.HORIZON in u:
            gate("G10 oracle at surrogate horizon", True,
                 f"oracle evaluated at h={C.HORIZON} (parity with the surrogate MPC)")
        else:
            gate("G10 oracle at surrogate horizon", False,
                 f"h={C.HORIZON} absent -> fidelity and horizon stay confounded")
        # Same distinction as G2: a solver abort disqualifies the run, a simulator
        # termination is a result about the oracle's own behaviour.
        if "stop_reason" in hz.columns:
            ab = int((hz.stop_reason == "solver_aborted").sum())
            gate("G10 oracle: no solver aborts", ab == 0, f"{ab} solver-aborted oracle runs")
        elif "truncated" in hz.columns:
            t = int(hz.truncated.astype(bool).sum())
            gate("G10 oracle seasons complete", t == 0,
                 f"{t} truncated oracle runs (cause unknown: no `stop_reason`)")


def main() -> int:
    global SMOKE
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--smoke", action="store_true",
                    help="plumbing check: coverage gates warn instead of blocking")
    args = ap.parse_args()
    SMOKE = bool(args.smoke)
    out = Path(args.out) if args.out else (HERE / "results")
    print(f"verifying {out}{'  [SMOKE]' if SMOKE else ''}\n"
          f"config_hash={C.config_hash()} git={C.git_sha()}\n")

    frames = {k: _load(out, k) for k in ("main", "mechanism", "parity")}
    check_provenance(out, frames)
    check_main(frames["main"])
    check_mechanism(frames["mechanism"])
    check_parity(frames["parity"])

    print()
    if WARNINGS:
        print(f"{len(WARNINGS)} warning(s) -- these change what the TEXT may claim:")
        for w in WARNINGS:
            print(f"  - {w}")
    if FAILURES:
        print(f"\n{len(FAILURES)} BLOCKING failure(s) -- do not publish these numbers:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all blocking gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
