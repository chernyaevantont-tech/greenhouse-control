<!-- DRAFT §3 Methods -->

## 3. Methods

### 3.1 Primary metric: economic performance indicator (EPI)

All controllers are scored by the simulator's own economics rather than a proxy.
At each step the GreenLight reward model returns a profit
$\pi_k = g_k - c_k$, where the gain $g_k = (x^{\mathrm{fruit}}_k -
x^{\mathrm{fruit}}_{k-1})\,\tfrac{10^{-6}}{\mathrm{dmfm}}\,p_{\mathrm{fruit}}$ is the
revenue from fruit dry-matter growth (converted to fresh weight through the
dry-to-fresh ratio $\mathrm{dmfm}=0.065$ and priced at $p_{\mathrm{fruit}}=1.6~
\mathrm{EUR/kg}$), and the variable cost $c_k$ sums heating, lighting and CO$_2$
dosing priced at $0.09~\mathrm{EUR/kWh}$, $0.30~\mathrm{EUR/kWh}$ and
$0.30~\mathrm{EUR/kg}$. The seasonal indicator is $\mathrm{EPI}=\sum_k \pi_k$
$[\mathrm{EUR/m^2}]$. We verified that the per-step economics used by every
controller (and by the oracle, §3.7) are *identical* term-for-term to the
simulator's reward, so EPI is the ground-truth objective and not an approximation.

EPI intentionally omits constraint penalties. Because a controller can raise EPI by
spending more time outside the productive corridors (CO$_2 \in [300,1600]$~ppm,
$T\in[15,34]~^\circ$C, RH$\in[50,85]\%$), the primary comparison is a **two-axis
Pareto criterion** — EPI versus the seasonal count of violation steps — reported
with a non-dominated frontier (Fig.~\ref{fig:pareto}). As a secondary,
dimensionally-consistent severity scalar we report `scaled_pen`, the violation area
per constraint normalised by the simulator's own scaling. We deliberately do not
combine EPI and violations into a single "EUR-penalised EPI", since the simulator
does not price violations and any conversion would be arbitrary.

### 3.2 Simulator, location and data

Experiments use the GreenLight tomato model \citep{katzin2020greenlight} through the
GreenLight-Gym interface \citep{vanlaatum2025greenlightgym}. The location is
Rostov-on-Don ($47.24^\circ$N, $39.71^\circ$E); real weather for 2018--2023 is
obtained from ERA5/ERA5-Land via Open-Meteo, with derived sky and soil terms. A
season is 60 days starting 1 March, at a 15-minute control period. We use a
leakage-free year split: training on 2018--2019, in-distribution test on 2020, and
2021--2023 held out as out-of-distribution (OOD) for the generalisation and
adaptation experiments. Identification data are collected by the rule-based
controller augmented with a pseudo-random binary excitation signal (PRBS, amplitude
$0.3$) on the actuators to improve identifiability, with the regression condition
number monitored.

### 3.3 Controllers

We compare **ten controllers** spanning five families (Table~\ref{tab:controllers}):
a tuned **rule-based** agronomic heuristic (the lower reference and the DAgger
expert); the proposed **SINDy-MPC** in four variants — the pre-registered
*confirmatory* recipe, a boiler-preserving *dense* recipe, and DAgger-repaired
versions of each; a reduced first-principles **grey-box MPC** that reuses the same
solver; a **neural-network MPC** (NN-MPC, $64{\times}64$ surrogate); two
reinforcement-learning policies, **PPO** \citep{schulman2017ppo} and **SAC**
\citep{haarnoja2018sac}, via Stable-Baselines3 \citep{raffin2021sb3}; and an
**oracle** MPC that plans over the true simulator dynamics (§3.7). All learned
controllers receive an equal hyper-parameter budget (16 trials, one search method).
RL is trained for $2\times10^5$ environment steps with observation and reward
normalisation (VecNormalize), a standard practice whose omission we found to
distort the RL result badly (§4.5).

### 3.4 Proposed pipeline and pre-registration

The proposed method is a four-stage pipeline: (i) collect data with the rule-based
controller plus PRBS; (ii) identify an interpretable discrete one-step map
$x_{k+1}=\Xi\,\Theta(x_k,u_k,d_k)$ by sparse regression, degree~1 for analytic MPC
embeddability; (iii) embed the surrogate in a CasADi/do-mpc solver that optimises an
EPI-aligned objective under the climate constraints on a finite horizon; and (iv)
optionally adapt online (DAgger or EKF-SINDy) with an OOD monitor and a safe
fallback. The **identification recipe** — denoising, optimiser and library — is not
fixed a priori: it is selected in an ablation (E2) and then *frozen* by open-loop
identification metrics (multi-step rollout stability, MPC-embeddability,
transparency) **before and independently of** any closed-loop EPI on the held-out
test season. This pre-registration guards against circular inference. The frozen
*confirmatory* recipe is `physics_no_cross` library, degree~1, ensemble optimiser;
a closed-loop-selected *exploratory* recipe is recorded separately and reported only
as post-hoc sensitivity, never as the confirmatory result. The identical frozen
recipe is loaded by every downstream experiment through a single source of truth.

### 3.5 Gates

A model is admitted to the closed-loop comparison only if it passes two gates:
**transparency** (glass-box explicit equations, a threshold fraction of passed
physical sign/dimension checks, and structural stability of the active-term set
under bootstrap) and **MPC-embeddability** (the degree-1 map compiles into the
solver within a per-step time budget). These gates are, deliberately, open-loop; the
consequences of that choice are the subject of §4.3.

### 3.6 Statistics

The valid source of variance is the *re-collection of training data per seed*: each
seed re-collects the identification dataset and re-fits the surrogate, so the
per-seed models genuinely differ (unlike fixing the model and varying only the
rollout seed, which yields zero model variance). We use 20 seeds for all
deterministic and cheap controllers; the compute-heavy oracle and NN-MPC use the
full 20, while SAC converged on only 10 of 20 seeds and is reported on those.
Pairwise comparisons use the Wilcoxon signed-rank test paired by seed
\citep{wilcoxon1945} with Holm correction for multiplicity \citep{holm1979},
reporting effect size (Cohen's $d$) and bootstrap 95\% confidence intervals
\citep{efron1994bootstrap, demsar2006}.

### 3.7 The oracle

The oracle is a receding-horizon cross-entropy-method (CEM) controller that plans
directly over the true simulator integrator (48 sampled action sequences, a 3-hour
horizon, two refinement iterations, warm-started from the rule-based action), with
the same economic objective as the MPC. Because it uses the true model, the
gap between it and a surrogate-based MPC isolates model fidelity. It is, however,
**not** an upper bound on seasonal EPI: a short receding horizon greedily maximises
short-horizon profit, which is not the same as maximising seasonal profit, and the
sampling optimiser degrades at longer horizons. We treat it as a fidelity control,
not a ceiling, and substantiate this in §4.4.
