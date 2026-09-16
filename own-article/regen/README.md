# Simulated greenhouse control experiments: data and code

Data and code underlying

> **Multi-step stability selects sparse surrogate models for economic greenhouse climate
> control: an in silico study**

Every value the article reports (in its tables, its figures and its running text) is
derived from the comma-separated files under `results/` by the scripts in this directory.

Nothing here is measured in a physical greenhouse. All quantities come from the GreenLight
tomato greenhouse model, driven by reanalysis weather for Rostov-on-Don (47.24° N,
39.71° E), and describe simulated seasons.

## The study in brief

A sparse surrogate model of the greenhouse climate is identified from excitation data and
then used inside an economic model-predictive controller. Two questions are asked. First,
which inexpensive open-loop criterion (one-step prediction error, multi-step rollout stability, or the conditioning of the regression) anticipates the seasonal economics that
the closed loop eventually delivers. Second, whether physically motivated basis functions,
which are nonlinear transforms of the same measured states, help or hurt a surrogate built
for control.

Seventy-two identification configurations were screened open-loop. Fifteen controllers
(surrogate-based predictive controllers on three feature libraries, a neural-surrogate
controller, two reinforcement-learning agents, a full-model planner, and an agronomic
setpoint heuristic before and after tuning) were then compared over four 60-day test
seasons with up to twenty identification replicates each. Outcomes are the seasonal economic
margin and the time spent outside the climate corridors, treated jointly under Pareto
dominance rather than combined into one score.

## What is in the data

One row is one simulated season: one controller, one identification replicate, one test
year. Files are grouped by experimental wave; `results/final/` holds the merged blocks and
the derived tables, `results/final/tables/SUMMARY.md` summarises that tree, and
`results/final/NUMBERS.md` lists every quantity the article states with the value recomputed
from the tree and the files it comes from.

The schema is not identical across waves. The outcome and constraint columns below appear
everywhere. The rest depend on what the wave varied, and two conventions differ:

- the controller-comparison waves identify a row by `method`; the supporting blocks
  (`adapt`, `guard`, `faults`, `design`, `mechanism`) identify it by `block` and
  `condition`, because what varies there is a treatment rather than a controller;
- `stop_reason` and `solver_aborted` are recorded by the later waves and by the supporting
  blocks that can exhaust the solver budget. Where they are absent, `truncated` and
  `season_fraction` carry the same information.

Read the header row before selecting columns.

### Outcome columns

| column | meaning | unit |
|---|---|---|
| `epi` | seasonal economic margin: the simulator's own per-step profit, summed | EUR m⁻² season⁻¹ |
| `revenue` | income from modelled fruit dry-matter growth | EUR m⁻² |
| `cost_total` | variable costs, the sum of the three below | EUR m⁻² |
| `cost_heat`, `cost_elec`, `cost_co2` | heating, lighting and CO₂ enrichment | EUR m⁻² |
| `fruit_dm_growth` | accumulated fruit dry matter | mg m⁻² |
| `energy_heat_kwh_m2`, `energy_elec_kwh_m2` | the two energy costs at the tariff, as physical use | kWh m⁻² |
| `co2_kg_m2` | CO₂ cost at its price, as physical use | kg m⁻² |

### Constraint columns

The simulator enforces a productive band on three variables: CO₂ 300–1600 ppm, air
temperature 15–34 °C, relative humidity 50–85 %. For each of `t_in`, `co2` and `rh`:

| column | meaning | unit |
|---|---|---|
| `<var>_in_corridor_pct` | share of control steps inside the band | % |
| `<var>_violation_steps` | control steps outside it | count |
| `<var>_violation_area` | summed distance outside it, over steps | ppm·step, °C·step, %·step |
| `violation_steps_total` | the three violation-step counts added | count |

`violation_steps_total` is the second axis of every comparison in the article. It counts
steps, not seasons, out of 5760 per season.

### Actuator and solver columns

