<!-- DRAFT §2 Related work -->

## 2. Related work

### 2.1 Greenhouse climate control

Optimal and predictive control of greenhouse climate has a long lineage, from
van Henten's optimal-control formulation of the coupled climate--crop system
\citep{vanhenten1994thesis, vanhenten2009timescale} to modern MPC implementations
\citep{lin2021greenhousempc, chenyou2020ddrmpc} and stochastic optimal control under
weather uncertainty \citep{vanmourik2023stochastic}. Reinforcement learning (RL) has
been explored as a model-free alternative and compared against MPC, with mixed
economic outcomes: RL can raise production but often at worse profitability
\citep{morcego2023rlvsmpc, mallick2024rlmpc, adaptiverobust2025greenhouse}. Our
simulator is GreenLight \citep{katzin2020greenlight, katzin2021led}, a validated
first-principles tomato model, wrapped by GreenLight-Gym
\citep{vanlaatum2025greenlightgym}. That benchmark, however, is an RL *environment*
— it provides a fast differentiable simulator and benchmarks RL algorithms — and
does not perform an honest economic *controller* comparison against a tuned
rule-based baseline, nor does it consider interpretable sparse-identification
surrogates or the open-loop/closed-loop selection question. Our study occupies that
gap.

### 2.2 Sparse identification and SINDy-MPC

SINDy recovers parsimonious governing equations by sparse regression over a
candidate library \citep{brunton2016sindy}, extends to actuated systems (SINDYc)
\citep{brunton2016sindyc}, and combines naturally with MPC in the low-data limit
\citep{kaiser2018sindympc}. Robustness has been improved by ensembling
\citep{fasel2022ensemble}, relaxed/constrained optimisation \citep{champion2020sr3},
and mature tooling \citep{desilva2020pysindy, kaptanoglu2022pysindy}. The
sequentially-thresholded least-squares (STLSQ) core is, however, known to be
sensitive to its sparsity threshold: too large a threshold removes physically
important small-coefficient terms, degrading the identified dynamics
\citep{cortiella2021sparse, mangan2017modelselection}, a problem that recent
optimisers explicitly target \citep{balanceguided2026}. Prior work treats this as
an *identification* pathology and proposes better *optimisers*; we instead
*diagnose* its consequence inside an economic MPC loop, with a causal link to
profit, and show that a standard open-loop selection protocol walks straight into it.

### 2.3 Identification for control and objective mismatch

That open-loop prediction accuracy is a poor proxy for closed-loop control is a
foundational message of identification-for-control: the loop, not the fit, must
arbitrate model quality, motivating control-relevant identification and closed-loop
experiment design \citep{gevers1993, hjalmarsson1994closing, vandenhof1995closedloop,
hjalmarsson2005experiment}. The same phenomenon was sharpened for learned dynamics
as *objective mismatch* — one-step likelihood is not correlated with control
performance \citep{lambert2020objective, wei2023unified} — with related remedies in
value-aware and control-oriented model learning \citep{farahmand2017value,
jacobiandmd2022, controlorientedsurvey2025}. Our contribution is neither the general
principle nor a new remedy, but a concrete, interpretable, and causally verified
instance of it: because our surrogate is a glass box, the failure is legible
term-by-term — a single removed actuator — rather than diagnosed by re-weighting a
black-box model. To restore the term we use dataset aggregation (DAgger)
\citep{ross2011dagger}, itself an established bridge between an MPC expert and a
learned model \citep{sun2017deeply, tagliabue2021guided, espin2024deepmpc}.
