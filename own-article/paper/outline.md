# Outline — full section tree

Title: **When sparsity hides the actuator: a pre-registered economic benchmark of
SINDy-MPC for greenhouse climate control.** Target: *Comput. Electron. Agric.*
Spine: benchmark as differential diagnosis; λ-sweep (§4.3) is the money figure.
Citations use `articles/references.bib` keys. Word budget ≈ 9–11k.

## Front matter
- Highlights → `highlights.txt`
- Abstract (≤250 w): context → gap (unfair benchmarks + open-loop selection) →
  what (pre-registered economic benchmark, EPI from simulator, 20 seeds, 11 ctrls) →
  key result (sparsity zeroes boiler; open-loop flat, closed-loop collapses; fix →
  parity) → diagnosis (fidelity/black-box/MPC not the cause) → value (safety/OOD).

## 1. Introduction  (~1.2k)
1.1 Economics + why interpretability is a practical requirement.
1.2 Gap: three benchmark pathologies — untuned baselines; proxy metrics;
    open-loop model selection. → motivates pre-registration + economics.
1.3 What we do (diagnostic benchmark; EPI term-for-term from simulator; 11 ctrls).
1.4 Contributions (4): economic benchmark; mechanism; pre-registration trap;
    re-definition of interpretability's value.
1.5 Positioning (novelty) → `positioning.md`: instance of objective mismatch
    [lambert2020objective] / I4C [gevers1993, vandenhof1995closedloop] with an
    identified physical term. Cite [jacobiandmd2022] (same open≠closed for DMD).

## 2. Related work  (~1.0k)
2.1 Greenhouse control (rule-based, MPC, RL): [vanhenten1994thesis,
    morcego2023rlvsmpc, vanlaatum2025greenlightgym, katzin2020greenlight].
2.2 SINDy / SINDy-MPC: [brunton2016sindy, brunton2016sindyc, kaiser2018sindympc,
    fasel2022ensemble, champion2020sr3, kaptanoglu2022pysindy]; STLSQ sensitivity
    [cortiella2021sparse, balanceguided2026, mangan2017modelselection].
2.3 Identification-for-control & objective mismatch [gevers1993,
    vandenhof1995closedloop, lambert2020objective, wei2023unified, farahmand2017value].

## 3. Methods  (~2.5k)
3.1 EPI (primary metric): Σ profit from GreenhouseReward; decomposition; two-axis
    criterion (EPI × violations); scaled_pen; verified vs simulator reward.
3.2 Simulator/location/data: GreenLight; Rostov 2018–23 (ERA5); splits; PRBS; κ.
3.3 Controllers (11) + equal HP budget; DAgger data-budget footnote. → Table T1.
3.4 Pipeline + pre-registration (frozen recipe; confirmatory vs exploratory).
3.5 Gates (transparency, MPC-embeddability).
3.6 Statistics: variance = per-seed train re-collection; 20 seeds; Wilcoxon+Holm+
    bootstrap+Cohen d [wilcoxon1945, holm1979, efron1994bootstrap, demsar2006].
3.7 Oracle definition (greedy 3-h economic CEM over true model; NOT a ceiling).

## 4. Results  (~3.5k)  — open with "benchmark = differential diagnosis" + T3 scorecard
4.1 Identification ladder (E2), brief; freeze confirmatory.
4.2 Closed-loop economic benchmark (E3): main table T2 + Pareto F3. Tie
    conf_dagger↔rule_based (p=0.26); all else sig. worse.
4.3 **The mechanism: sparsity hides the actuator** → `sections/04-3_mechanism.md`.
    λ-sweep (F2) + dagger_compare; causal uBoil↔EPI. CORE.
4.4 Ruling out fidelity: oracle 1.99 + horizon probe (over-spend). F4.
4.5 Ruling out interpretability cost: RL (VecNorm −13→+3.4) + NN-MPC.
4.6 Adaptation is a null (E4): DAgger +0.39 ns; EKF worse; confounding mechanism.
4.7 Where the model pays off: safety & OOD (E5 guard −50%; E7 supervisor). F5.
4.8 Robustness (E6): prices dominate; ranking not robust to energy price. F6.

## 5. Discussion  (~1.8k)
5.1 Don't select surrogates for MPC by open-loop; drop `sparsity` from criteria;
    zeroed key actuator ⇒ transparency-gate failure.
5.2 Parsimony ≠ interpretability (dense fix ≡ grey-box).
5.3 Why the heuristic is strong (multi-day fruit dynamics vs short horizon).
5.4 Generalization of the mechanism beyond greenhouses.
5.5 Limitations: single test season; in-silico; DAgger budget; CEM oracle; sac n=10.

## 6. Conclusions  (~0.4k)  + Reproducibility statement (code, seeds, frozen recipe).

## Figures / Tables → see `README.md` + `tables.md`
F2 λ-sweep (done), F3 Pareto (done), F4 oracle-horizon (done), F5 safety, F6 tornado;
T1 controllers→hypothesis, T2 E3 main, T3 scorecard.