| column | meaning |
|---|---|
| `boiler_sum`, `lamp_sum`, `co2_injection_sum`, `vent_sum` | accumulated normalised control, each actuator on [0, 1] |
| `solver_failures` | steps at which the optimiser did not converge and the fallback action was applied |
| `max_solver_failures` | the budget; a season that exhausts it stops early |
| `steps`, `steps_expected`, `season_fraction` | steps completed, expected, and their ratio |
| `truncated` | the simulator ended the season early |
| `solver_aborted` | the season ended because the solver budget was exhausted (later waves) |
| `stop_reason` | which of the above applies (later waves) |

Seasons that end early are kept as outcomes, not discarded: stopping early forgoes both
revenue and cost, and which controllers stop is itself a result. Analyses that require
complete seasons say so and filter on these columns.

### Identifying columns

| column | meaning |
|---|---|
| `method` | controller label, in the comparison waves |
| `block`, `condition` | experiment and treatment, in the supporting blocks |
| `seed` | identification replicate |
| `test_year` | test season, 2014–2017 or 2020–2023 |
| `objective` | which stage cost the predictive controller optimised |
| `horizon` | prediction horizon, in control steps |
| `xi_uboil` | the identified direct boiler-input coefficient of the surrogate; zero when thresholding removed it |
| `rng_seed`, `config_hash`, `git_sha`, `regen_id`, `image` | provenance of the run |

`xi_uboil` is the mechanism variable of the article: whether the coefficient survives
sparsification, rather than how well-conditioned the regression is, is what tracks the
closed-loop ranking.

### Open-loop identification files

`ladder_rerun/` and `holdout/` hold one row per fit rather than per season. They share the
measurement columns:

| column | meaning | unit |
|---|---|---|
| `variant` | feature library: `raw`, `physics_no_cross`, `physics` | — |
| `optimizer` | sparse estimator | — |
| `kappa` | condition number of the regression matrix | — |
| `nonzero` | non-zero coefficients after thresholding | count |
| `one_step_rmse_t_in` | one-step prediction error for indoor temperature | °C |
| `rollout_rmse_t_in` | free-running rollout error at the reported horizon | °C |
| `diverged_frac` | share of rollouts that diverged | — |
| `rollout_horizons` | the horizons evaluated, in control steps | — |

