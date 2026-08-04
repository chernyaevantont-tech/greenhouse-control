<!-- DRAFT §4 Results. §4.3 is in 04-3_mechanism.md (insert between 4.2 and 4.4). -->

## 4. Results

We report the benchmark not as a leaderboard but as a **differential diagnosis**:
the controller cast is an elimination structure whose purpose is to explain why the
pre-registered interpretable controller underperforms and to rule out the obvious
alternative causes. Table~\ref{tab:scorecard} summarises the verdicts on the
pre-registered hypotheses; the subsections that follow supply the evidence.

### 4.1 Identification ladder and the frozen recipe

The E2 ablation over denoising, optimiser, library and degree ($42$ recipes)
selected, by open-loop rollout stability and the transparency and embeddability
gates, a `physics_no_cross` / degree-1 / ensemble recipe as the **confirmatory**
recipe, which was then frozen before any closed-loop evaluation (§3.4). Multi-step
rollout divergence is negligible for this recipe (the diverged-trajectory fraction
is $\approx 0$ for budgets $\ge 3$ days), so it passes the open-loop bar that
pre-registration relies on. Hypothesis Г2 (a stable-rollout recipe exists) is thus
met — but, as §4.3 shows, open-loop stability is necessary and not sufficient.

### 4.2 Closed-loop economic benchmark

Table~\ref{tab:e3main} reports the 20-seed closed-loop EPI, violations and severity
for all ten controllers, with paired significance against the rule-based baseline;
Fig.~\ref{fig:pareto} shows the EPI--violation Pareto plane. The result is clean and
sobering for the proposed method. Only the DAgger-repaired SINDy-MPC reaches the top:
$5.23\pm2.40~\mathrm{EUR/m^2}$, statistically indistinguishable from the rule-based
$4.63$ ($\Delta=+0.59$, $p_\mathrm{Holm}=0.26$). **Every other controller is
significantly worse than the tuned heuristic**, including the grey-box MPC
($3.79$, $p_\mathrm{Holm}=0.017$), PPO ($3.36$, $p_\mathrm{Holm}=0.001$), the
pre-registered confirmatory SINDy-MPC ($1.18$, $p_\mathrm{Holm}=0.009$), SAC
($-2.41$) and NN-MPC ($-5.09$, $p_\mathrm{Holm}\approx2\times10^{-5}$). The
non-dominated frontier comprises the DAgger-repaired SINDy-MPC, the rule-based
heuristic, PPO, and — only as a degenerate minimum-violation corner with negative
EPI — SAC. On the severity axis the picture is if anything kinder to the heuristic's
challengers: the DAgger SINDy-MPC accrues a lower total violation severity than the
rule-based controller ($426$ vs $485$) despite more violation steps, which is why we
report both axes.

The pre-registered central hypothesis — SINDy-MPC non-dominated at a low price of
interpretability — is therefore not confirmed. The heuristic is a strong,
hard-to-beat reference, and the only interpretable controller that matches it does so
through a repair whose necessity we now explain.

<!-- ===== §4.3 (mechanism) is inserted here — see 04-3_mechanism.md ===== -->

### 4.4 Ruling out model fidelity: the oracle over-spends

If the surrogate simply were not accurate enough, an MPC over the *true* model
should win. It does not. The oracle returns only $1.99\pm0.68~\mathrm{EUR/m^2}$
(Table~\ref{tab:e3main}), below the rule-based heuristic, the DAgger SINDy-MPC, the
dense/grey-box models and PPO. A horizon probe explains why: sweeping the oracle's
planning horizon, EPI *falls* rather than rises with horizon ($+0.26$ at 3~h,
$+0.04$ at 12~h, $-0.51$ at 24~h on a 14-day window where the rule-based controller
scores $+0.63$). Decomposing the economics, fruit growth and revenue rise toward the
heuristic's level as the horizon lengthens, but cost rises faster — chiefly
electricity and CO$_2$ — so the oracle attains comparable production more expensively.
This is greedy over-spend from a short receding horizon, compounded by degradation of
the sampling optimiser in higher dimensions, not a fidelity deficit. The consequence
for the protocol is that the "gap-to-oracle" framing (hypothesis Г1) is not a
meaningful ceiling here: a genuine ceiling requires a long-horizon or terminal-value
optimal control, which we leave to future work. Importantly, this is a structural
property of short-horizon economic MPC, not an experimental error: the oracle
correctly maximises the very quantity the simulator rewards, only greedily and over
too short a window.

