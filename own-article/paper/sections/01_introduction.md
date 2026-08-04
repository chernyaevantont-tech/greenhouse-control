<!-- DRAFT §1 Introduction -->

## 1. Introduction

Greenhouse horticulture is an energy-intensive industry in which climate control
decisions translate directly into profit: heating, CO$_2$ enrichment and
supplemental lighting are the dominant variable costs, and they must be balanced
against the revenue from crop growth. Model predictive control (MPC) is a natural
fit, since it optimises a finite-horizon objective subject to the temperature,
humidity and CO$_2$ constraints that define a productive climate
\citep{vanhenten1994thesis, mayne2000constrained, lin2021greenhousempc}. MPC,
however, needs a model, and first-principles greenhouse models are laborious to
build and calibrate. This has motivated data-driven surrogates, and in particular
sparse identification of nonlinear dynamics (SINDy), which recovers explicit
governing equations as a sparse combination of candidate terms
\citep{brunton2016sindy, brunton2016sindyc, kaiser2018sindympc}. Unlike neural
surrogates, a SINDy model is a glass box: its equations can be read, sign-checked
against physics, and embedded analytically in an MPC solver. For a grower or a
certifying body, this interpretability is not a luxury but a practical requirement
for trust and debugging.

The central empirical question is whether interpretability costs performance —
whether an interpretable SINDy-MPC is Pareto-competitive with black-box
alternatives, or pays a measurable "price of interpretability". Answering it fairly
is harder than it appears, because the greenhouse-control literature and the
learned-control literature more broadly are prone to three benchmarking
pathologies. First, **untuned baselines**: learned controllers are frequently
compared against a weak rule-based straw man, whereas a well-tuned agronomic
heuristic is a strong competitor. Second, **proxy metrics**: setpoint-tracking
error is reported in place of economic profit, even though the two are not
monotonically related. Third, and most subtly, **open-loop model selection**: the
surrogate's hyper-parameters are chosen by open-loop prediction accuracy on a
validation set, on the tacit assumption that a more accurate model yields better
control. This last assumption is exactly what identification-for-control has warned
against for three decades \citep{gevers1993, vandenhof1995closedloop}, and what
objective mismatch has re-established for learned dynamics
\citep{lambert2020objective, jacobiandmd2022}.

We address all three by running a **pre-registered, in-silico economic benchmark**.
The primary metric is the simulator's own economic performance indicator (EPI) —
seasonal profit harvested directly from the reward model, not a proxy — and, because
EPI does not penalise constraint violations, the primary comparison is a two-axis
Pareto criterion (EPI versus violations). Baselines include a tuned rule-based
heuristic and fairly implemented reinforcement-learning controllers under an equal
hyper-parameter budget. The identification recipe is frozen by open-loop and
transparency criteria *before* any closed-loop evaluation, following pre-registration
practice \citep{pineau2021repro}, precisely so that recipe selection cannot
contaminate the honest comparison. We evaluate ten controllers over 20 seeds with
paired non-parametric statistics \citep{wilcoxon1945, holm1979, efron1994bootstrap}.

The pre-registered hypothesis — that SINDy-MPC is non-dominated with a low price of
interpretability — is **not** confirmed. But the value of the benchmark is not the
negative headline; it is the mechanism we uncover. The ten controllers function
as a differential diagnosis that isolates *why* the pre-registered interpretable
controller underperforms, and the answer is specific and transferable.

**Contributions.**
1. An **honest economic benchmark** on a validated agronomic simulator, with EPI
   verified term-for-term against the simulator's reward, a tuned rule-based
   baseline, an equal hyper-parameter budget, and 20-seed paired statistics —
   filling a gap left by RL-only greenhouse benchmarks \citep{vanlaatum2025greenlightgym}.
2. A **mechanism**: the STLSQ sparsity threshold silently removes the
   control-critical boiler actuator term, and closed-loop EPI causally tracks its
   presence while open-loop error does not — a physically legible instance of
   objective mismatch.
3. A **pre-registration trap**: an open-loop-frozen recipe-selection procedure, the
   standard guard against circular inference, systematically selects the
   control-catastrophic model.
4. A **re-definition of interpretability's value** for this problem: transparency
   plus safety and out-of-distribution guarding, not economic supremacy — and the
   observation that *parsimony is not interpretability*.

Section 2 places the work against SINDy, MPC, identification-for-control and
greenhouse control. Section 3 defines the metric, data, controllers, pre-registration
and statistics. Section 4 reports the benchmark and, at its core (§4.3), the
mechanism. Section 5 draws the methodological lessons and Section 6 concludes.
