# Article experiments — E0–E3 (protocol-aligned)

Reproducible notebooks for the **data-efficient interpretable greenhouse SINDy-MPC**
study, implemented per [`EXPERIMENT_PROTOCOL.md`](EXPERIMENT_PROTOCOL.md). All claims
are **in-silico** on `gl_gym/GreenLightTomato-v0` (GreenLight-Gym2).

This pass covers the **core hypothesis chain E0→E3** at article grade, on
**Rostov-on-Don 2018–2023** with the economic indicator **EPI** read directly from
the simulator. E4–E8 (online adaptation, OOD, sensitivity, faults, full multi-seed)
are the next pass; the legacy `0x_*.ipynb` notebooks remain as their scaffolding.

## Notebooks (run in order)

| Notebook | Experiment | Output |
|---|---|---|
| `E0_canonical_setup_and_metrics.ipynb` | E0 — EPI metric + frozen protocol config | `protocol.json`, EPI decomposition |
| `E1_data_and_scenarios.ipynb` | E1 — Rostov splits, excitation (noise + PRBS), budget/κ curve | `.npz` datasets, split + κ tables |
| `E2_identification_ladder.ipynb` | E2 — denoise×optimizer×library×degree ablation + gates | ablation table, `recipe_frozen.json`, equations |
| `E3_closed_loop_benchmark.ipynb` | E3 — closed-loop EPI benchmark + statistics | main mean±CI table, Pareto, Wilcoxon |

`protocol_config.py` is the single source of truth (split, budgets, seeds, horizons,
HP budget) and reads the simulator's prices/corridors via `read_env_economics()`.
Helper code lives in `article_experiment_utils.py`.

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
- **Rostov soil** (`rostov_soil.apply_rostov_soil`) is patched automatically inside
  `_make_env` (gated on location) before the first weather load.
- **Identification ladder** factors: optimizer {STLSQ, SR3, Ensemble, ConstrainedSR3},
  denoise {none, Savitzky–Golay, Kalman}, library {raw, physics, physics_no_cross},
  degree {1,2}. The recommended recipe is frozen (pre-registration) before E3.
- **Gates:** MPC-embeddability (degree-1 → CasADi/do-mpc within a step-time budget)
  and transparency (sign/dimension checks + bootstrap structural stability).
- **E3 controllers:** rule-based · SINDy-MPC (frozen recipe) · grey-box-MPC
  (reduced linear physics) · NN-MPC · PPO · SAC · **oracle-MPC** (CEM over the true
  simulator model `env.F`). Variance comes from re-collecting train per seed
  (retraining surrogates) — the valid source the legacy `07_multi_seed` lacked.
  Oracle and RL run on a reduced seed set (CPU budget).

All artifacts are written to `results_scenarios/{datasets,models,tables,figures}` plus
`protocol.json` and `recipe_frozen.json`. The legacy `results/` directory is stale.
