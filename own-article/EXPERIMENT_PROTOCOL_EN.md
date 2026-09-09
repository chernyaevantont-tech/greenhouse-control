# Experiment protocol

**Subject.** Data-efficient interpretable predictive control of a greenhouse climate
built on sparse identification of nonlinear dynamics (SINDy), with an identification
procedure aimed at long-horizon prediction and with safe online adaptation.

**Simulator.** `gl_gym/GreenLightTomato-v0` (GreenLight-Gym). Every claim is in silico
and does not transfer to a physical greenhouse without separate validation.

**About this document.** This is an English translation of the experiment protocol for
the study. It records the plan together with the status notes that were written while the
earlier experiment campaign was running, so it also documents what became of each part of
the plan.

File and directory names refer to the working tree in which the plan was drafted. The
waves reported in the manuscript were produced later by the driver in `regen/`, and the
tables under `regen/results/` supersede the `results_scenarios/` paths named below. The
numbers quoted inside the status notes come from that earlier campaign and are superseded
in the same way. `regen/results/final/NUMBERS.md` maps every published quantity to the
file and column it is computed from.

---

## 0. Status and central claim (Path A)

**Status of the central hypothesis (§1.4): not supported by E3.** SINDy-MPC does not hold
a non-dominated competitive position on EPI. A tuned rule-based heuristic and a fairly
implemented PPO match it or do better. The work is therefore framed as **Path A**, an
honest in silico economic benchmark whose contribution is a negative result on
superiority together with interpretability, safety and adaptation, rather than as a
method-wins paper. Sections 1.4 and 1.5 are kept as the pre-specified plan; their outcome
is recorded in this section and in §6.3.

**The four messages of the paper (Path A):**

1. **A simple heuristic is a strong reference and hard to beat.** The tuned rule-based
   controller is Pareto-strong, reaching high EPI at the lowest violation count among the
   methods that do well on EPI.
2. **Fairness of the RL baselines decides the comparison.** Observation normalisation
   (VecNormalize) moves PPO from EPI −13 to +3.8; the naive implementation produced a
   falsely weak RL baseline. This is a reproducibility lesson rather than a property
   of RL.
3. **Sparse identification for MPC has a concrete and generalisable failure mode.**
   Selection on coefficient magnitude together with a threshold silently deletes an
   actuator term that is small in magnitude but critical for control (the boiler `uBoil`
   in the temperature equation), and closed-loop control then fails. A denser recipe or
   DAgger repairs it with no loss of interpretability, since the model stays explicit.
   This is the methodological contribution.
4. **The value of SINDy-MPC lies in transparency together with safety,
   out-of-distribution behaviour and adaptation** (E4/E5/E7), not in an EPI advantage.

**The comparison criterion has two axes (Pareto) and is not scalar EPI.** EPI = Σ profit
carries **no penalty for constraint violations**: the simulator's reward subtracts
*scaled* penalties, while EPI keeps the profit term alone. A method can therefore win on
EPI while spending more time outside the CO₂/T/RH corridor. The primary conclusion of E3
is stated through **Pareto dominance in (EPI × violations)**; see
`results_scenarios/figures/e3_pareto_annotated.png` and `tables/e3_pareto_table.csv`. The
secondary, dimensionally consistent scalar for violation severity is `scaled_penalty`,
the violation area divided by `max_violation`, as in the simulator's reward. A single
EUR-penalised EPI is **not** introduced, because violations carry no monetary value in
the simulator and any price for them would be invented.

**Interpretability and sparsity are different properties.** Interpretability of the
method means an explicit derived mathematical model: a glass-box with explicit equations
`x_{k+1} = Ξ·Θ(x,u)`, checkable signs and analytic embedding in the MPC. Sparsity, in the
sense of few active terms, is parsimony and stands apart from it. A dense model that
keeps the boiler term is just as interpretable. The failure described in message 3 is an
error in a selection hyperparameter (`sparsity` among the E2 Pareto criteria) rather than
a price paid for interpretability.

