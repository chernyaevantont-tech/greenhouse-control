# Paper scaffold — "When sparsity hides the actuator"

Working title: **When sparsity hides the actuator: a pre-registered economic
benchmark of SINDy-MPC for greenhouse climate control**
Target: *Computers and Electronics in Agriculture* (Elsevier, elsarticle).
Spine: **benchmark as differential diagnosis** — the controller cast rules out
rival explanations for why the pre-registered interpretable method underperforms;
the λ-sweep (mechanism) is the money figure.

## Files
- `highlights.txt` — 5 CEA highlights (≤85 chars)
- `positioning.md` — Related-work differentiation (GreenLight-Gym, objective mismatch, I4C, STLSQ/Balance-Guided) + novelty statement
- `tables.md` — T1 (controllers → hypothesis eliminated), T2 (E3 main, paper-ready), T3 (hypothesis scorecard)
- full section-by-section outline: see chat / to be dropped as `outline.md`

## Blockers — status
1. ✅ **Annotated Pareto regenerated** from fresh 20-seed / 11-method table →
   `../results_scenarios/figures/e3_pareto_annotated.png` + `tables/e3_pareto_table.csv`.
   Frontier: SINDy-MPC(conf+DAgger), Rule-based, PPO, SAC (degenerate min-viol corner).
   Generator: `../e3_pareto.py`.
2. ✅ **GreenLight-Gym positioned** (van Laatum, van Henten, Boersma, IFAC 2025;
   arXiv 2410.05336): RL benchmark *environment* (differentiable C++, ×17 speed,
   2 RL algos) — NO tuned rule-based, NO SINDy, NO economic controller benchmark,
   NO open/closed-loop mismatch. We build an honest *economic controller* benchmark
   on that environment. See `positioning.md`.
3. ✅ **Duplicate + sac resolved**: drop base `sindy_mpc` (≡ `sindy_mpc_confirmatory`,
   same frozen recipe); report SAC at n=10 with a divergence footnote. Encoded in
   `e3_pareto.py` (DROP set) and `tables.md` (T2 + notes).
4. ✅ **T1 / T3 assembled** from the hypothesis analysis → `tables.md`.

## Draft status — FULL PROSE DRAFT COMPLETE (~5,930 words body)

Section files in `sections/` (assembly order):
1. `00_abstract.md` (366 w) — abstract + keywords
2. `01_introduction.md` (646 w)
3. `02_related_work.md` (421 w)
4. `03_methods.md` (905 w)
5. `04_results.md` (1135 w) — §4.1, §4.2, §4.4–§4.8  ← INSERT §4.3 after §4.2
6. `04-3_mechanism.md` (733 w) — §4.3 core mechanism
7. `05_discussion.md` (645 w)
8. `06_conclusions.md` (369 w) + reproducibility
Plus `outline.md`, `positioning.md`, `tables.md`, `highlights.txt`.

All numbers are from the fresh 20-seed regen. Citations use `../../articles/references.bib` keys.

## Remaining (polish / production)
- Assemble into one document; decide **Markdown vs LaTeX (elsarticle)**.
- Final numeric pass: verify every figure/inline value against source CSVs
  (e.g. λ=0.03 boiler coef is 0.032, rounded to ≈0.036 in §4.3 — tighten).
- Build Tables T1–T3 (in `tables.md`) into the document; add Fig captions.
- F1 pipeline schematic still to draw; F2/F3/F4/F6 exist, F5 (safety) to compose.
- Verify the 5 remaining ⚠ journal refs (see `../../articles/bibliography.md`).