`ladder_rerun/` adds what the sweep varied (`degree`, `denoise`, `n_days_train`) and two
screens, `embeddable` (whether the fit can be embedded in the optimiser's nonlinear program)
and `sign_pass`.

`holdout/` instead adds `fit_year`, `eval_year` and `in_sample`: it refits on one training
season and evaluates on the other in all four directions, which is how the article separates
the library ordering from the evaluation year.

## Reproducing the article's numbers

From the deposited results, without re-running any simulation:

```bash
python make_tables.py --out results/final     # every derived table, and tables/SUMMARY.md
python verify_regen.py --out results/final    # acceptance gates; non-zero exit = do not publish
```

The six figure scripts in `figures/` read the same tree and carry their own self-checks;
each fails the build rather than drawing a figure that disagrees with the data.

## Re-running the experiments

```bash
python repro.py --selftest                                  # determinism check
python run_regen.py --experiment <block> --seeds 0-19 --out <dir>
python run_regen.py --merge --out <dir>
```

`INSTRUCTIONS.md` is the runbook. The blocks are `main` (the headline comparison),
`ladder` (the open-loop identification sweep), `mechanism` (the sparsity sweep and the
single-coefficient knock-out and knock-in), `parity` (the full-model planner), `adapt`
(static against on-policy re-identification and an observer), `guard` (out-of-distribution
detection), `faults` (six actuator and sensor faults with and without a residual
supervisor), and `design` (sensitivity to horizon, threshold and coefficient perturbation).

`regen_config.py` is the only place a constant that can change a number is declared: the
season, the control step, the horizon, the solver budget, the seed set, the train/test split
and the identification recipes. `recipe_frozen_v2.json` records the confirmatory recipe with
its sparsity threshold. Simulation itself is not reimplemented here; every rollout calls the
model through the `article_experiment_utils` interface in the parent directory.

The price sensitivity needs no rollouts. The simulator records per-step profit, so
`make_tables.py` re-scores the recorded physical quantities over the price grid while
holding the trajectories at their nominal-price optimum, which is what a claim about the
*ranking* being robust to prices means, and what the corresponding table reports.

### Software

Package versions, identical in both environments below: numpy 1.26.4, scipy 1.17.1,
pandas 2.3.3, scikit-learn 1.8.0, pysindy 2.1.0, casadi 3.7.2 (bundled IPOPT), do-mpc 5.1.1,
gl_gym 0.3.1, gymnasium 1.2.3, torch 2.11.0, stable-baselines3 2.9.0; the pinned list is
`requirements-cluster.txt` at the archive root.

Two computing environments produced the waves, and the `image` column of every result row
records which. The canonical default-objective blocks (`final/main.csv`, `mechanism*.csv`,
`faults.csv`, `design*.csv`, `parity.csv`, `ladder*.csv` and, as `v4`, `draws.csv`) were
produced on a compute cluster in a Linux container built from `python:3.11-slim`
(`image == "greenhouse-regen:v1"`). Every other file, including `final/adapt.csv` and
`final/guard.csv` and all the later waves, was produced on a workstation under
Python 3.14 (`image == "local"`). `python repro.py --fingerprint` prints the full record of
the environment it runs in; the `regen_manifest.json` of each results directory carries the
configuration hash and the git commit but no environment fingerprint and no package
versions -- the row-level image tag is the only per-wave record of where it ran.

`repro.py --selftest` runs the pipeline twice in one process and compares SHA-256 digests of
the training data, the identified coefficient matrices, the network weights and the
closed-loop trajectory and margin. Identification and simulation are deterministic given the
seed and these versions. The reinforcement-learning baselines are deterministic under the
same conditions but were trained once; their weights are not redistributed here.

## Caveats a reader should know

**Do not compare cells across environments.** Closed-loop trajectories amplify
platform-level floating-point differences over 5760 steps: the same deterministic heuristic
scores −1.2061 EUR m⁻² in one harness and −1.2264 in another under an identical
configuration hash. Waves are therefore compared within one environment, never cell by cell
across them. The article reports the size of this effect.

**One site, one planting date, one crop model, one weather source.** The comparison is
between controllers under identical conditions, not a claim about absolute achievable
margin. No recursive feasibility or stability guarantee is claimed or proved.

**Two files are superseded and kept only as a record.** `results_pull/raw/` is the compute
cluster's own output. For most blocks it matches `results/final/` row for row, but its
`adapt.csv` and `guard.csv` hold one bootstrap realisation per seed (180 rows) where
`results/final/` holds ten (1800 rows). A single realisation is a lottery ticket: across
draws within one seed the margin has a standard deviation of 1.25 and 1.31 EUR m⁻² for the
two controllers measured on that axis, as large as the gap between the leading controllers,
and on a six-seed by six-draw grid the leader leads in 32 of 36 cells rather than all of
them. Read `results/final/`. The claim table in that superseded directory carries a header
saying where it disagrees with the article.

**The identification ladder was corrected.** `results/final/ladder.csv` was computed with
open-loop evaluation horizons of up to seven days instead of the intended 4, 20 and 96
steps. Everything diverges over seven days, so that wave overstates instability and 30 of
its 72 configurations clear the open-loop gates instead of 32. The article's ladder numbers
and open-loop figures come from `results/ladder_rerun/`. The uncorrected wave is kept
because the correction is part of the record.

## Contents

```
regen/
  regen_config.py         the only place a number-affecting constant is declared
  recipe_frozen_v2.json   the confirmatory identification recipe
  repro.py                seeding, environment fingerprint, determinism self-test
  run_regen.py            experiment driver, and --merge
  experiments_support.py  the supporting blocks
  make_tables.py          derived tables and the claim-to-column map
  verify_regen.py         acceptance gates
  exp_draws.py            the bootstrap-draw axis
  ladder_notuboil.py      term-deletion library, open loop
  kappa_notuboil.py       its conditioning
  analyze_notuboil.py     its closed-loop contrasts
  make_archive.py         declares what this archive contains
  results/                one row per simulated season, by wave
  results_pull/raw/       the cluster's own output; superseded, see above
```

Run logs, container manifests and the cluster submission script are not included: they are
infrastructure for one cluster and duplicate what the result files already record.