---

## Terms used

| Term | Meaning as used here |
|---|---|
| MPC (model predictive control) | at each step a finite-horizon optimisation is solved against a model of the plant |
| RL (reinforcement learning) | the policy is learned from interaction with the environment through a reward signal |
| SINDy (sparse identification of nonlinear dynamics) | recovery of the equations of motion as a sparse combination of library functions |
| SINDy-LOM (library optimization mechanism) | automatic selection of library functions with long-horizon prediction as the target |
| surrogate model | a computationally cheap stand-in for an expensive simulation model |
| EPI (economic performance indicator) | revenue from fruit growth minus the cost of resources; the seasonal margin |
| setpoint | the target value of a controlled variable |
| rollout (multi-step) | successive open-loop prediction over many steps without feedback |
| one-step prediction | prediction one step ahead |
| baseline | the method against which the proposed one is assessed |
| oracle | a controller built on the true model, the upper bound attainable in this setting |
| black-box / grey-box / glass-box | opaque / semi-empirical / fully interpretable model |
| Pareto front | the set of non-dominated trade-off solutions |
| gate | an admission criterion; a candidate that fails it does not enter the comparison |
| sparsity | the fraction of zero coefficients in the model |
| condition number (κ) | sensitivity of the regression to perturbations of the data |
| STLSQ (sequentially thresholded least squares) | the baseline sparse estimator of SINDy |
| SR3 (sparse relaxed regularized regression) | a variable-splitting estimator |
| Ensemble-SINDy | a bootstrap ensemble of models, giving a distribution over coefficients |
| Kalman smoothing | estimation of a signal and its derivative under a noise model |
| EKF (extended Kalman filter) | the nonlinear generalisation of the Kalman filter, used here for online assimilation |
| DAgger (dataset aggregation) | iterative retraining on trajectories of the current policy against an expert |
| OOD (out-of-distribution) | a regime not covered by the training data |
| Mahalanobis distance | distance of a point from a distribution, accounting for covariance |
| PPO (proximal policy optimization) | an on-policy RL algorithm |
| SAC (soft actor-critic) | an off-policy RL algorithm with entropy maximisation |
| NN-MPC | predictive control with a neural-network surrogate |
| PRBS (pseudo-random binary sequence) | an excitation signal used for identification |
| excitation | a control input that raises identifiability |
| bootstrap | resampling with replacement, used for spread and confidence intervals |
| effect size | the magnitude of a difference, independent of sample size |
| Wilcoxon signed-rank test | a non-parametric paired test |
| pre-specification | fixing the decisions before the test results are seen |
| MPC-embeddability | whether the model can be placed in the solver at acceptable cost |
| in silico | obtained on a model rather than on a physical plant |
| data efficiency | the performance reached per unit of data spent |

---

## 1. Aim and hypothesis

### 1.1 Scope and a single protocol

All comparisons are made within the **compared set of controllers** under one protocol:
the same weather scenarios, horizons and constraints; an **equal hyperparameter tuning
budget**, meaning the same number of trials and the same search method; the same rules
for data collection and one **currency for the cost of data**, namely the number of
simulator calls and the number of observed greenhouse-days. Data efficiency is a
**curve** of performance against budget rather than a single ratio.

### 1.2 References and controller classes

