<!-- DRAFT §6 Conclusions + reproducibility -->

## 6. Conclusions

We set out to measure the price of interpretability for sparse-identification MPC in
greenhouse climate control, under a protocol designed to be honest: economic profit
from the simulator itself as the metric, a tuned rule-based baseline, fairly
normalised RL, an equal hyper-parameter budget, and a recipe frozen by
pre-registration. The pre-registered claim — that SINDy-MPC is Pareto-competitive at
a low price of interpretability — was not confirmed. But the benchmark's contribution
is the mechanism it exposed rather than the negative headline.

First, a tuned agronomic heuristic is a strong, hard-to-beat economic reference; the
only interpretable controller that matches it does so through a repair. Second, that
repair is necessitated by a specific, transferable failure: the STLSQ sparsity
threshold silently removes the control-critical boiler term, collapsing closed-loop
profit while leaving open-loop prediction error essentially unchanged — so an
open-loop, pre-registered selection procedure systematically certifies a
control-catastrophic model. Third, the controller cast, read as a differential
diagnosis, rules out the intuitive alternative explanations: the true-model oracle
over-spends and is no ceiling, a normalised PPO improves but does not win, and a
black-box NN-MPC is worst — neither insufficient fidelity nor interpretability is the
bottleneck. Fourth, the value of the transparent surrogate is real but lies elsewhere
than EPI: an OOD guard cuts violations by half while improving profit, and a fault
supervisor significantly mitigates six fault modes. Parsimony is not interpretability,
and sparsity does not belong among model-selection objectives when the downstream task
is closed-loop control.

Future work should pursue a genuine economic ceiling — a long-horizon or
terminal-value optimal controller that can, unlike a short receding-horizon oracle,
account for multi-day fruit dynamics — control-relevant recipe selection that is
immune to the sparsity trap, and, ultimately, sim-to-real validation.

## Reproducibility

All experiments are fully scripted and seed-controlled. We release the controller
implementations, the pre-registered frozen recipe, the distributed 20-seed runners
and mergers, and the analysis that produces every table and figure. EPI is read from
the simulator's reward model, and its per-step economics were verified term-for-term
against the oracle's objective. Weather data, splits, prices and corridors are fixed
in a single configuration file, and the identical frozen recipe is loaded by every
experiment through one source of truth.
