<!-- DRAFT — Abstract + Highlights. Numbers from the fresh 20-seed regen. -->

## Abstract

Interpretable data-driven surrogates such as sparse identification of nonlinear
dynamics (SINDy) are attractive for greenhouse model predictive control (MPC)
because they yield explicit, inspectable equations rather than black boxes.
Whether this interpretability comes at an economic cost, however, is rarely tested
under a fair protocol: baselines are often untuned, the metric is a tracking proxy
rather than profit, and — most subtly — the identification recipe is chosen by
open-loop prediction quality. We report a pre-registered, in-silico economic
benchmark of ten controllers on the GreenLight tomato simulator (Rostov-on-Don,
2018--2023 ERA5 weather), using the simulator's own economic performance indicator
(EPI, seasonal profit) as the primary metric and a two-axis Pareto criterion
(EPI versus constraint violations), over 20 seeds with paired non-parametric
statistics. The pre-registered SINDy-MPC recipe, frozen by open-loop metrics
before any closed-loop evaluation, is economically among the weakest interpretable
controllers ($1.18$ vs $4.63~\mathrm{EUR/m^2}$ for a tuned rule-based baseline). A
one-parameter ablation traces the cause: the sparsity threshold silently zeroes
the boiler term in the temperature equation — the only modelled heating actuator —
and closed-loop EPI collapses from $3.8$ to $1.0~\mathrm{EUR/m^2}$ while the
open-loop rollout error stays flat ($2.25\rightarrow2.39$). The open-loop selection
criterion is thus blind to the closed-loop failure it induces. Restoring the term,
by a denser threshold or by DAgger, recovers EPI to parity with the heuristic
without loss of interpretability, and the repaired model coincides with a
first-principles grey-box model. A controller cast designed as differential
diagnosis rules out the obvious alternatives: the true-model oracle over-spends and
is not a ceiling, a normalized PPO improves but does not win, and a black-box
NN-MPC is worst — so neither insufficient fidelity nor interpretability is the
bottleneck. The interpretable surrogate's demonstrable value lies instead in safety
and out-of-distribution guarding (a Mahalanobis guard cuts violations by 50\% while
improving EPI; a fault supervisor significantly mitigates six actuator/sensor
faults), not in economic supremacy. We conclude that parsimony is not
interpretability, that sparsity must be removed from model-selection objectives
when the downstream task is closed-loop control, and that open-loop-frozen
pre-registration can systematically certify a control-catastrophic model.

**Keywords:** greenhouse climate control; model predictive control; sparse
identification of nonlinear dynamics; interpretable machine learning;
identification for control; economic benchmarking