| Class | Instances | Role |
|---|---|---|
| Model-based, exact model | **oracle MPC** (MPC on the simulator's own model) | upper reference, the optimum *relative to the simulator*, with a sensitivity analysis over horizon, solver and model fidelity |
| Grey-box (reduced physics) | MPC on a simplified first-principles model | physically interpretable comparator |
| Data-driven, black-box | **PPO**, **SAC**, data-efficient RL (offline or model-based), **NN-MPC** | the main competitors |
| Heuristic | rule-based (agronomic rules) | lower reference |
| **Proposed method** | **SINDy-MPC** (interpretable sparse surrogate) | the subject of the study |

### 1.3 Criterion space (Pareto front)

The front is sought in **four measurable axes**: EPI; data budget; the number and area of
constraint violations; and adaptivity, understood as the EPI recovered under a shift in
weather.

**Interpretability enters as a qualifying gate rather than as an axis.** A controller counts as
transparent if it is a glass-box with explicit equations, passes the physical and
dimensional consistency checks above a threshold, and is structurally stable under
bootstrap. The **price of interpretability** is measured separately as the gap between
the Pareto front of the subset that passes the gate and the unconditional front.

### 1.4 Central hypothesis

> **Status after E3: not supported, see §0.** It is reproduced here as the pre-specified
> plan. On EPI, SINDy-MPC does not give the smallest gap; the rule-based controller and
> PPO are competitive or stronger. The study was reframed as Path A (§0).

Under the conditions of §1.1 the proposed method holds a non-dominated trade-off position
in the four-dimensional space of §1.3: it narrows the gap to oracle MPC at least as well
as the strongest black-box data-driven controller and as the grey-box comparator, at an
equal or smaller data budget, while passing the transparency gate and tuning itself to
the plant from data. In other words, the **price of interpretability is small**. This
holds only if H2 to H4 hold.

### 1.4.1 What "the proposed method" is, and pre-specification of the recipe

**The proposed method** is a closed-loop model predictive controller whose internal
prediction model is an **interpretable sparse surrogate of the greenhouse dynamics**
recovered from data (SINDy-MPC). The pipeline has four stages:

1. **Data collection** with a heuristic controller plus an excitation signal (PRBS or
   noise) on the weather of the region.
2. **Surrogate identification** by sparse regression, yielding **explicit discrete
   equations** `x_{k+1} = f(x_k, u_k, d_k)` with few non-zero terms that pass the
   transparency gate; polynomial degree 1 is used so that the map can be embedded
   analytically in the MPC.
3. **MPC**: the surrogate is placed in the solver (CasADi and do-mpc, through
   `build_mpc_controller` in `article_experiment_utils.py`) and optimises EPI subject to
   temperature, CO₂ and relative-humidity constraints over the horizon.
4. **Online adaptation** (for H4) by dataset aggregation (DAgger) or by an extended
   Kalman filter (EKF-SINDy), together with an out-of-distribution monitor and a safe
   fallback.

**Two levels of definition.** The hypothesis of §1.4 is stated about the
*architecture or family*, a sparse surrogate inside an MPC, which is fixed. The *specific
identification recipe* is not fixed in advance and is chosen in experiment E2: which
smoother (finite differences or Kalman), which estimator (STLSQ, ensemble, or one with
stability constraints), which feature library (physics-informed or SINDy-LOM).

**Pre-specification, against circular inference.** The recipe is frozen on
*identification and validation* metrics (multi-step rollout stability, MPC-embeddability
and transparency) **before** and **independently of** the closed-loop EPI on the held-out
test seasons. The choice of recipe in E2 therefore does not contaminate the fair
comparison in E3 (H1). The current prototype implementation is `fit_sindy` (STLSQ with
physics features, degree 1) together with `build_mpc_controller` in
`article_experiment_utils.py`; E2 generalises it into a robust recipe.

**One recipe across E3, E4 and E5.** Identification in every experiment goes through a
single source of truth, `protocol_config.load_frozen_recipe()`, which reads
`results_scenarios/recipe_frozen.json`. The confirmatory recipe is
`physics_no_cross / degree 1 / ensemble / no denoising`. `run_e4_shift.py` and
`run_e5_grid.py` previously hard-coded `stlsq/0.05` while `run_e3_seeds.py` used the
ensemble; that unintended divergence was removed and all three now call
`load_frozen_recipe()`. The exploratory variant `physics/stlsq/0.1`
(`recipe_exploratory.json`) is used only for post-hoc sensitivity.

**A documented defect of the confirmatory recipe, recorded as a finding rather than a
bug.** With `physics_no_cross` and a threshold near 0.05 the sparse regression **zeroes
the boiler term** `uBoil→t_in`: the temperature equation is then heated only through the
sun (`S_eff`), the thermal screen and negative ventilation, while the boiler migrates
into the humidity equation as `−0.087·uBoil`. In the heating-dominated Rostov spring this
removes the MPC's main heating actuator, and both the temperature correlation and EPI
fall (see `results_scenarios/tables/sindy_equations_text.csv` and `e2_sign_checks.csv`).
The cause is the `sparsity` term among the E2 Pareto selection criteria (§ E2,
"Criterion"): selection rewards parsimony and cuts a term that is small in magnitude yet
critical for control. A counter-experiment on 10 seeds shows that restoring the boiler,
either with a dense recipe at `stlsq/1e-3` or with **DAgger**, raises EPI from +0.82 to
between +3.8 and +6.0, and `uBoil→t_in ≠ 0` tracks EPI causally. The dense model is
**equally interpretable**, since the equations remain explicit; what is lost is parsimony
and not transparency. Artefacts of the counter-experiment are in
`results_scenarios/tables/e3_dagger_compare_*.csv`. The methodological conclusion is to
drop `sparsity` from the recipe-selection criteria, or to count a zeroed key actuator as
a failure of the transparency gate, which at present it is not: `transparency_gate`
excludes `missing_or_zero` from the denominator, which is a blind spot.

### 1.5 Sub-hypotheses

- **H1 (competitiveness under a limited data budget).** The gap to oracle MPC is no
  larger than that of the strongest black-box controller and of the grey-box comparator,
  at an equal or smaller data budget, and the price of interpretability is below the
  threshold. *Falsified if* some controller gives a significantly smaller gap at a
  comparable or smaller budget.
- **H2 (stability of long-horizon prediction, diagnostic).** There exists an
  identification recipe drawn from Kalman smoothing, SINDy-LOM and stability constraints,
  **whose minimal composition is determined by ablation**, that removes divergence of the
  multi-step open-loop rollout, driving the diverged fraction towards zero. Open-loop
  quality is necessary and not sufficient, since the arbiter is the closed loop (H1); a
  model enters the comparison only if it is embeddable in the MPC at acceptable cost.
  *Falsified if* no composition removes divergence, or if a stable open-loop model either
  fails to embed or fails to improve closed-loop EPI.
- **H3 (transparency without loss of performance).** The model is a glass-box, passes the
  physical and dimensional consistency checks, is structurally stable, and is not inferior
  in closed loop to NN-MPC or to the grey-box comparator. *Falsified if* the checks fail,
  the structure is unstable, or the closed-loop result is worse than either of those two.
- **H4 (safe adaptation under shift).** (a) Online adaptation, by DAgger or EKF-SINDy,
  recovers EPI under weather outside the training distribution; (b) the OOD signal,
  Mahalanobis distance or ensemble variance, predicts the growth of error and violations,
  so that the guard reduces violations; (c) the optimiser does not exploit surrogate
  error, and the trajectory stays predominantly in-distribution. *Falsified if* the OOD
  signal does not correlate with error, the guard does not help, or the optimiser
  systematically moves into regions where the surrogate over-predicts.

### 1.6 Null hypotheses

For each paired comparison, H₀ states that the distributions of the target metric (EPI,
violations, error) are indistinguishable. It is rejected by the Wilcoxon signed-rank test
at p < 0.05 with a correction for multiple comparisons, reported with the effect size and
bootstrap confidence intervals, over a sample of at least 10 independent runs.

---

## 2. Data and scenarios

- **Site.** Rostov-on-Don (47.24 N, 39.71 E). Real weather comes from ERA5 and ERA5-Land
  through Open-Meteo; the format and the derived quantities (sky and soil temperature) are
  described in `weather_data_methodology.md`, and the soil boundary condition is
  implemented in `rostov_soil.py`.
- **Years.** 2018 to 2023, with the CSV files under
  `gl_gym/data/weather/Rostov-on-Don/`.
- **Splits.**
  - *Train and in-distribution:* a subset of years (for example 2018 to 2020) and of
    start dates.
  - *Out-of-distribution:* the remaining years (2021 to 2023) and seasons whose weather
    differs, used in H4 and E5. Extreme episodes such as heat and cold waves are treated
    as explicit OOD cases.
- **Excitation for identification.** Rule-based control with added noise, which exists
  already, plus PRBS or multisine signals on the actuators for identifiability, with the
  condition number κ monitored.
- **Data budgets.** 1, 3, 7, 14, 30 and 60 days, giving the data-efficiency curve.
- `rostov_soil.apply_rostov_soil()` is called before the environment is created; weather
  is cached.

---

## 3. Metrics

| Category | Metrics |
|---|---|
| **Economics (primary)** | EPI [EUR/m²·season]; revenue; the cost of energy, CO₂ and lighting separately |
| Constraints | share of time inside the T/CO₂/RH corridor; number and area of violations |
| Resources | energy [kWh/m²], CO₂ [kg/m²] |
| Agronomy | fruit dry-matter growth (`yCFrt` from GreenLight) |
| Model quality | one-step R² and RMSE; rollout RMSE at horizons 4, 20 and 96; **diverged fraction**; sparsity; κ; noise robustness; ensemble variance |
| Transparency (gate) | glass-box, yes or no; share of sign and dimension checks passed; structural stability under bootstrap |
| Computation | identification time; MPC step time; number of simulator calls |

> **EPI and violations are decoupled and are compared in two axes.** EPI = Σ profit
> contains no penalty for violations (§0). The primary comparison in E3 is
> **Pareto (EPI × violations)**, and any one-dimensional statement that X beats Y on EPI
> is reported together with the violation count. The secondary severity scalar is
> `scaled_penalty`, the violation area divided by `max_violation`, as in the simulator's
> reward. A EUR-penalised EPI is not introduced, since violations carry no monetary value.

---

## 4. Experiments

> Template for each entry: **Aim · Hypotheses · Factors · Procedure · Criterion ·
> Artefacts.**

### E0. Canonical setting and metrics (foundation)

- **Aim:** move from setpoint error to EPI; fix the constraints, the real action units,
  the single currency for data and the equal hyperparameter budget.
- **Procedure:** implement EPI and the constraint penalty in `rollout_metrics()`; set
  `ymin` and `ymax` for T, CO₂ and RH.
- **Artefacts:** the metrics module; the protocol configuration covering scenarios,
  horizons, budgets and hyperparameters.

### E1. Data and scenarios (foundation)

- **Aim:** train, in-distribution and OOD splits over 2018 to 2023; excitation signals;
  the budget curve.
- **Procedure:** generate datasets with rule-based control plus noise, and optionally
  PRBS, at each data budget; fix the splits.
- **Artefacts:** `.npz` datasets; the table of splits; κ against budget.

### E2. Surrogate identification ladder (core)

- **Aim:** find an identification recipe that is stable in long-horizon prediction and
  usable inside an MPC.
- **Hypotheses:** H2, and H3 in part.
- **Factors (factorial ablation):**
  - denoising and derivative: finite difference, Savitzky–Golay, **Kalman smoothing**;
  - estimator: STLSQ, SR3, **Ensemble-SINDy**, and constrained or stability-constrained
    variants;
  - feature library: raw, physics-informed (hand-built), **SINDy-LOM** (automatic
    optimisation for long-horizon prediction);
  - polynomial degree: 1 (for the MPC) and 2 (an upper bound on open-loop quality).
- **Gates:** **MPC-embeddability**, so that a model enters E3 only if it embeds in CasADi
  and do-mpc at acceptable solver cost; and **transparency** (§1.3).
- **Criterion:** Pareto over rollout stability, noise robustness, MPC cost and
  closed-loop EPI, giving a recommended minimal recipe.
- **Artefacts:** the ablation table; a figure of rollout RMSE and diverged fraction
  against budget; the table of sign and dimension checks.

### E3. Closed-loop MPC benchmark (core)

- **Aim:** compare controllers on EPI and on constraint violations.
- **Hypotheses:** H1, H3.
- **Controllers:** rule-based, PPO, SAC, NN-MPC, **SINDy-MPC** (recipe from E2),
  grey-box MPC, oracle MPC.
- **Procedure:** closed-loop runs on the test seasons, equal hyperparameter budget, at
  least 10 runs.
- **Criterion (two axes):** primarily **Pareto (EPI × violations)** rather than scalar
  EPI (§0, §3). The gap to oracle MPC and the price of interpretability are secondary.
- **Artefacts:** the main table of mean ± CI; the **Pareto diagram**
  `e3_pareto_annotated.png` with `tables/e3_pareto_table.csv`, carrying the
  non-dominance flag and `scaled_penalty`.
- **Result (10 seeds, Path A, §0):** on the Pareto front are `rule_based` (balanced),
  `ppo` (few violations) and `sindy_mpc_conf_dagger` (highest EPI at the cost of
  violations); the cluster of `grey_box`, dense `sindy_mpc` and confirmatory `sindy_mpc`
  is **Pareto-dominated**. `sac` reaches the front only as the degenerate corner of
  minimum violations, at EPI below zero.
- **Ablation of the boiler term against controllability** (the methodological
  contribution of §0.3): a sweep over the sparsity threshold of `SINDy-MPC(λ)`
  (`figures/e3_lambda_sweep_ablation.png`, `tables/e3_lambda_sweep_table.csv`, 6 seeds)
  shows that `uBoil→t_in` drops out at λ ≈ 0.05 and closed-loop EPI collapses from +4 to
  −2.6 EUR/m², **while the open-loop rollout RMSE barely moves** (2.54 to 2.62). The
  pre-specified open-loop selection is therefore blind to a closed-loop failure, which is
  the central argument against `sparsity` as a selection criterion. The dense and DAgger
  counter-experiment is in `tables/e3_dagger_compare_*.csv`.

### E4. Online adaptation

- **Aim:** recovery of EPI under a shift in weather.
- **Hypotheses:** H4(a).
- **Factors:** offline, **DAgger** (`run_dagger` in `article_experiment_utils.py`) and
  **EKF-SINDy**.
- **Criterion:** the recovered EPI, the violation count, the cost of adaptation, and the
  **share of seasons completed**, meaning runs that reach the end without an integrator
  abort.
- **The ceiling, as fixed in `run_e4_shift.py`:** `retrained_ceiling` is trained on a
  budget equal to the offline one, namely twice `n_train` days of the shifted season,
  which makes it a genuine upper bound. It previously used N days and could fall below
  offline, which made `gap_recovered` invalid.
- **Choice of shift, with a diagnosis of integrator truncation.** The original shift to
  July 2021 is pathological. The over-sparsified frozen surrogate drives `t_in` to
  **62 °C**, the integrator returns NaN, and the run aborts at step 229 of 2880 offline
  and at step 28 of 2880 even for the ceiling; the hard summer season also breaks
  `rule_based`, which aborts at step 1680 of 2880 at RH 100 %. The diagnosis is in
  `scratchpad/diag_e4_*.py`. E4 is therefore run on **spring OOD shifts**, 1 March of
  2021, 2022 and 2023, comparing year against year within the same planting season, where
  both `rule_based` and the frozen surrogate complete the season with tmax between 34 and
  36 °C, so that full-season EPI and `gap_recovered` are valid. The dense,
  boiler-preserving recipe also completes July 2021 at tmax 43.5 °C, which makes the early
  abort of the frozen recipe a **safety finding**: over-sparsification is unsafe under
  shift. That finding is recorded separately through the completion share, and the recipe
  itself is left unchanged for consistency with E3.
- **Result (spring OOD, 20 seeds, `tables/e4_adaptation_springOOD.csv`):** completion is
  100 %, so truncation is removed. H4(a) is **not supported** in this setting: the offline
  model already generalises well at EPI near zero, ahead of `rule_based` at −2.9; the
  ceiling sits below offline, so there is no gap and `gap_recovered` is invalid; the EKF
  under its old default **does harm**; and DAgger gives a small gain.
- **EKF diagnosis (`tables/e4_ekf_tuning_diag.csv`, `scratchpad/diag_ekf.py`):** the old
  default `p0=10` produces **covariance windup** under the low excitation of the closed
  loop and destabilises the model, at EPI −4.3. The default was changed to `p0=0.1` with
  `forgetting=0.999`, which is stable at EPI +0.7. The finding for §0 is that recursive
  least squares steadily lowers the one-step residual **while the one-step fit does not
  track closed-loop EPI**: the most accurate variant gives the worst EPI, because control
  is decided by a discrete question about the actuator, namely whether `uBoil` has
  re-entered the model. This echoes the blindness of open-loop RMSE to closed-loop
  failure.
- **Diagnosis of the ceiling (`scratchpad/diag_ceiling.py`).** That the retrained ceiling
  is worse than offline is an artefact of **collecting data on the shifted season**, and not
  evidence against adaptation. On a hot shift (June 2022) `rule_based` with PRBS at 0.3
  breaks the integrator and collection stops at 3201 of 5760 rows, so the ceiling is
  trained on a fragment. Closed-loop confounding then adds to it: in summer the vents are
  open when it is hot, so corr(`uVent`, `t_in`) is +0.67 against +0.03 for the spring
  offline case, the learned cooling effect of ventilation is weakened by a factor of 2.6
  (−0.13 against −0.35), the MPC under-ventilates in heat and EPI falls to −14.3. The
  condition number is 73 against 20. On the mild spring the collection is complete and the
  models coincide structurally, so no gap exists. The conclusion is that a ceiling on
  adaptation runs into the safety and identifiability of on-shift data collection.
  **Probe with gentler excitation (`tables/e4_ceiling_confounding_probe.csv`):** lowering
  PRBS from 0.3 to 0.15 and 0.10 repairs the completeness of collection (5760 of 5760) and
  does not touch the confounding. corr(`uVent`, `t_in`) stays between +0.62 and +0.67 at
  every scale, because the correlation is created by the `rule_based` policy itself, with
  vents open when it is hot, rather than by the excitation; the `uVent` effect stays
  understated by a factor of three (−0.11 against −0.35) and every ceiling model is
  catastrophic, between −6 and −20 EPI. **E4 conclusion:** single-season summer
  closed-loop data are intrinsically confounded, and the correlation is broken only by
  diversity of conditions, as two spring years give corr +0.03. This is the precise
  mechanism by which the offline model generalises while a naive retrain does not. A
  ceiling from naive retraining is not attainable, and under shift the work is done by
  structure (the boiler term) and by the guard (E5) rather than by adaptation of
  coefficients.
- **Artefacts:** `tables/e4_adaptation_springOOD.csv`, `tables/e4_ekf_tuning_diag.csv`;
  adaptation curves against iteration.

### E5. Generalisation and OOD

- **Aim:** link input novelty to risk and test the guard.
- **Hypotheses:** H4(b, c).
- **Procedure:** a matrix of training on season A against testing on season B across years
  and dates; two confidence signals, **Mahalanobis distance** and ensemble variance;
  correlation of those signals with rollout RMSE and with violations; an ablation of the
  guard, with and without the OOD fallback; and a check that the closed-loop trajectory
  stays in-distribution.
- **Criterion:** a significant correlation between the OOD signal and error, and a
  reduction of violations with the guard.
- **Artefacts:** the generalisation matrix; a scatter of OOD signal against error; the ROC
  curve of the detector.

### E6. Sensitivity analysis

- **Aim:** robustness of the conclusions.
- **Factors:** energy and CO₂ prices; MPC horizon; cost weights; the STLSQ threshold;
  **parametric crop uncertainty of 0 to 30 %**; and the sensitivity of the oracle to
  horizon, solver and model fidelity.
- **Artefacts:** tornado or line plots of EPI sensitivity.

### E7. Fault injection and safety

- **Aim:** safety under sensor and actuator faults.
- **Hypotheses:** the safety part of H4.
- **Procedure:** a fault injector (stuck, offset, dead) applied to sensors and actuators,
  comparing the degradation of EPI and violations with and without the OOD supervisor.
- **Artefacts:** a table of degradation by fault type.

### E8. Statistical validity (validity of every hypothesis)

- **Aim:** valid inference.
- **Procedure:** vary the seed in the *collection of the training data* and refit the
  model for each seed, which is the real source of variance; at least 10 runs; bootstrap
  confidence intervals; effect sizes; and the Wilcoxon test with a correction for multiple
  comparisons. The notebook `07_multi_seed_benchmark.ipynb` is invalid on this point,
  because its per-seed models are identical.
- **Artefacts:** the significance table; boxplots across seeds.

---

## 5. Gates, as formal admission criteria

- **Transparency:** glass-box, and the share of sign and dimension checks passed above the
  threshold, and structural stability of the active-term set under bootstrap above the
  threshold.
- **MPC-embeddability:** the model embeds in the solver at an MPC step cost below budget;
  otherwise it is excluded from E3 whatever its open-loop quality.

---

## 6. Reproducibility and repository hygiene

- Pin the versions of numpy (< 2), scikit-learn (< 1.6), gymnasium (0.29), gl_gym, pysindy
  and do-mpc.
- Keep one canonical results directory, `results_scenarios/`, and delete the stale
  `results/`.
- Use one driver script with fixed seeds, and keep the data currency and the equal
  hyperparameter budget in the configuration.
- Call `apply_rostov_soil()` before creating the environment, with the weather CSV files
  copied into the gl_gym installation of the active virtual environment.
- Fix the hyperparameters of every controller and the search budget.

---

## 7. Mapping from experiment to hypothesis to paper artefact

| Exp. | Tests | Results section | Main artefact |
|---|---|---|---|
| E0/E1 | foundation | Experimental setup | configuration, splits, metrics |
| E2 | H2, part of H3 | 6.1 Identification ladder | rollout stability against budget; ablation |
| E2 | H3 | 6.2 Interpretability | equations with sign checks |
| E3 | H1, H3 | 6.3 Closed-loop EPI | main table of mean ± CI; Pareto diagram |
| E4 | H4(a) | 6.4 Online adaptation | DAgger against EKF-SINDy curves |
| E5 | H4(b, c) | 6.5 Generalisation and OOD | matrix; OOD against error; ROC |
| E6 | robustness | 6.6 Sensitivity | sensitivity plots |
| E7 | safety (H4) | 6.6 Fault robustness | degradation by fault type |
| E8 | validity of every hypothesis | all of Results | significance, confidence intervals |

---

## 8. Key literature

SINDy-MPC (Kaiser 2018); physics-informed and constrained variants (Champion 2020,
Loiseau 2018, trapping SINDy 2021); SINDy-LOM (Yonezawa 2025); Kalman-SINDy
(Stevens-Haas 2024, Rosafalco EKF-SINDy 2024); Ensemble-SINDy (Fasel 2022); DAgger
(Ross 2011, Espin 2024); greenhouse control and RL (van Laatum 2025 GreenLight-Gym,
Morcego 2023, Lin 2021, Chen and You).
