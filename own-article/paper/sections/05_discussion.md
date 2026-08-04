<!-- DRAFT §5 Discussion -->

## 5. Discussion

### 5.1 Do not select a control surrogate by open-loop metrics

The central lesson is procedural. Our pre-registration froze the identification
recipe by open-loop metrics precisely to avoid circular inference — and in doing so
selected the model that fails in the loop, because the open-loop metric it optimised
is blind to the closed-loop consequence (§4.3). This is not an argument against
pre-registration; it is an argument against pre-registering the *wrong* criterion.
Two concrete corrections follow. First, **sparsity should not be a model-selection
objective when the downstream task is closed-loop control**: a term with a small
coefficient can be dynamically negligible for prediction yet control-critical, as the
boiler term is here. Control-relevant or value-aware selection
\citep{farahmand2017value, jacobiandmd2022}, closed-loop-in-the-loop validation, or
optimisers that explicitly protect small important terms
\citep{balanceguided2026, cortiella2021sparse} are the appropriate remedies. Second,
**the transparency gate is incomplete**: a gate that certifies a model whose only
active heating actuator has been zeroed is not, in any useful sense, verifying
control-relevant transparency. A dropped key actuator — detectable by a sign/support
check against the known actuation structure — should itself constitute a gate
failure.

### 5.2 Parsimony is not interpretability

It is tempting to read our negative result as a "price of interpretability". It is
not. The repair that recovers economic performance — restoring the boiler term — does
not sacrifice transparency: the dense model is the same glass-box discrete map with
explicit, sign-checkable equations, only less parsimonious. Strikingly, the repaired
dense SINDy-MPC coincides with the reduced first-principles grey-box model to within
noise ($3.81$ vs $3.79~\mathrm{EUR/m^2}$): once over-sparsification is removed, the
data-driven interpretable surrogate collapses onto the physical model it was meant to
replace. What sparsity destroyed was neither accuracy nor interpretability but
*controllability*. Parsimony and interpretability are distinct properties, and
conflating them — optimising the former in the name of the latter — can silently
break control.

### 5.3 Why a tuned heuristic is hard to beat

The heuristic's strength, and the oracle's over-spend, share a root cause. Seasonal
profit is dominated by fruit growth accruing over days to weeks, whereas a receding
economic MPC with a several-hour horizon optimises near-term profit and greedily
trims heating and CO$_2$ that would have paid off later (§4.4). A well-tuned
agronomic rule set encodes, implicitly, the long-horizon trade-offs that a
short-horizon economic optimiser cannot see. This suggests that the productive route
to beating strong heuristics is not a better short-horizon surrogate but a genuinely
long-horizon economic formulation — a terminal value function on crop state, or a
gradient-based multi-day optimiser — which we identify as the key open problem.

### 5.4 Beyond greenhouses

The mechanism is not specific to horticulture. Any pipeline that (i) identifies a
sparse surrogate, (ii) selects its sparsity by prediction-oriented criteria, and
(iii) embeds it in a controller is exposed to the same failure: a small-coefficient
actuator or coupling term, negligible for open-loop error, can be thresholded out
and cripple closed-loop authority. The greenhouse simply makes the failure vivid and
legible, because the missing term is a named physical actuator whose coefficient we
can watch track profit.

### 5.5 Limitations

Our claims are in-silico and do not transfer to a physical greenhouse without
separate validation; the sim-to-real gap is out of scope here. The headline E3 result
uses a single test season (spring 2020), so the deterministic controllers have zero
test-weather variance and the reported variance reflects surrogate re-identification
only; the E5 generalisation matrix partially offsets this across seasons and years,
but a multi-season economic benchmark is needed to fully characterise variance. The
DAgger parity comes at an additional closed-loop data budget (three aggregation
iterations of five days) that a strict data-efficiency accounting must charge against
it. The oracle is a short-horizon CEM and therefore not a ceiling (§4.4). Finally,
SAC converged on only 10 of 20 seeds; we report it as a robustness observation rather
than a tuned competitor.
