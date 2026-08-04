<!-- DRAFT §4.3 — the core mechanism section. LaTeX-friendly (\citep{key}, \ref{}).
     Numbers from results_scenarios/tables/{e3_lambda_sweep_table,e3_main_table,
     e3_pareto_table}.csv and e3_stats_vs_rulebased.csv (fresh 20-seed regen). -->

## 4.3 The mechanism: sparsity hides the actuator

The pre-registered confirmatory recipe is economically the weakest of the
interpretable controllers: it returns an EPI of only
$1.18 \pm 4.33~\mathrm{EUR/m^2}$, against $4.63$ for the tuned rule-based baseline
and $3.79$ for the grey-box MPC that shares its solver and feature library
(Table~\ref{tab:e3main}; $p_\mathrm{Holm}=0.009$). Crucially, this recipe was
*not* selected for weak closed-loop control — it was frozen, before any
closed-loop evaluation, because it was the most parsimonious model that passed the
open-loop rollout-stability and transparency gates (§3.4). The recipe that our
pre-registration certified as identification-optimal is therefore the recipe that
fails in the loop. This section explains why.

### The sparsity threshold silently removes the boiler

We isolate the cause with a one-parameter ablation: holding the feature library
(`physics_no_cross`, degree~1) and the MPC fixed, we sweep the STLSQ sparsity
threshold $\lambda$ over $[10^{-6},\,10^{-1}]$ and, at each value and for each of
20 seeds, record (i) the number of surviving coefficients, (ii) the signed
coefficient of the boiler term in the temperature equation,
$\Xi_{u_\mathrm{Boil}\rightarrow T_\mathrm{in}}$ — the greenhouse's only modelled
active heating actuator, (iii) the *open-loop* rollout-RMSE of $T_\mathrm{in}$ on
the deployment season, and (iv) the *closed-loop* EPI and violations obtained when
the identified model is embedded in the MPC. Results are in
Fig.~\ref{fig:lambda} and Table~\ref{tab:lambda}.

Two curves move in opposite directions. As $\lambda$ increases from $10^{-6}$ to
$0.1$ the model becomes parsimonious as intended (surviving terms $54\rightarrow20$),
and the boiler coefficient decays and then vanishes:
$\Xi_{u_\mathrm{Boil}\rightarrow T_\mathrm{in}} = 0.036$ at $\lambda\le 0.03$,
$0.006$ at $\lambda=0.05$, and exactly $0$ at $\lambda=0.1$. Closed-loop EPI tracks
this collapse — from a peak of $4.67~\mathrm{EUR/m^2}$ at $\lambda=0.02$ down to
$0.99$ at $\lambda=0.05$, precisely where the boiler term is thresholded out.
Once the surrogate contains no heating actuator, the MPC can no longer plan
heating, and in a heating-dominated spring climate the economic loss is severe.

The open-loop metric, by contrast, is almost inert across the same sweep:
rollout-RMSE moves only from $2.25$ to $2.39$ — a $6\%$ change — while EPI swings
by a factor of five and the boiler term disappears entirely. The pre-registered
open-loop selection criterion is thus *blind to the closed-loop failure it causes*:
the model that minimises parsimony-penalised open-loop error is the one that
disables the control-critical actuator. This is a concrete, physically legible
instance of the objective mismatch between predictive accuracy and control
performance \citep{lambert2020objective, jacobiandmd2022}, and a modern,
sparse-identification realisation of the classical identification-for-control
principle that the closed loop, not open-loop fit, must arbitrate model quality
\citep{gevers1993, vandenhof1995closedloop}.

### Causal confirmation: restoring the boiler restores performance

If removal of the boiler term is the cause, then restoring it — by any means —
should recover economic performance. Two independent interventions do exactly
that (Table~\ref{tab:e3main}). Reducing the threshold to a dense recipe
(`stlsq`, $\lambda=10^{-3}$) keeps $\Xi_{u_\mathrm{Boil}\rightarrow T_\mathrm{in}}
\approx 0.034$ and lifts EPI from $1.18$ to $3.81$; iterative dataset aggregation
(DAgger) applied to the confirmatory recipe reintroduces the term through
closed-loop data and lifts EPI to $5.23$, statistically indistinguishable from the
rule-based baseline ($\Delta = +0.59$, $p_\mathrm{Holm}=0.26$). Across all
SINDy-MPC variants, closed-loop EPI is monotone in the presence of the boiler
coefficient: whenever $\Xi_{u_\mathrm{Boil}\rightarrow T_\mathrm{in}}\neq 0$, EPI
rises from $\approx 1$ to $4$–$5~\mathrm{EUR/m^2}$. The boiler coefficient is a
one-dimensional causal proxy for economic competence.

### Parsimony is not interpretability

The dense fix is not a black box: it is the same glass-box discrete map with
explicit, sign-checkable equations, only with more non-zero terms. Tellingly, the
repaired dense SINDy-MPC ($3.81$) coincides with the reduced first-principles
grey-box MPC ($3.79$) to within noise (Fig.~\ref{fig:pareto}): once
over-sparsification is removed, the data-driven interpretable surrogate collapses
onto the physical model it was meant to replace. What sparsity removed was
therefore neither predictive accuracy nor transparency, but the *controllability*
conferred by a single small-magnitude actuator term. Parsimony and
interpretability are distinct properties, and optimising the former can silently
destroy control performance while leaving the latter intact.

Two methodological consequences follow. First, `sparsity` should not appear among
the model-selection objectives when the downstream task is closed-loop control;
control-relevant selection \citep{farahmand2017value, cortiella2021sparse,
balanceguided2026} or a closed-loop-in-the-loop criterion is required. Second, a
transparency gate that certifies a model while a control-critical actuator has been
zeroed is incomplete: a dropped key actuator should itself constitute a gate
failure. We return to both points in §5.1.
