"""Regenerate E2 interpretability artifacts against the CONFIRMATORY frozen recipe.

Fixes the provenance desync flagged in the audit: sign-checks / coefficients /
equations in results_scenarios were left over from a different recipe than the one
now frozen. This refits SINDy with recipe_frozen.json on the E2 train collection and
rewrites, consistently:
    tables/e2_sign_checks.csv, tables/e2_coefficients.csv, tables/sindy_equations_text.csv
"""
from __future__ import annotations
import json, os, sys, warnings
warnings.filterwarnings("ignore")
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402
import protocol_config as P  # noqa: E402


def eq_text(coef: pd.DataFrame, state: str, thresh: float = 1e-9) -> str:
    t = coef[(coef.equation == state) & (coef.coefficient.abs() > thresh)].sort_values(
        "abs_coefficient", ascending=False)
    parts = [f"{r.coefficient:+.4g}*{r.term}" for r in t.itertuples()]
    return f"{state}_next_scaled = " + (" ".join(parts) if parts else "0")


def main() -> int:
    pc = P.DEFAULT.resolved(False)
    RES = U.results_dir()
    recipe = json.loads((RES / "recipe_frozen.json").read_text(encoding="utf-8"))["recipe"]
    print("CONFIRMATORY recipe:", recipe)

    train_sc = pc.train_scenarios()[0]
    train = U.collect_rule_based_dataset(
        pc.cfg_for(train_sc, seed=0), n_days=pc.n_days_train, prbs_scale=0.3)
    bundle = U.fit_sindy(train, period=float(pc.period),
                         metadata={"label": "confirmatory_e2"}, **recipe)

    coef = U.coefficient_table(bundle)
    sign = U.sign_check_table(bundle)
    eqs = pd.DataFrame([{"equation": s, "text": eq_text(coef, s)} for s in U.STATE_NAMES])

    coef.to_csv(RES / "tables" / "e2_coefficients.csv", index=False)
    sign.to_csv(RES / "tables" / "e2_sign_checks.csv", index=False)
    eqs.to_csv(RES / "tables" / "sindy_equations_text.csv", index=False)

    nz = int((coef.coefficient.abs() > 1e-12).sum())
    npass = int((sign.verdict == "consistent").sum())
    print(f"\nnonzero terms: {nz} | sign checks consistent: {npass}/{len(sign)}")
    print("\n--- sign checks ---")
    print(sign[["equation", "term", "expected_sign", "coefficient", "verdict"]].to_string(index=False))
    print("\n--- equations ---")
    for _, r in eqs.iterrows():
        print(r["text"][:160])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
