# Positioning / novelty (for §1.5 + §2)

## The one-paragraph novelty statement (drop into Introduction §1.5)

The observation that open-loop prediction accuracy is a poor proxy for closed-loop
control performance is not new: it is the premise of *identification for control*
(Gevers; Van den Hof & Schrama) and was sharpened for learned dynamics as
**objective mismatch** by Lambert et al. (2020), who showed one-step likelihood is
not correlated with control performance and proposed reweighting dense
neural-network model training. Our contribution is not this general principle but a
**concrete, interpretable, and causally verified instance of it in an economic
control loop**: we identify the *specific physical term* a sparsity threshold
removes (the boiler actuator in the temperature equation), show that its
coefficient *causally tracks* seasonal profit, and demonstrate that a
pre-registered open-loop model-selection procedure — the standard guard against
circular inference — therefore *systematically selects a control-catastrophic
model*. Because the surrogate is a glass-box, the failure is legible term-by-term
rather than diagnosed by re-weighting a black box.

## Differentiation table (for Related Work §2)

| Prior work | What it does | What it does NOT do (our gap) |
|---|---|---|
| **GreenLight-Gym** (van Laatum, van Henten, Boersma, IFAC 2025; arXiv 2410.05336) | RL *benchmark environment*: differentiable C++ GreenLight, ×17 speed, benchmarks 2 RL algorithms | No tuned rule-based baseline; no SINDy/interpretable surrogate; no honest economic *controller* comparison; no open/closed-loop mismatch analysis. **We build an economic controller benchmark on this environment.** |
| **RL vs MPC on greenhouse** (Morcego et al., CEA 2023) | Compares RL and MPC; finds RL higher production but worse economics | Not interpretable ID; no sparsity-mechanism; no pre-registration; no honest-baseline emphasis |
| **SINDy-MPC** (Kaiser, Kutz, Brunton, RSPA 2018); **SINDYc** (Brunton 2016) | Introduces sparse-ID surrogate inside MPC; low-data control | Tracking tasks, not economic greenhouse; no failure-mode analysis of thresholding |
| **Objective mismatch** (Lambert et al., L4DC 2020) | Open-loop likelihood ≠ control performance; reweight dense NN model | Abstract/black-box; no identified physical term; no economic loop; no pre-registration angle |
| **Balance-Guided SINDy** (2026); STLSQ sensitivity literature | Proposes optimizers preserving small-coefficient physical terms | Proposes a *cure* on ID benchmarks; does not *diagnose* the failure inside an economic MPC loop with a causal EPI link |
| **Identification for control** (Gevers 1993; Van den Hof & Schrama 1995) | Foundational: control-relevant ID, closed-loop is the arbiter | Classical linear framing; we give a modern sparse-ID, economic, pre-registered instance |

## How to phrase our four contributions against the above
1. **Honest economic benchmark** on a validated agronomic simulator (EPI verified
   term-for-term against the simulator reward) with a *tuned* rule-based baseline
   and equal HP budget — filling the gap left by GreenLight-Gym (environment only).
2. **Mechanism**: sparsity-induced actuator dropout, causally linked to EPI — a
   physical, legible instance of objective mismatch (vs Lambert's abstract/NN one).
3. **Pre-registration trap**: open-loop-frozen recipe selection systematically picks
   the control-catastrophic model — a methodological warning for SINDy-for-MPC.
4. **Re-definition of interpretability's value**: transparency + safety/OOD, not EPI
   supremacy; and *parsimony ≠ interpretability* (the dense fix is equally glass-box).

## Key citations to secure (verify DOIs before submission)
- Lambert, Amos, Yadan, Calandra. *Objective Mismatch in MBRL.* L4DC 2020.
- Kaiser, Kutz, Brunton. *SINDy-MPC in the low-data limit.* Proc. R. Soc. A, 2018.
- Brunton, Proctor, Kutz. *SINDYc.* IFAC 2016.
- van Laatum, van Henten, Boersma. *GreenLight-Gym.* IFAC 2025 (arXiv 2410.05336).
- Morcego et al. *RL vs MPC on greenhouse climate control.* Comput. Electron. Agric. 2023.
- Gevers, *Towards a joint design of identification and control*, 1993 (I4C anchor).
- Balance-Guided SINDy (arXiv 2604.18414) — nearest mechanism neighbour.
- Fasel et al. Ensemble-SINDy; Stevens-Haas / Rosafalco Kalman/EKF-SINDy (methods used).