### 4.5 Ruling out an interpretability bottleneck: RL and NN-MPC

Would a black-box learner have won, making interpretability the bottleneck? No. Two
observations settle it. First, RL baselines are treacherous without normalisation: a
naive PPO scores $-13~\mathrm{EUR/m^2}$, but adding standard observation/reward
normalisation lifts it to $+3.4$ — a reproducibility lesson, not a property of RL
\citep{henderson2018matters}. Even so, at 20 seeds the normalised PPO ($3.36$)
remains significantly below the heuristic, and SAC is unstable, diverging on 10 of 20
seeds. Second, the black-box NN-MPC is the worst controller in the study
($-5.09~\mathrm{EUR/m^2}$), decisively beaten by every interpretable SINDy variant.
Interpretability is not what costs the win; the heuristic is simply strong, and among
learned controllers it is the sparsity mechanism of §4.3 that governs performance.

### 4.6 Online adaptation is a null

Under spring OOD shifts (2021--2023, same planting season, year-to-year), the offline
surrogate already generalises well — its mean EPI is $\approx 0$, beating the
rule-based controller's $-2.9$ under the same shift — leaving little gap for
adaptation to recover. Consistent with this, over 60 (shift $\times$ seed) pairs
DAgger improves on the static offline model by only $+0.39~\mathrm{EUR/m^2}$
($p=0.088$, not significant), and online EKF-SINDy is significantly *worse*
($-2.17$, $p<10^{-6}$); an earlier, smaller sample ($n=9$) that had suggested a
significant DAgger gain does not survive the larger design. Hypothesis Г4a (online
adaptation recovers EPI) is thus not supported. Diagnostically, we find the failure
under shift is not a gradual coefficient drift that adaptation could track but a
data problem: single-season on-shift identification data are intrinsically confounded
(the rule-based policy ventilates when it is hot, giving $\mathrm{corr}(u_\mathrm{Vent},
T_\mathrm{in})=+0.67$ against $+0.03$ for the multi-year offline data), so a model
re-fit on "fresh" shift data mislearns the ventilation effect. What confers OOD
robustness is structure (keeping the boiler term) and guarding (§4.7), not
coefficient adaptation.

### 4.7 Where the interpretable model pays off: safety and OOD guarding

The demonstrable value of the transparent surrogate is in safety. The two epistemic
signals it affords — Mahalanobis distance on the exogenous inputs and ensemble
prediction variance — correlate with error and profit across the generalisation
matrix (Mahalanobis: $+0.63$ with rollout-RMSE, $-0.50$ with EPI; ensemble std:
$-0.57$ with EPI). Gating the controller on the Mahalanobis signal, with a fallback
to the rule-based policy on OOD steps, cuts seasonal violations from $1723$ to $863$
(a $50\%$ reduction) while, notably, *improving* EPI (from $-2.06$ to
$-1.48~\mathrm{EUR/m^2}$); the reduction is highly significant over 200 pairs
($p\approx10^{-24}$). Under injected sensor/actuator faults (E7), a residual-based
supervisor with the same rule-based fallback significantly mitigates all six fault
types, reducing violations by $1304$ steps on average ($p\approx6\times10^{-21}$,
120 pairs) and recovering EPI for most faults (Table~\ref{tab:e7}). Hypothesis Г4b
(an OOD signal that predicts error and enables a protective guard) is the study's
strongest positive result.

### 4.8 Robustness of the ranking

A sensitivity analysis (E6) shows that the economic ranking is governed by prices far
more than by design choices: the EPI range induced by the fruit price ($19.7$) and
the energy price ($13.3~\mathrm{EUR/m^2}$) dwarfs that of surrogate-coefficient uncertainty
($2.7$), the sparsity threshold ($1.3$) or the MPC horizon ($0.6$)
(Fig.~\ref{fig:tornado}). Moreover the ranking is not robust to the energy price:
when energy is expensive, the thrifty grey-box model overtakes the more
energy-intensive heuristic. The identity of the "winner" is thus an economic
contingency as much as a control-design fact — a caution for any single-price
benchmark, and further reason to report the Pareto structure rather than a scalar
ranking.
