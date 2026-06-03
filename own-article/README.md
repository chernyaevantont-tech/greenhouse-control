# Article Experiment Notebooks

This folder contains reproducible notebooks for testing the publishable claims
around a data-efficient interpretable greenhouse MPC controller with
physics-informed sparse dynamics.

The notebooks deliberately ignore OOD/LLM components and focus on:

1. Physics-informed SINDy feature ablations.
2. Closed-loop MPC performance.
3. DAgger-style dataset aggregation.
4. Interpretability of sparse equations.
5. Cross-season / cross-start-date generalization.

## Recommended order

1. `00_data_collection.ipynb`
2. `01_sindy_feature_ablation.ipynb`
3. `02_closed_loop_mpc_benchmark.ipynb`
4. `03_dagger_dataset_aggregation.ipynb`
5. `04_interpretability_and_equations.ipynb`
6. `05_cross_season_generalization.ipynb`

All generated artifacts are written to `own-article/results_scenarios/`.
The helper code resolves `start_date` into an explicit GreenLightGym2 weather
scenario (`location`, `growth_year`, `start_day`), so train/test and seasonal
generalization runs use genuinely different weather trajectories.

Ignore `own-article/results/` if it exists locally; it is retained only as a
stale pre-fix run.

- `datasets/`: `.npz` trajectory datasets.
- `models/`: pickled SINDy bundles.
- `tables/`: CSV tables for the paper.
- `figures/`: PNG figures for the paper.

Each notebook has a `FAST_MODE` switch. Keep it enabled for smoke tests; disable
it for article-grade runs.
