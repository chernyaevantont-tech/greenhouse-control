# Paper tables (assembled from the fresh 20-seed regen)

Sources: `../results_scenarios/tables/e3_main_table.csv`, `e3_pareto_table.csv`,
`e3_stats_vs_rulebased.csv`, `e8_stats_*.csv`, `e3_lambda_sweep_table.csv`.

---

## T1 — Controllers as differential diagnosis (the cast is a set of controls, not a leaderboard)

| Controller | Class | Rival hypothesis it rules out | Answer from data |
|---|---|---|---|
| **Rule-based** | tuned heuristic | "Is there even a strong simple target?" (also the DAgger expert) | Yes — EPI 4.63, the bar to beat |
| **Grey-box MPC** | reduced first-principles | "Is the MPC solver / library itself weak?" | No — 3.79 works ⇒ **isolates the sparsity threshold as the cause**, not the MPC |
| **SINDy-MPC (confirmatory)** | proposed, pre-registered | the method under test | Fails: 1.18 (boiler dropped) |
| **SINDy-MPC (dense / +DAgger)** | proposed, repaired | "Can the defect be fixed without losing interpretability?" | Yes — restoring the boiler → 3.8–5.2, still glass-box |
| **Oracle (3 h CEM)** | MPC on the *true* model | "Would a more accurate model fix it?" | No — 1.99, over-spends ⇒ **fidelity is not the cure** |
| **NN-MPC** | black-box surrogate MPC | "Would a black-box surrogate win?" | No — −5.09, worse than the interpretable one |
| **PPO / SAC** | black-box RL | "Is interpretability the bottleneck — would black-box RL win?" | No — both below the heuristic ⇒ interpretability is not the cost |

Framing sentence for Results: *"We run this benchmark not to crown a winner but to
explain why the pre-registered interpretable controller underperforms and to rule
out the obvious alternatives (weak MPC, insufficient model fidelity, black-box
advantage). The controller set is an elimination structure, not a leaderboard."*

---

## T2 — E3 closed-loop economic benchmark (20 seeds; paper-ready, de-duplicated)

Sorted by EPI. ΔEPI and p_Holm are paired Wilcoxon vs Rule-based (Holm-corrected).
Frontier = non-dominated in (EPI ↑, violation-steps ↓).

| Controller | EPI (EUR/m²) | Viol. steps | scaled_pen† | T-corridor % | n | ΔEPI vs RB | p_Holm | Frontier |
|---|--:|--:|--:|--:|--:|--:|--:|:--:|
| SINDy-MPC (conf+DAgger) | **5.23 ± 2.40** | 4302 | 426 | 62 | 20 | +0.59 | 0.26 (ns) | ● |
| **Rule-based** | **4.63 ± 0.00** | 2458 | 485 | 95 | 20 | — | — | ● |
| SINDy-MPC (dense) | 3.81 ± 1.27 | 6073 | 1206 | 65 | 20 | −0.82 | 0.017 | |
| Grey-box MPC | 3.79 ± 1.27 | 6083 | 1209 | 65 | 20 | −0.85 | 0.017 | |
| PPO | 3.36 ± 1.59 | 1842 | 392 | 84 | 20 | −1.28 | 0.0013 | ● |
| SINDy-MPC (dense+DAgger) | 3.23 ± 2.21 | 4467 | 624 | 66 | 20 | −1.40 | 0.031 | |
| Oracle (3 h CEM)‡ | 1.99 ± 0.68 | 2816 | 379 | 72 | 20 | −2.65 | 2e-5 | |
| SINDy-MPC (confirmatory)§ | 1.18 ± 4.33 | 5357 | 793 | 50 | 20 | −3.46 | 0.0086 | |
| SAC¶ | −2.41 ± 1.24 | 1683 | 179 | 82 | 10 | −7.04 | 0.0098 | ● |
| NN-MPC | −5.09 ± 3.11 | 4368 | 767 | 70 | 20 | −9.72 | 2e-5 | |

Headline: **Rule-based and SINDy-MPC(conf+DAgger) are statistically tied at the top
(p=0.26); every other controller is significantly worse than Rule-based.**

† scaled_pen = Σ_c (violation area_c / max_violation_c), simulator's severity scale.
  Note conf+DAgger violates on more steps than Rule-based but with *lower* total
  severity (426 vs 485) — supports reporting both axes.
‡ Oracle is a greedy 3-h economic optimum over the true model; it is **not** an
  upper bound (over-spends — see §4.4 / horizon probe). Do not read as a ceiling.
§ Confirmatory = the pre-registered frozen recipe (physics_no_cross/ensemble) — the
  method actually under test; its failure is the paper's subject.
¶ SAC diverged (NaN) on 10/20 seeds despite VecNormalization; reported on the 10
  converged seeds. Base run's "sindy_mpc" row (≡ confirmatory) dropped as a duplicate.

---

## T3 — Hypothesis scorecard (pre-registered Г1–Г4, fresh 20-seed verdicts)

| Hypothesis | Verdict | Evidence (20 seeds) |
|---|---|---|
| **Central §1.4** — SINDy-MPC non-dominated / low price of interpretability | ❌ **Not confirmed** (Path A) | conf+DAgger ties rule-based (p=0.26); pre-registered confirmatory +1.18 sig. worse than all strong baselines |
| **Г1** — gap to oracle ≤ best black-box & grey-box | ❌ **Not met; framing broken** | Oracle 1.99 < rule-based/ppo/grey-box ⇒ not a ceiling; confirmatory (−3.56 vs RB) worse than grey-box (−0.85) and ppo (−1.28) |
| **Г2** — a recipe removes rollout divergence | ✅ **Met, but reveals the core** | rollout-RMSE stable 2.25–2.39; but open-loop stability is *necessary, not sufficient* — closed loop is the arbiter |
| **Г3** — transparency without quality loss | ⚠️ **Partial** | glass-box ✅; beats NN-MPC decisively ✅; but confirmatory < grey-box — parity only after the boiler fix (still interpretable) |
| **Г4a** — online adaptation recovers EPI | ❌ **Not supported (strengthened)** | DAgger vs offline +0.39, p=0.088 ns (60 pairs); EKF sig. worse (−2.17). Earlier "significant" was a small-sample (n=9) artefact |
| **Г4b** — OOD signal → guard cuts violations | ✅ **Supported — strongest positive** | Mahalanobis corr +0.63 (RMSE) / −0.50 (EPI); guard violations 1723→863 (−50%) *and* EPI improves; p≈1e-24 |
| **Г4c** — optimizer doesn't exploit surrogate error | ⚠️ **Partial** | confirmatory over-violates (5357 vs 2458) — MPC pushes into over-estimated regions; guard mitigates |

Additional (non-Г) findings to report: RL normalization flips PPO −13→+3.4
(reproducibility lesson); E6 EPI ranking dominated by prices (fruit 19.7 > energy
13.3 ≫ design choices) and not robust to energy price.
