# Article experiments — E0–E8 (protocol-aligned, complete)

Reproducible notebooks for the **data-efficient interpretable greenhouse SINDy-MPC**
study, implemented per [`EXPERIMENT_PROTOCOL.md`](EXPERIMENT_PROTOCOL.md). All claims
are **in-silico** on `gl_gym/GreenLightTomato-v0` (GreenLight-Gym2).

The **full protocol E0–E8** is implemented at article grade on **Rostov-on-Don
2018–2023** with the economic indicator **EPI** read directly from the simulator:
E0–E3 (core hypothesis chain), E4 (online adaptation, Г4а), E5 (generalization +
OOD, Г4б,в), E6 (sensitivity), E7 (fault injection + safety), E8 (statistical
validity across all hypotheses).

> **Framing: Path A (honest in-silico benchmark).** The pre-registered central
> hypothesis (SINDy-MPC is non-dominated / low price of interpretability) is **not
> confirmed** — a tuned rule-based heuristic and a fairly-implemented PPO are
> competitive or better on EPI. The paper's contribution is therefore an honest
> economic benchmark: (1) simple heuristics are Pareto-strong; (2) RL baselines are
> misleading unless normalized (PPO −13→+3.8 with VecNormalize); (3) sparse system-ID
> for MPC has a specific failure mode — magnitude-thresholded selection silently drops
> the control-critical boiler term; (4) SINDy-MPC's value is transparency + safety/OOD/
> adaptation, not EPI supremacy. **Compare in two axes (EPI × violations)** — EPI does
> not penalise constraint violations. See `EXPERIMENT_PROTOCOL.md` §0.

## Notebooks (run in order)

| Notebook | Experiment | Output |
|---|---|---|
| `E0_canonical_setup_and_metrics.ipynb` | E0 — EPI metric + frozen protocol config | `protocol.json`, EPI decomposition |
| `E1_data_and_scenarios.ipynb` | E1 — Rostov splits, excitation (noise + PRBS), budget/κ curve | `.npz` datasets, split + κ tables |
| `E2_identification_ladder.ipynb` | E2 — denoise×optimizer×library×degree ablation + gates | ablation table, `recipe_frozen.json`, equations |
| `E3_closed_loop_benchmark.ipynb` | E3 — closed-loop EPI benchmark + statistics | main mean±CI table, Pareto, Wilcoxon |
| `E4_online_adaptation.ipynb` | E4 — EKF-SINDy + DAgger recovery under OOD shift | adaptation table, DAgger curve |
| `E5_generalization_ood.ipynb` | E5 — train→test matrix, Mahalanobis/ensemble OOD, guard, ROC | generalization matrix, OOD corr, guard, ROC |
| `E6_sensitivity.ipynb` | E6 — price/horizon/threshold/uncertainty sensitivity | tornado, price-ranking robustness |
| `E7_fault_injection.ipynb` | E7 — sensor/actuator faults + safety supervisor | degradation table, supervisor mitigation |
| `E8_statistical_validity.ipynb` | E8 — Wilcoxon+Holm+bootstrap CI across all hypotheses | significance tables, seed boxplots |

`protocol_config.py` is the single source of truth (split, budgets, seeds, horizons,
HP budget) and reads the simulator's prices/corridors via `read_env_economics()`.
Helper code lives in `article_experiment_utils.py`.

**Distributed (article-grade) runners** (heavy grids run across two LAN servers, see
[`REMOTE_RUN.md`](REMOTE_RUN.md)): `run_e3_seeds.py`, `run_e4_shift.py`,
`run_e5_grid.py`, each with a matching `merge_*.py`. Snapshots in
`results_e0_e3_final/` and `results_e4_e8_final/`.

## How to run

The project venv is `…/greenlight/sindylom/.venv` (uv-managed, Python 3.14;
has gl_gym, pysindy 2.1, do-mpc, casadi, torch, gymnasium, stable-baselines3,
nbformat/nbclient). Notebooks read **`FAST_MODE`** from the `ARTICLE_FAST` env var.

```bash
# FAST_MODE smoke (tiny data/horizons/seeds — minutes, validates the whole pipeline)
python run_all_notebooks.py

# article-grade (full Rostov, >=10 seeds, 60-day rollouts — hours; oracle/RL reduced)
ARTICLE_FAST=0 python run_all_notebooks.py
```

Run a single notebook: `python run_all_notebooks.py E2_identification_ladder.ipynb`.

## Key design points

- **EPI is the simulator's economics, not a proxy.** `EPI = Σ profit` per season is
  harvested from `env.step(...)` info (gl_gym `GreenhouseReward`); revenue and
  heat/CO₂/electricity costs are decomposed from the same dict. Constraint corridors
  (CO₂∈[300,1600], T∈[15,34], RH∈[50,85]) come from `env.constraints_*`.
  **EPI does NOT penalise violations** → compare via the Pareto artifact
  `results_scenarios/figures/e3_pareto_annotated.png` + `tables/e3_pareto_table.csv`
  (per-method EPI, violations, `scaled_penalty`, non-dominated flag).
- **Rostov soil** (`rostov_soil.apply_rostov_soil`) is patched automatically inside
  `_make_env` (gated on location) before the first weather load.
- **Identification ladder** factors: optimizer {STLSQ, SR3, Ensemble, ConstrainedSR3},
  denoise {none, Savitzky–Golay, Kalman}, library {raw, physics, physics_no_cross},
  degree {1,2}. The recommended recipe is frozen (pre-registration) before E3.
- **One recipe across E3/E4/E5.** All runners load it via
  `protocol_config.load_frozen_recipe()` (single source of truth = `recipe_frozen.json`);
  previously E4/E5 hard-coded STLSQ while E3 used the frozen ensemble recipe.
- **Documented recipe defect (a finding, not a bug).** The confirmatory recipe
  (`physics_no_cross` + threshold ≈0.05) zeroes the small-magnitude but control-critical
  boiler term `uBoil→t_in`, so the surrogate has no modelled heating actuator. Restoring
  it (dense recipe `stlsq/1e-3` or DAgger) lifts EPI +0.82 → +3.8…+6.0 (10-seed
  counter-experiment, `tables/e3_dagger_compare_*.csv`). The dense model is **equally
  interpretable** (explicit equations) — only parsimony is lost, not transparency. Root
  cause: `sparsity` was one of the E2 recipe-selection pareto objectives.
- **Gates:** MPC-embeddability (degree-1 → CasADi/do-mpc within a step-time budget)
  and transparency (sign/dimension checks + bootstrap structural stability).
- **E3 controllers:** rule-based · SINDy-MPC (frozen recipe) · grey-box-MPC
  (reduced linear physics) · NN-MPC · PPO · SAC · **oracle-MPC** (CEM over the true
  simulator model `env.F`). Variance comes from re-collecting train per seed
  (retraining surrogates) — the valid source the legacy `07_multi_seed` lacked.
  Oracle and RL run on a reduced seed set (CPU budget).

All artifacts are written to `results_scenarios/{datasets,models,tables,figures}` plus
`protocol.json`, `recipe_frozen.json` (CONFIRMATORY — pre-registered open-loop recipe
`physics_no_cross/ensemble`) and `recipe_exploratory.json` (post-hoc closed-loop recipe
`physics/stlsq/0.1`, reported as sensitivity only). The legacy `results/` directory is
archived under `archive/results_legacy/`; the legacy `00`–`07` notebooks are superseded
by `E0`–`E8`.
