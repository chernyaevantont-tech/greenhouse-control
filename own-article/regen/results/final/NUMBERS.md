# NUMBERS — every quantity the manuscript states, recomputed, with its source

Generated 2026-09-23 by `paper/en/make_numbers_md.py` from the checks that gate the manuscript build (`verify_tables.py`, `verify_prose.py`): 800 table cells and 410 values in the running text, each compared with the value recomputed from this tree at half a unit in the last printed digit. Mismatches at generation time: 0. Configuration hash of every wave read: `637c6b535a9e`.

Each block names the files the values are computed from, relative to `regen/results/`. The loaders behind every recomputation (`figures/_plotstyle.py`) apply one deduplication key, (method or block, seed, test year), and one exclusion rule, solver-aborted seasons, before any average is taken.

`tables/SUMMARY.md` is a different file: the derived summary of the canonical default-objective tree written by `make_tables.py`. It is not the manuscript's claim map.

## Tables

### Table 1 — Three benchmarking risks, the safeguards used in this study and the measured sensitivity to removing each safeguard (`tab:defects`)

Sources: `n2_tune/tune_rb_n2.csv`, `priced_main/*.csv`, `priced_dagger/*.csv`, `final/main.csv`, `n7/main_n7.csv`, `ladder_rerun/ladder_rerun*.csv`.

10 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| heuristic stock present in cell | 1 | 1 |
| heuristic stock | -1.23 | -1.226 |
| heuristic tuned present in cell | 1 | 1 |
| heuristic tuned | 2.26 | 2.261 |
| tuning gain present in cell | 1 | 1 |
| tuning gain | 3.49 | 3.488 |
| stock violations present in cell | 1 | 1 |
| stock violations | 2 813 | 2 813 |
| tuned violations present in cell | 1 | 1 |
| tuned violations | 4 339 | 4 338 |

### Table 2 — Controllers compared (`tab:controllers`)

Sources: `regen/regen_config.py`.

29 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| sindy_mpc_raw library | 1 | 1 |
| sindy_mpc_raw estimator | 1 | 1 |
| sindy_mpc_raw threshold | 0.05 | 0.05 |
| sindy_mpc_raw_ens library | 1 | 1 |
| sindy_mpc_raw_ens estimator | 1 | 1 |
| sindy_mpc_raw_ens threshold | 0.05 | 0.05 |
| sindy_mpc_conf library | 1 | 1 |
| sindy_mpc_conf estimator | 1 | 1 |
| sindy_mpc_conf threshold | 0.05 | 0.05 |
| sindy_mpc_phys library | 1 | 1 |
| sindy_mpc_phys estimator | 1 | 1 |
| sindy_mpc_phys threshold | 0.05 | 0.05 |
| sindy_mpc_phys_ens library | 1 | 1 |
| sindy_mpc_phys_ens estimator | 1 | 1 |
| sindy_mpc_phys_ens threshold | 0.05 | 0.05 |
| sindy_mpc_dense library | 1 | 1 |
| sindy_mpc_dense estimator | 1 | 1 |
| sindy_mpc_dense threshold | 0.001 | 0.001 |
| sindy_mpc_lowthr library | 1 | 1 |
| sindy_mpc_lowthr estimator | 1 | 1 |
| sindy_mpc_lowthr threshold | 1e-06 | 1e-06 |
| labels covered | 7 | 7 |
| MLP width 1 | 64 | 64 |
| MLP width 2 | 64 | 64 |
| planner candidate sequences | 48 | 48 |
| planner refinement iterations | 2 | 2 |
| planner elite fraction | 0.2 | 0.2 |
| shared horizon | 20 | 20 |
| solver-failure budget | 100 | 100 |

### Table 3 — Rule-based setpoint search (`tab:rbtune`)

Sources: `n2_tune/tune_rb_n2.csv`.

12 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| temp_setpoint_day hard-coded | 19.5 | 19.5 |
| temp_setpoint_day selected | 22.92 | 22.92 |
| temp_setpoint_night hard-coded | 16.5 | 16.5 |
| temp_setpoint_night selected | 14.38 | 14.38 |
| co2_day hard-coded | 800 | 800 |
| co2_day selected | 828.3 | 828.3 |
| lamp_rad_sum_limit hard-coded | 10 | 10 |
| lamp_rad_sum_limit selected | 7.62 | 7.616 |
| training J hard-coded | -1.936 | -1.936 |
| training J selected | 0.92 | 0.9202 |
| test J hard-coded | -1.226 | -1.226 |
| test J selected | 2.261 | 2.261 |

### Table 4 — Identification ladder, degree-1 configurations without denoising (`tab:ladder`)

Sources: `ladder_rerun/`.

36 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| all/raw kappa | 8.21 | 8.207 |
| all/raw kappa SD | 0.22 | 0.2247 |
| all/raw active terms | 12.95 | 12.95 |
| all/raw one-step RMSE | 2.137 | 2.137 |
| all/raw rollout median | 3.31 | 3.312 |
| all/raw rollout q25 | 2.67 | 2.669 |
| all/raw rollout q75 | 4.43 | 4.426 |
| all/raw diverged fraction | 0 | 0 |
| all/physics_no_cross kappa | 24.52 | 24.52 |
| all/physics_no_cross kappa SD | 0.94 | 0.9388 |
| all/physics_no_cross active terms | 18.66 | 18.66 |
| all/physics_no_cross one-step RMSE | 2.174 | 2.174 |
| all/physics_no_cross rollout median | 7.11 | 7.109 |
| all/physics_no_cross rollout q25 | 4.24 | 4.239 |
| all/physics_no_cross rollout q75 | 10.99 | 10.99 |
| all/physics_no_cross diverged fraction | 0.011 | 0.01104 |
| all/physics kappa | 53.43 | 53.43 |
| all/physics kappa SD | 2.4 | 2.397 |
| all/physics active terms | 26.74 | 26.74 |
| all/physics one-step RMSE | 2.022 | 2.022 |
| all/physics rollout median | 30.84 | 30.84 |
| all/physics rollout q25 | 24.08 | 24.08 |
| all/physics rollout q75 | 2 360 | 2 360 |
| all/physics diverged fraction | 0.13 | 0.13 |
| sparse/raw active terms | 20.05 | 20.05 |
| sparse/raw one-step RMSE | 1.862 | 1.862 |
| sparse/raw rollout median | 2.67 | 2.668 |
| sparse/raw diverged fraction | 0 | 0 |
| sparse/physics_no_cross active terms | 28.18 | 28.18 |
| sparse/physics_no_cross one-step RMSE | 1.728 | 1.728 |
| sparse/physics_no_cross rollout median | 10.58 | 10.58 |
| sparse/physics_no_cross diverged fraction | 0.0204 | 0.02042 |
| sparse/physics active terms | 36.98 | 36.98 |
| sparse/physics one-step RMSE | 1.675 | 1.675 |
| sparse/physics rollout median | 24.27 | 24.27 |
| sparse/physics diverged fraction | 0.0758 | 0.07583 |

### Table 5 — Tuning the rule-based reference under the reinforcement-learning agents' budget (16 random trials plus the hard-coded configuration as trial 0; selection on 2018–2019 only) (`tab:tune`)

Sources: `n2_tune/tune_rb_n2.csv`.

22 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| selected temp_setpoint_day | 22.92 | 22.92 |
| selected temp_setpoint_night | 14.38 | 14.38 |
| selected co2_day | 828.3 | 828.3 |
| selected lamp_rad_sum_limit | 7.62 | 7.616 |
| Hard-coded 2020 | 4.63 | 4.63 |
| Hard-coded 2021 | -6.98 | -6.985 |
| Hard-coded 2022 | 1.3 | 1.301 |
| Hard-coded 2023 | -3.85 | -3.852 |
| Hard-coded mean | -1.23 | -1.226 |
| Hard-coded violations | 2 813 | 2 813 |
| Tuned 2020 | 6.29 | 6.293 |
| Tuned 2021 | -1.99 | -1.991 |
| Tuned 2022 | 2.81 | 2.806 |
| Tuned 2023 | 1.94 | 1.937 |
| Tuned mean | 2.26 | 2.261 |
| Tuned violations | 4 339 | 4 338 |
| Gain 2020 | 1.66 | 1.663 |
| Gain 2021 | 4.99 | 4.994 |
| Gain 2022 | 1.5 | 1.505 |
| Gain 2023 | 5.79 | 5.79 |
| Gain mean | 3.49 | 3.488 |
| Gain violations | 1 526 | 1 526 |

### Table 6 — Four-season economic comparison, EPI in EUR m-2 (mean ± SD over runs; n runs = seeds × seasons) (`tab:main`)

Sources: `final/main.csv`, `n2_tune/tune_rb_n2.csv`, `phys_lib/`, `priced_dagger/`, `priced_main/`.

173 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| sindy_mpc_raw_ens 2020 mean | 9.1 | 9.101 |
| sindy_mpc_raw_ens 2020 SD | 0.36 | 0.359 |
| sindy_mpc_raw_ens 2021 mean | -1.56 | -1.556 |
| sindy_mpc_raw_ens 2021 SD | 0.58 | 0.5764 |
| sindy_mpc_raw_ens 2022 mean | 4.62 | 4.62 |
| sindy_mpc_raw_ens 2022 SD | 2.7 | 2.703 |
| sindy_mpc_raw_ens 2023 mean | 5.1 | 5.104 |
| sindy_mpc_raw_ens 2023 SD | 0.39 | 0.3911 |
| sindy_mpc_raw_ens four-season mean | 4.32 | 4.317 |
| sindy_mpc_raw_ens four-season SD | 4.08 | 4.076 |
| sindy_mpc_raw_ens n | 80 | 80 |
| sindy_mpc_raw_ens violation steps | 4 130 | 4 130 |
| sindy_mpc_raw 2020 mean | 8.4 | 8.4 |
| sindy_mpc_raw 2020 SD | 2.24 | 2.238 |
| sindy_mpc_raw 2021 mean | -1.71 | -1.708 |
| sindy_mpc_raw 2021 SD | 0.7 | 0.7021 |
| sindy_mpc_raw 2022 mean | 4.04 | 4.035 |
| sindy_mpc_raw 2022 SD | 3.4 | 3.398 |
| sindy_mpc_raw 2023 mean | 4.61 | 4.606 |
| sindy_mpc_raw 2023 SD | 1.59 | 1.591 |
| sindy_mpc_raw four-season mean | 3.83 | 3.833 |
| sindy_mpc_raw four-season SD | 4.23 | 4.233 |
| sindy_mpc_raw n | 80 | 80 |
| sindy_mpc_raw violation steps | 4 466 | 4 466 |
| sindy_mpc_lowthr 2020 mean | 6.58 | 6.577 |
| sindy_mpc_lowthr 2020 SD | 1.25 | 1.254 |
| sindy_mpc_lowthr 2021 mean | 0.27 | 0.2654 |
| sindy_mpc_lowthr 2021 SD | 1.73 | 1.728 |
| sindy_mpc_lowthr 2022 mean | 3.22 | 3.22 |
| sindy_mpc_lowthr 2022 SD | 1.35 | 1.353 |
| sindy_mpc_lowthr 2023 mean | 2.29 | 2.293 |
| sindy_mpc_lowthr 2023 SD | 1.48 | 1.482 |
| sindy_mpc_lowthr four-season mean | 3.09 | 3.089 |
| sindy_mpc_lowthr four-season SD | 2.71 | 2.707 |
| sindy_mpc_lowthr n | 80 | 80 |
| sindy_mpc_lowthr violation steps | 3 692 | 3 692 |
| sindy_mpc_dense 2020 mean | 6.58 | 6.575 |
| sindy_mpc_dense 2020 SD | 1.23 | 1.229 |
| sindy_mpc_dense 2021 mean | 0.25 | 0.2483 |
| sindy_mpc_dense 2021 SD | 1.71 | 1.709 |
| sindy_mpc_dense 2022 mean | 3.21 | 3.212 |
| sindy_mpc_dense 2022 SD | 1.34 | 1.339 |
| sindy_mpc_dense 2023 mean | 2.29 | 2.293 |
| sindy_mpc_dense 2023 SD | 1.45 | 1.452 |
| sindy_mpc_dense four-season mean | 3.08 | 3.082 |
| sindy_mpc_dense four-season SD | 2.7 | 2.7 |
| sindy_mpc_dense n | 80 | 80 |
| sindy_mpc_dense violation steps | 3 686 | 3 686 |
| sindy_mpc_phys_ens 2020 mean | 6.35 | 6.351 |
| sindy_mpc_phys_ens 2020 SD | 2.12 | 2.12 |
| sindy_mpc_phys_ens 2021 mean | -1.91 | -1.912 |
| sindy_mpc_phys_ens 2021 SD | 0.87 | 0.8655 |
| sindy_mpc_phys_ens 2022 mean | 3.07 | 3.071 |
| sindy_mpc_phys_ens 2022 SD | 2.34 | 2.34 |
| sindy_mpc_phys_ens 2023 mean | 3.51 | 3.506 |
| sindy_mpc_phys_ens 2023 SD | 1.44 | 1.443 |
| sindy_mpc_phys_ens four-season mean | 2.75 | 2.754 |
| sindy_mpc_phys_ens four-season SD | 3.47 | 3.469 |
| sindy_mpc_phys_ens n | 80 | 80 |
| sindy_mpc_phys_ens violation steps | 4 193 | 4 193 |
| sindy_mpc_phys 2020 mean | 5.82 | 5.819 |
| sindy_mpc_phys 2020 SD | 2.87 | 2.871 |
| sindy_mpc_phys 2021 mean | -2.02 | -2.016 |
| sindy_mpc_phys 2021 SD | 1.01 | 1.009 |
| sindy_mpc_phys 2022 mean | 2.89 | 2.886 |
| sindy_mpc_phys 2022 SD | 2.76 | 2.762 |
| sindy_mpc_phys 2023 mean | 3.22 | 3.215 |
| sindy_mpc_phys 2023 SD | 1.98 | 1.981 |
| sindy_mpc_phys four-season mean | 2.48 | 2.476 |
| sindy_mpc_phys four-season SD | 3.62 | 3.623 |
| sindy_mpc_phys n | 80 | 80 |
| sindy_mpc_phys violation steps | 4 174 | 4 174 |
| rule_based_tuned 2020 mean | 6.29 | 6.293 |
| rule_based_tuned 2021 mean | -1.99 | -1.991 |
| rule_based_tuned 2022 mean | 2.81 | 2.806 |
| rule_based_tuned 2023 mean | 1.94 | 1.937 |
| rule_based_tuned four-season mean | 2.26 | 2.261 |
| rule_based_tuned n | 4 | 4 |
| rule_based_tuned violation steps | 4 339 | 4 338 |
| sindy_mpc_conf_dagger 2020 mean | 4.56 | 4.56 |
| sindy_mpc_conf_dagger 2020 SD | 3.09 | 3.089 |
| sindy_mpc_conf_dagger 2021 mean | -1.73 | -1.732 |
| sindy_mpc_conf_dagger 2021 SD | 2.43 | 2.435 |
| sindy_mpc_conf_dagger 2022 mean | 2.23 | 2.227 |
| sindy_mpc_conf_dagger 2022 SD | 3.74 | 3.741 |
| sindy_mpc_conf_dagger 2023 mean | 1.57 | 1.572 |
| sindy_mpc_conf_dagger 2023 SD | 2.52 | 2.518 |
| sindy_mpc_conf_dagger four-season mean | 1.66 | 1.657 |
| sindy_mpc_conf_dagger four-season SD | 3.71 | 3.706 |
| sindy_mpc_conf_dagger n | 80 | 80 |
| sindy_mpc_conf_dagger violation steps | 4 138 | 4 138 |
| sindy_mpc_dense_dagger 2020 mean | 4.74 | 4.736 |
| sindy_mpc_dense_dagger 2020 SD | 2.59 | 2.585 |
| sindy_mpc_dense_dagger 2021 mean | -1.59 | -1.587 |
| sindy_mpc_dense_dagger 2021 SD | 1.09 | 1.094 |
| sindy_mpc_dense_dagger 2022 mean | 1.7 | 1.699 |
| sindy_mpc_dense_dagger 2022 SD | 1.78 | 1.785 |
| sindy_mpc_dense_dagger 2023 mean | 0.63 | 0.6295 |
| sindy_mpc_dense_dagger 2023 SD | 1.37 | 1.369 |
| sindy_mpc_dense_dagger four-season mean | 1.37 | 1.369 |
| sindy_mpc_dense_dagger four-season SD | 2.89 | 2.891 |
| sindy_mpc_dense_dagger n | 80 | 80 |
| sindy_mpc_dense_dagger violation steps | 3 615 | 3 615 |
| ppo 2020 mean | 3.36 | 3.355 |
| ppo 2020 SD | 1.59 | 1.592 |
| ppo 2021 mean | -2.1 | -2.097 |
| ppo 2021 SD | 1.03 | 1.029 |
| ppo 2022 mean | 1.72 | 1.724 |
| ppo 2022 SD | 1.19 | 1.19 |
| ppo 2023 mean | -1.17 | -1.167 |
| ppo 2023 SD | 3.4 | 3.402 |
| ppo four-season mean | 0.45 | 0.4537 |
| ppo four-season SD | 2.97 | 2.973 |
| ppo n | 80 | 80 |
| ppo violation steps | 1 330 | 1 330 |
| sindy_mpc_conf 2020 mean | 3.88 | 3.882 |
| sindy_mpc_conf 2020 SD | 4.23 | 4.232 |
| sindy_mpc_conf 2021 mean | -3.16 | -3.161 |
| sindy_mpc_conf 2021 SD | 1.34 | 1.34 |
| sindy_mpc_conf 2022 mean | -0.31 | -0.3116 |
| sindy_mpc_conf 2022 SD | 3.42 | 3.421 |
| sindy_mpc_conf 2023 mean | 0.72 | 0.7177 |
| sindy_mpc_conf 2023 SD | 3.46 | 3.464 |
| sindy_mpc_conf four-season mean | 0.28 | 0.2818 |
| sindy_mpc_conf four-season SD | 4.11 | 4.106 |
| sindy_mpc_conf n | 80 | 80 |
| sindy_mpc_conf violation steps | 4 755 | 4 755 |
| rule_based 2020 mean | 4.63 | 4.634 |
| rule_based 2020 SD | 0 | 0 |
| rule_based 2021 mean | -6.97 | -6.971 |
| rule_based 2021 SD | 0 | 9.11e-16 |
| rule_based 2022 mean | 1.33 | 1.328 |
| rule_based 2022 SD | 0 | 2.28e-16 |
| rule_based 2023 mean | -3.81 | -3.814 |
| rule_based 2023 SD | 0 | 4.56e-16 |
| rule_based four-season mean | -1.21 | -1.206 |
| rule_based four-season SD | 4.52 | 4.516 |
| rule_based n | 80 | 80 |
| rule_based violation steps | 2 810 | 2 810 |
| oracle_mpc 2020 mean | 2.77 | 2.765 |
| oracle_mpc 2020 SD | 0.08 | 0.07529 |
| oracle_mpc 2021 mean | -6.76 | -6.757 |
| oracle_mpc 2021 SD | 0.09 | 0.08709 |
| oracle_mpc 2023 mean | -3.95 | -3.953 |
| oracle_mpc 2023 SD | 0.06 | 0.06323 |
| oracle_mpc four-season mean | -2.65 | -2.648 |
| oracle_mpc four-season SD | 4.03 | 4.03 |
| oracle_mpc n | 60 | 60 |
| oracle_mpc violation steps | 3 321 | 3 321 |
| nn_mpc 2020 mean | -1.78 | -1.777 |
| nn_mpc 2020 SD | 1.95 | 1.946 |
| nn_mpc 2021 mean | -5.94 | -5.938 |
| nn_mpc 2021 SD | 1.99 | 1.994 |
| nn_mpc 2022 mean | -4.63 | -4.628 |
| nn_mpc 2022 SD | 1.82 | 1.82 |
| nn_mpc 2023 mean | -2.93 | -2.931 |
| nn_mpc 2023 SD | 1.73 | 1.728 |
| nn_mpc four-season mean | -3.82 | -3.818 |
| nn_mpc four-season SD | 2.42 | 2.416 |
| nn_mpc n | 40 | 40 |
| nn_mpc violation steps | 2 818 | 2 818 |
| sac 2020 mean | -2.43 | -2.43 |
| sac 2020 SD | 1.33 | 1.326 |
| sac 2021 mean | -6.13 | -6.134 |
| sac 2021 SD | 1.47 | 1.468 |
| sac 2022 mean | -2.99 | -2.987 |
| sac 2022 SD | 1.61 | 1.615 |
| sac 2023 mean | -5.05 | -5.049 |
| sac 2023 SD | 1.2 | 1.204 |
| sac four-season mean | -4.15 | -4.15 |
| sac four-season SD | 2.05 | 2.052 |
| sac n | 80 | 80 |
| sac violation steps | 1 689 | 1 689 |

### Table 7 — Comparison against the tuned rule-based reference (priced objective) (`tab:wilcoxon`)

Sources: `priced_main/*.csv`, `priced_dagger/*.csv`, `phys_lib/main_physlib.csv`, `final/main.csv`, `n2_tune/tune_rb_n2.csv`.

112 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| sindy_mpc_raw_ens seed-level wins | 19 | 19 |
| sindy_mpc_raw_ens seeds | 20 | 20 |
| sindy_mpc_raw_ens seed-level p_Holm | 7.4e-05 | 7.44e-05 |
| sindy_mpc_raw_ens delta mean | 2.06 | 2.056 |
| sindy_mpc_raw_ens delta median | 2.85 | 2.846 |
| sindy_mpc_raw_ens wins | 75 | 75 |
| sindy_mpc_raw_ens n | 80 | 80 |
| sindy_mpc_raw_ens p_Holm | 8.3e-11 | 8.34e-11 |
| sindy_mpc_raw seed-level wins | 17 | 17 |
| sindy_mpc_raw seeds | 20 | 20 |
| sindy_mpc_raw seed-level p_Holm | 0.044 | 0.04374 |
| sindy_mpc_raw delta mean | 1.57 | 1.572 |
| sindy_mpc_raw delta median | 2.83 | 2.828 |
| sindy_mpc_raw wins | 68 | 68 |
| sindy_mpc_raw n | 80 | 80 |
| sindy_mpc_raw p_Holm | 6.5e-07 | 6.48e-07 |
| sindy_mpc_lowthr seed-level wins | 13 | 13 |
| sindy_mpc_lowthr seeds | 20 | 20 |
| sindy_mpc_lowthr seed-level p_Holm | 0.103 | 0.1031 |
| sindy_mpc_lowthr delta mean | 0.83 | 0.8275 |
| sindy_mpc_lowthr delta median | 0.74 | 0.7396 |
| sindy_mpc_lowthr wins | 51 | 51 |
| sindy_mpc_lowthr n | 80 | 80 |
| sindy_mpc_lowthr p_Holm | 0.0007 | 0.000705 |
| sindy_mpc_dense seed-level wins | 13 | 13 |
| sindy_mpc_dense seeds | 20 | 20 |
| sindy_mpc_dense seed-level p_Holm | 0.103 | 0.1031 |
| sindy_mpc_dense delta mean | 0.82 | 0.8209 |
| sindy_mpc_dense delta median | 0.69 | 0.6868 |
| sindy_mpc_dense wins | 51 | 51 |
| sindy_mpc_dense n | 80 | 80 |
| sindy_mpc_dense p_Holm | 0.0007 | 0.000705 |
| sindy_mpc_phys_ens seed-level wins | 14 | 14 |
| sindy_mpc_phys_ens seeds | 20 | 20 |
| sindy_mpc_phys_ens seed-level p_Holm | 0.53 | 0.5309 |
| sindy_mpc_phys_ens delta mean | 0.49 | 0.4927 |
| sindy_mpc_phys_ens delta median | 0.25 | 0.2518 |
| sindy_mpc_phys_ens wins | 41 | 41 |
| sindy_mpc_phys_ens n | 80 | 80 |
| sindy_mpc_phys_ens p_Holm | 0.176 | 0.1759 |
| sindy_mpc_phys seed-level wins | 13 | 13 |
| sindy_mpc_phys seeds | 20 | 20 |
| sindy_mpc_phys seed-level p_Holm | 0.94 | 0.9354 |
| sindy_mpc_phys delta mean | 0.21 | 0.2148 |
| sindy_mpc_phys delta median | 0.29 | 0.2925 |
| sindy_mpc_phys wins | 44 | 44 |
| sindy_mpc_phys n | 80 | 80 |
| sindy_mpc_phys p_Holm | 0.334 | 0.3339 |
| sindy_mpc_conf_dagger seed-level wins | 9 | 9 |
| sindy_mpc_conf_dagger seeds | 20 | 20 |
| sindy_mpc_conf_dagger seed-level p_Holm | 0.94 | 0.9354 |
| sindy_mpc_conf_dagger delta mean | -0.6 | -0.6047 |
| sindy_mpc_conf_dagger delta median | -0.84 | -0.8358 |
| sindy_mpc_conf_dagger wins | 31 | 31 |
| sindy_mpc_conf_dagger n | 80 | 80 |
| sindy_mpc_conf_dagger p_Holm | 0.334 | 0.3339 |
| sindy_mpc_dense_dagger seed-level wins | 5 | 5 |
| sindy_mpc_dense_dagger seeds | 20 | 20 |
| sindy_mpc_dense_dagger seed-level p_Holm | 0.075 | 0.07482 |
| sindy_mpc_dense_dagger delta mean | -0.89 | -0.892 |
| sindy_mpc_dense_dagger delta median | -0.79 | -0.7908 |
| sindy_mpc_dense_dagger wins | 23 | 23 |
| sindy_mpc_dense_dagger n | 80 | 80 |
| sindy_mpc_dense_dagger p_Holm | 0.00012 | 0.000124 |
| ppo seed-level wins | 1 | 1 |
| ppo seeds | 20 | 20 |
| ppo seed-level p_Holm | 0.00011 | 0.000105 |
| ppo delta mean | -1.81 | -1.808 |
| ppo delta median | -1.78 | -1.776 |
| ppo wins | 11 | 11 |
| ppo n | 80 | 80 |
| ppo p_Holm | 2.3e-10 | 2.29e-10 |
| sindy_mpc_conf seed-level wins | 7 | 7 |
| sindy_mpc_conf seeds | 20 | 20 |
| sindy_mpc_conf seed-level p_Holm | 0.058 | 0.05836 |
| sindy_mpc_conf delta mean | -1.98 | -1.98 |
| sindy_mpc_conf delta median | -1.91 | -1.914 |
| sindy_mpc_conf wins | 29 | 29 |
| sindy_mpc_conf n | 80 | 80 |
| sindy_mpc_conf p_Holm | 6.8e-05 | 6.84e-05 |
| rule_based seed-level wins | 0 | 0 |
| rule_based seeds | 20 | 20 |
| rule_based seed-level p_Holm | 9.3e-05 | 9.29e-05 |
| rule_based delta mean | -3.47 | -3.467 |
| rule_based delta median | -3.32 | -3.32 |
| rule_based wins | 0 | 0 |
| rule_based n | 80 | 80 |
| rule_based p_Holm | 7.3e-14 | 7.31e-14 |
| oracle_mpc seed-level wins | 0 | 0 |
| oracle_mpc seeds | 20 | 20 |
| oracle_mpc seed-level p_Holm | 2.9e-05 | 2.86e-05 |
| oracle_mpc delta mean | -4.73 | -4.728 |
| oracle_mpc delta median | -4.79 | -4.788 |
| oracle_mpc wins | 0 | 0 |
| oracle_mpc n | 60 | 60 |
| oracle_mpc p_Holm | 1.8e-10 | 1.79e-10 |
| nn_mpc seed-level wins | 0 | 0 |
| nn_mpc seeds | 10 | 10 |
| nn_mpc seed-level p_Holm | 0.02 | 0.01953 |
| nn_mpc delta mean | -6.08 | -6.08 |
| nn_mpc delta median | -5.52 | -5.524 |
| nn_mpc wins | 0 | 0 |
| nn_mpc n | 40 | 40 |
| nn_mpc p_Holm | 2.4e-11 | 2.36e-11 |
| sac seed-level wins | 0 | 0 |
| sac seeds | 20 | 20 |
| sac seed-level p_Holm | 2.9e-05 | 2.86e-05 |
| sac delta mean | -6.41 | -6.411 |
| sac delta median | -6.68 | -6.675 |
| sac wins | 0 | 0 |
| sac n | 80 | 80 |
| sac p_Holm | 1.1e-13 | 1.1e-13 |

### Table 8 — Four seasons never used at any stage, default objective, 8 seeds (`tab:unseen`)

Sources: `n5_years/main_n5.csv`.

28 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| sindy_mpc_raw_ens 2014 | 7.08 | 7.08 |
| sindy_mpc_raw_ens 2015 | 6.25 | 6.25 |
| sindy_mpc_raw_ens 2016 | 5.98 | 5.978 |
| sindy_mpc_raw_ens 2017 | 6.38 | 6.38 |
| sindy_mpc_raw_ens mean | 6.42 | 6.422 |
| sindy_mpc_raw_ens SD | 0.95 | 0.9516 |
| sindy_mpc_raw_ens violations | 4 385 | 4 385 |
| sindy_mpc_conf 2014 | 3.06 | 3.057 |
| sindy_mpc_conf 2015 | 1.7 | 1.703 |
| sindy_mpc_conf 2016 | 2.18 | 2.176 |
| sindy_mpc_conf 2017 | 2.57 | 2.566 |
| sindy_mpc_conf mean | 2.38 | 2.375 |
| sindy_mpc_conf SD | 4.03 | 4.032 |
| sindy_mpc_conf violations | 5 458 | 5 458 |
| sindy_mpc_dense 2014 | 1.63 | 1.63 |
| sindy_mpc_dense 2015 | 0.54 | 0.5445 |
| sindy_mpc_dense 2016 | 0.84 | 0.8409 |
| sindy_mpc_dense 2017 | 1.27 | 1.269 |
| sindy_mpc_dense mean | 1.07 | 1.071 |
| sindy_mpc_dense SD | 1.74 | 1.742 |
| sindy_mpc_dense violations | 6 226 | 6 226 |
| rule_based 2014 | 0.99 | 0.9861 |
| rule_based 2015 | -1.13 | -1.126 |
| rule_based 2016 | -2.22 | -2.222 |
| rule_based 2017 | 1.05 | 1.053 |
| rule_based mean | -0.33 | -0.3271 |
| rule_based SD | 1.42 | 1.424 |
| rule_based violations | 2 624 | 2 624 |

### Table 9 — One-factor library comparison (`tab:survival3`)

Sources: `ladder_rerun/`, `notuboil/`, `phys_lib/`, `priced_dagger/`, `priced_main/`.

45 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| ensemble/raw kappa | 8.21 | 8.207 |
| ensemble/raw rollout median | 2.67 | 2.665 |
| ensemble/raw diverged fraction | 0 | 0 |
| ensemble/raw survival | 0.55 | 0.55 |
| ensemble/raw EPI | 4.32 | 4.317 |
| ensemble/raw EPI SD | 4.08 | 4.076 |
| ensemble/physics_no_cross kappa | 24.52 | 24.52 |
| ensemble/physics_no_cross rollout median | 10.99 | 10.99 |
| ensemble/physics_no_cross diverged fraction | 0.0208 | 0.02083 |
| ensemble/physics_no_cross survival | 0.15 | 0.15 |
| ensemble/physics_no_cross EPI | 0.28 | 0.2818 |
| ensemble/physics_no_cross EPI SD | 4.11 | 4.106 |
| ensemble/physics kappa | 53.43 | 53.43 |
| ensemble/physics rollout median | 24.27 | 24.27 |
| ensemble/physics diverged fraction | 0.0767 | 0.07667 |
| ensemble/physics survival | 0.55 | 0.55 |
| ensemble/physics EPI | 2.75 | 2.754 |
| ensemble/physics EPI SD | 3.47 | 3.469 |
| ensemble/physics_no_tuboil kappa | 52.28 | 52.28 |
| ensemble/physics_no_tuboil rollout median | 24.17 | 24.17 |
| ensemble/physics_no_tuboil diverged fraction | 0.0842 | 0.08417 |
| ensemble/physics_no_tuboil survival | 0.4 | 0.4 |
| ensemble/physics_no_tuboil EPI | 2.11 | 2.113 |
| ensemble/physics_no_tuboil EPI SD | 3.51 | 3.506 |
| stlsq/raw kappa | 8.21 | 8.207 |
| stlsq/raw rollout median | 2.67 | 2.675 |
| stlsq/raw diverged fraction | 0 | 0 |
| stlsq/raw survival | 0.5 | 0.5 |
| stlsq/raw EPI | 3.83 | 3.833 |
| stlsq/raw EPI SD | 4.23 | 4.233 |
| stlsq/physics_no_cross kappa | 24.52 | 24.52 |
| stlsq/physics_no_cross rollout median | 10.45 | 10.45 |
| stlsq/physics_no_cross diverged fraction | 0.02 | 0.02 |
| stlsq/physics kappa | 53.43 | 53.43 |
| stlsq/physics rollout median | 24.49 | 24.49 |
| stlsq/physics diverged fraction | 0.075 | 0.075 |
| stlsq/physics survival | 0.55 | 0.55 |
| stlsq/physics EPI | 2.48 | 2.476 |
| stlsq/physics EPI SD | 3.62 | 3.623 |
| stlsq/physics_no_tuboil kappa | 52.28 | 52.28 |
| stlsq/physics_no_tuboil rollout median | 23.58 | 23.58 |
| stlsq/physics_no_tuboil diverged fraction | 0.0783 | 0.07833 |
| stlsq/physics_no_tuboil survival | 0.4 | 0.4 |
| stlsq/physics_no_tuboil EPI | 2.28 | 2.283 |
| stlsq/physics_no_tuboil EPI SD | 3.55 | 3.552 |

### Table 10 — Sparsity sweep within the physics_no_cross library, season 2020, 20 seeds per level (`tab:lambda`)

Sources: `final/mechanism*.csv`, `priced_mech/`.

96 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| cells compared across the two waves | 260 | 260 |
| cells differing on active terms | 28 | 28 |
| largest term difference | 2 | 2 |
| largest level-mean difference | 0.15 | 0.15 |
| cells whose boiler survival flips | 1 | 1 |
| lambda=10^{-6} active terms | 53.95 | 53.95 |
| lambda=10^{-6} survival | 1 | 1 |
| lambda=10^{-6} EPI priced | 6.58 | 6.577 |
| lambda=10^{-6} SD priced | 1.25 | 1.254 |
| lambda=10^{-6} EPI original | 3.68 | 3.677 |
| lambda=10^{-6} SD original | 1.85 | 1.854 |
| lambda=10^{-6} delta | 2.9 | 2.9 |
| lambda=10^{-3} active terms | 49.6 | 49.6 |
| lambda=10^{-3} survival | 1 | 1 |
| lambda=10^{-3} EPI priced | 6.58 | 6.575 |
| lambda=10^{-3} SD priced | 1.23 | 1.229 |
| lambda=10^{-3} EPI original | 3.63 | 3.628 |
| lambda=10^{-3} SD original | 1.93 | 1.926 |
| lambda=10^{-3} delta | 2.95 | 2.95 |
| lambda=0.01 active terms | 42.65 | 42.65 |
| lambda=0.01 survival | 1 | 1 |
| lambda=0.01 EPI priced | 6.11 | 6.107 |
| lambda=0.01 SD priced | 2.52 | 2.517 |
| lambda=0.01 EPI original | 3.21 | 3.205 |
| lambda=0.01 SD original | 3.25 | 3.249 |
| lambda=0.01 delta | 2.9 | 2.9 |
| lambda=0.02 active terms | 38.8 | 38.8 |
| lambda=0.02 survival | 1 | 1 |
| lambda=0.02 EPI priced | 6.38 | 6.376 |
| lambda=0.02 SD priced | 2 | 2.005 |
| lambda=0.02 EPI original | 4.39 | 4.391 |
| lambda=0.02 SD original | 1.46 | 1.465 |
| lambda=0.02 delta | 1.99 | 1.99 |
| lambda=0.03 active terms | 36.1 | 36.1 |
| lambda=0.03 survival | 0.95 | 0.95 |
| lambda=0.03 EPI priced | 6.41 | 6.414 |
| lambda=0.03 SD priced | 1.82 | 1.822 |
| lambda=0.03 EPI original | 4.98 | 4.984 |
| lambda=0.03 SD original | 1.76 | 1.756 |
| lambda=0.03 delta | 1.43 | 1.43 |
| lambda=0.04 active terms | 32.15 | 32.15 |
| lambda=0.04 survival | 0.35 | 0.35 |
| lambda=0.04 EPI priced | 4.3 | 4.302 |
| lambda=0.04 SD priced | 3.51 | 3.505 |
| lambda=0.04 EPI original | 2.76 | 2.76 |
| lambda=0.04 SD original | 3.84 | 3.843 |
| lambda=0.04 delta | 1.54 | 1.54 |
| lambda=0.05 active terms | 28.1 | 28.1 |
| lambda=0.05 survival | 0.1 | 0.1 |
| lambda=0.05 EPI priced | 4.04 | 4.039 |
| lambda=0.05 SD priced | 4.14 | 4.139 |
| lambda=0.05 EPI original | 1.59 | 1.588 |
| lambda=0.05 SD original | 5.59 | 5.588 |
| lambda=0.05 delta | 2.45 | 2.45 |
| lambda=0.06 active terms | 25.45 | 25.45 |
| lambda=0.06 survival | 0 | 0 |
| lambda=0.06 EPI priced | 3.59 | 3.592 |
| lambda=0.06 SD priced | 2.96 | 2.964 |
| lambda=0.06 EPI original | 2.58 | 2.579 |
| lambda=0.06 SD original | 4.63 | 4.631 |
| lambda=0.06 delta | 1.01 | 1.01 |
| lambda=0.07 active terms | 23.05 | 23.05 |
| lambda=0.07 survival | 0 | 0 |
| lambda=0.07 EPI priced | 4.01 | 4.01 |
| lambda=0.07 SD priced | 2.37 | 2.368 |
| lambda=0.07 EPI original | 3.67 | 3.673 |
| lambda=0.07 SD original | 2.62 | 2.62 |
| lambda=0.07 delta | 0.34 | 0.34 |
| lambda=0.08 active terms | 21.3 | 21.3 |
| lambda=0.08 survival | 0 | 0 |
| lambda=0.08 EPI priced | 3.04 | 3.037 |
| lambda=0.08 SD priced | 1.09 | 1.091 |
| lambda=0.08 EPI original | 2.49 | 2.485 |
| lambda=0.08 SD original | 1.23 | 1.229 |
| lambda=0.08 delta | 0.55 | 0.55 |
| lambda=0.10 active terms | 19.5 | 19.5 |
| lambda=0.10 survival | 0 | 0 |
| lambda=0.10 EPI priced | 3.11 | 3.113 |
| lambda=0.10 SD priced | 0.36 | 0.3639 |
| lambda=0.10 EPI original | 2.5 | 2.504 |
| lambda=0.10 SD original | 0.34 | 0.337 |
| lambda=0.10 delta | 0.61 | 0.61 |
| lambda=0.15 active terms | 14.4 | 14.4 |
| lambda=0.15 survival | 0 | 0 |
| lambda=0.15 EPI priced | 4.61 | 4.606 |
| lambda=0.15 SD priced | 0.93 | 0.9308 |
| lambda=0.15 EPI original | 4.05 | 4.051 |
| lambda=0.15 SD original | 0.99 | 0.9868 |
| lambda=0.15 delta | 0.56 | 0.56 |
| lambda=0.20 active terms | 12.15 | 12.15 |
| lambda=0.20 survival | 0 | 0 |
| lambda=0.20 EPI priced | 2.43 | 2.433 |
| lambda=0.20 SD priced | 2.49 | 2.49 |
| lambda=0.20 EPI original | 1.34 | 1.339 |
| lambda=0.20 SD original | 3.05 | 3.049 |
| lambda=0.20 delta | 1.09 | 1.09 |

### Table 11 — Mean EPI (EUR m-2) by feature library and boiler-term survival, pooled over the nine SINDy-MPC controllers and four test seasons; run counts in parentheses (`tab:twobytwo`)

Sources: `final/main.csv`, `n7/main_n7.csv`, `phys_lib/`.

26 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| raw/original/dropped | 3.2 | 3.202 |
| raw/original/dropped n | 76 | 76 |
| raw/original/kept | 4.43 | 4.427 |
| raw/original/kept n | 84 | 84 |
| raw/priced/dropped | 3.48 | 3.483 |
| raw/priced/dropped n | 76 | 76 |
| raw/priced/kept | 4.61 | 4.611 |
| raw/priced/kept n | 84 | 84 |
| physics_no_cross/original/dropped | -1.42 | -1.421 |
| physics_no_cross/original/dropped n | 88 | 88 |
| physics_no_cross/original/kept | 0.15 | 0.1485 |
| physics_no_cross/original/kept n | 312 | 312 |
| physics_no_cross/priced/dropped | 0.02 | 0.01989 |
| physics_no_cross/priced/dropped n | 80 | 80 |
| physics_no_cross/priced/kept | 2.36 | 2.365 |
| physics_no_cross/priced/kept n | 320 | 320 |
| physics/priced/dropped | 2.74 | 2.736 |
| physics/priced/dropped n | 72 | 72 |
| physics/priced/kept | 2.52 | 2.516 |
| physics/priced/kept n | 88 | 88 |
| raw - physics_no_cross (original, dropped) | 4.62 | 4.623 |
| raw - physics_no_cross (original, kept) | 4.28 | 4.279 |
| raw - physics_no_cross (priced, dropped) | 3.46 | 3.463 |
| raw - physics_no_cross (priced, kept) | 2.25 | 2.246 |
| raw - physics (priced, dropped) | 0.75 | 0.7472 |
| raw - physics (priced, kept) | 2.09 | 2.095 |

### Table 12 — Fault injection with and without the residual-based supervisor, season 2020, 20 seeds (`tab:faults`)

Sources: `final/tables/faults.csv`.

44 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| uVent_dead raw mean | -18.19 | -18.19 |
| uVent_dead raw SD | 5.48 | 5.476 |
| uVent_dead sup mean | 0.1 | 0.0976 |
| uVent_dead sup SD | 0.3 | 0.3031 |
| uVent_dead delta | 18.28 | 18.28 |
| uVent_dead n | 20 | 20 |
| uVent_dead vs fault-free | -3.53 | -3.531 |
| uBoil_stuck raw mean | -8.41 | -8.41 |
| uBoil_stuck raw SD | 5.35 | 5.352 |
| uBoil_stuck sup mean | -3.88 | -3.875 |
| uBoil_stuck sup SD | 0.29 | 0.2915 |
| uBoil_stuck delta | 4.53 | 4.535 |
| uBoil_stuck n | 20 | 20 |
| uBoil_stuck vs fault-free | -7.5 | -7.503 |
| rh_offset raw mean | 1.27 | 1.266 |
| rh_offset raw SD | 3.72 | 3.723 |
| rh_offset sup mean | 4.45 | 4.453 |
| rh_offset sup SD | 0.36 | 0.3559 |
| rh_offset delta | 3.19 | 3.188 |
| rh_offset n | 20 | 20 |
| rh_offset vs fault-free | 0.83 | 0.8252 |
| uLamp_dead raw mean | 3.5 | 3.502 |
| uLamp_dead raw SD | 1.64 | 1.637 |
| uLamp_dead sup mean | 6.33 | 6.325 |
| uLamp_dead sup SD | 0.29 | 0.2851 |
| uLamp_dead delta | 2.82 | 2.824 |
| uLamp_dead n | 20 | 20 |
| uLamp_dead vs fault-free | 2.7 | 2.697 |
| t_in_stuck raw mean | 3.06 | 3.059 |
| t_in_stuck raw SD | 1.18 | 1.179 |
| t_in_stuck sup mean | 4.42 | 4.416 |
| t_in_stuck sup SD | 0.29 | 0.2903 |
| t_in_stuck delta | 1.36 | 1.357 |
| t_in_stuck n | 20 | 20 |
| t_in_stuck vs fault-free | 0.79 | 0.7878 |
| t_in_offset raw mean | 3.67 | 3.669 |
| t_in_offset raw SD | 1.16 | 1.162 |
| t_in_offset sup mean | 4.47 | 4.471 |
| t_in_offset sup SD | 0.39 | 0.3864 |
| t_in_offset delta | 0.8 | 0.802 |
| t_in_offset n | 20 | 20 |
| t_in_offset vs fault-free | 0.84 | 0.8432 |
| fault-free reference | 3.63 | 3.628 |
| fault-free SD | 1.93 | 1.926 |

### Table 13 — Coefficient-perturbation sensitivity of a single SINDy-MPC controller, season 2020, 10 seeds × 4 repetitions, default objective (`tab:sens`)

Sources: `priced_design/design_pricedDesign*.csv`.

32 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| 0.02 mean | 4.11 | 4.11 |
| 0.02 SD | 1.29 | 1.292 |
| 0.02 median | 4.47 | 4.468 |
| 0.02 min | 1.25 | 1.252 |
| 0.02 early terminations | 0 | 0 |
| 0.02 n | 40 | 40 |
| 0.05 mean | 4.03 | 4.029 |
| 0.05 SD | 2.06 | 2.06 |
| 0.05 median | 4.35 | 4.349 |
| 0.05 min | -1.19 | -1.187 |
| 0.05 early terminations | 0 | 0 |
| 0.05 n | 40 | 40 |
| 0.1 mean | 2.96 | 2.96 |
| 0.1 SD | 7.57 | 7.57 |
| 0.1 median | 5.4 | 5.401 |
| 0.1 min | -34.18 | -34.18 |
| 0.1 early terminations | 0 | 0 |
| 0.1 n | 40 | 40 |
| 0.15 mean | -3.86 | -3.863 |
| 0.15 SD | 14.27 | 14.27 |
| 0.15 median | 1.12 | 1.121 |
| 0.15 min | -42.87 | -42.87 |
| 0.15 early terminations | 4 | 4 |
| 0.15 n | 40 | 40 |
| 0.2 mean | -8.12 | -8.125 |
| 0.2 SD | 18.39 | 18.39 |
| 0.2 median | -0.31 | -0.3141 |
| 0.2 min | -42.16 | -42.16 |
| 0.2 early terminations | 12 | 12 |
| 0.2 n | 40 | 40 |
| span of means | 12.24 | 12.24 |
| span of medians | 5.72 | 5.715 |

### Table 14 — The selection reversal, measured on the held-out identification block (`tab:disc-libraries`)

Sources: `holdout/holdout_holdout.csv`.

54 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| in/raw features | 11 | 11 |
| in/raw kappa | 8.2 | 8.212 |
| in/raw terms | 20.6 | 20.57 |
| in/raw one-step | 1.84 | 1.839 |
| in/raw rollout median | 2.62 | 2.617 |
| in/raw rollout q25 | 2.53 | 2.535 |
| in/raw rollout q75 | 2.8 | 2.8 |
| in/raw diverged | 0 | 0 |
| in/raw n | 40 | 40 |
| in/physics_no_cross features | 14 | 14 |
| in/physics_no_cross kappa | 25.4 | 25.4 |
| in/physics_no_cross terms | 29.7 | 29.73 |
| in/physics_no_cross one-step | 1.69 | 1.691 |
| in/physics_no_cross rollout median | 12.14 | 12.14 |
| in/physics_no_cross rollout q25 | 2.88 | 2.885 |
| in/physics_no_cross rollout q75 | 14.1 | 14.1 |
| in/physics_no_cross diverged | 0.021 | 0.02083 |
| in/physics_no_cross n | 40 | 40 |
| in/physics features | 18 | 18 |
| in/physics kappa | 56.2 | 56.16 |
| in/physics terms | 36.6 | 36.58 |
| in/physics one-step | 1.64 | 1.64 |
| in/physics rollout median | 21.88 | 21.88 |
| in/physics rollout q25 | 18.06 | 18.06 |
| in/physics rollout q75 | 25.58 | 25.58 |
| in/physics diverged | 0.078 | 0.07792 |
| in/physics n | 40 | 40 |
| out/raw features | 11 | 11 |
| out/raw kappa | 8.2 | 8.212 |
| out/raw terms | 20.6 | 20.57 |
| out/raw one-step | 1.89 | 1.895 |
| out/raw rollout median | 2.72 | 2.722 |
| out/raw rollout q25 | 2.63 | 2.632 |
| out/raw rollout q75 | 2.84 | 2.843 |
| out/raw diverged | 0 | 0 |
| out/raw n | 40 | 40 |
| out/physics_no_cross features | 14 | 14 |
| out/physics_no_cross kappa | 25.4 | 25.4 |
| out/physics_no_cross terms | 29.7 | 29.73 |
| out/physics_no_cross one-step | 1.82 | 1.819 |
| out/physics_no_cross rollout median | 15.42 | 15.42 |
| out/physics_no_cross rollout q25 | 2.69 | 2.689 |
| out/physics_no_cross rollout q75 | 21.13 | 21.13 |
| out/physics_no_cross diverged | 0.046 | 0.04625 |
| out/physics_no_cross n | 40 | 40 |
| out/physics features | 18 | 18 |
| out/physics kappa | 56.2 | 56.16 |
| out/physics terms | 36.6 | 36.58 |
| out/physics one-step | 1.76 | 1.765 |
| out/physics rollout median | 21.57 | 21.57 |
| out/physics rollout q25 | 15.56 | 15.56 |
| out/physics rollout q75 | 31.74 | 31.74 |
| out/physics diverged | 0.086 | 0.08583 |
| out/physics n | 40 | 40 |

### Table 15 — Sensitivity of the headline comparison to two benchmarking safeguards (`tab:disc-defects`)

Sources: `n2_tune/tune_rb_n2.csv`, `priced_main/*.csv`, `priced_dagger/*.csv`, `final/main.csv`, `n7/main_n7.csv`.

10 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| heuristic stock present | 1 | 1 |
| heuristic stock | -1.23 | -1.226 |
| heuristic tuned present | 1 | 1 |
| heuristic tuned | 2.26 | 2.261 |
| tuning gain present | 1 | 1 |
| tuning gain | 3.49 | 3.488 |
| raw over stock heuristic present | 1 | 1 |
| raw over stock heuristic | 5.54 | 5.544 |
| raw over tuned heuristic present | 1 | 1 |
| raw over tuned heuristic | 2.06 | 2.056 |

### Table 16 — Headline quantities of the study and the result files they are read from (`tab:headline`)

Sources: `design_priced_real/design_designPriced.csv`, `final/main.csv`, `ladder_rerun/ladder_rerun*.csv`, `n2_tune/tune_rb_n2.csv`, `n5_years/main_n5.csv`, `n7/main_n7.csv`, `phys_lib/main_physlib.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`, `priced_mech/mechanism_pricedMech*.csv`.

39 cells verified.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| one-step RMSE [raw] | 1.86 | 1.862 |
| one-step RMSE [physics_no_cross] | 1.73 | 1.728 |
| one-step RMSE [physics] | 1.68 | 1.675 |
| rollout median [raw] | 2.67 | 2.668 |
| rollout median [physics_no_cross] | 10.58 | 10.58 |
| rollout median [physics] | 24.27 | 24.27 |
| divergence [raw] | 0 | 0 |
| divergence [physics_no_cross] | 0.02 | 0.02042 |
| divergence [physics] | 0.076 | 0.07583 |
| kappa [raw] | 8.21 | 8.207 |
| kappa [physics_no_cross] | 24.52 | 24.52 |
| kappa [physics] | 53.43 | 53.43 |
| non-zero terms [raw] | 20.1 | 20.05 |
| non-zero terms [physics_no_cross] | 28.2 | 28.18 |
| non-zero terms [physics] | 37 | 36.98 |
| one-factor EPI [raw] | 4.32 | 4.317 |
| one-factor EPI [physics_no_cross] | 0.28 | 0.2818 |
| one-factor EPI [physics] | 2.75 | 2.754 |
| one-factor survival [raw] | 0.55 | 0.55 |
| one-factor survival [physics_no_cross] | 0.15 | 0.15 |
| one-factor survival [raw] | 0.55 | 0.55 |
| STLSQ EPI [raw] | 3.83 | 3.833 |
| STLSQ EPI [physics] | 2.48 | 2.476 |
| raw_ens EPI | 4.32 | 4.317 |
| raw_ens SD | 4.08 | 4.076 |
| raw_ens violations | 4 130 | 4 130 |
| lowthr EPI | 3.09 | 3.089 |
| lowthr SD | 2.71 | 2.707 |
| tuned EPI | 2.26 | 2.261 |
| tuned n | 4 | 4 |
| stock EPI | -1.23 | -1.226 |
| stock n | 4 | 4 |
| ppo EPI | 0.45 | 0.4537 |
| ppo SD | 2.97 | 2.973 |
| ppo violations | 1 330 | 1 330 |
| unseen raw_ens | 6.42 | 6.422 |
| unseen raw_ens SD | 0.95 | 0.9516 |
| unseen heuristic | -0.33 | -0.3271 |
| tuning gain | 3.49 | 3.488 |

## Running text

### the identification ladder (passage `ladder`)

Sources: `ladder_rerun/ladder_rerun.csv`, `ladder_rerun/ladder_rerun2.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| physics mean rollout | 1 357 | 1 357 |
| physics rollout q75 | 2 360 | 2 360 |
| comparator rollout (raw) | 2.684 | 2.684 |
| comparator rollout (selected) | 10.5 | 10.5 |
| comparator diverged (raw) | 0 | 0 |
| comparator diverged (selected) | 0.0208 | 0.02083 |
| comparator terms (raw) | 19.9 | 19.9 |
| comparator terms (selected) | 28.25 | 28.25 |

### the held-out identification block (passage `holdout`)

Sources: `holdout/holdout_holdout.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| raw held-out/in-sample ratio | 1.04 | 1.04 |
| physics_no_cross held-out/in-sample ratio | 1.27 | 1.271 |
| physics held-out/in-sample ratio | 0.99 | 0.9857 |
| raw eval 2018 | 2.8 | 2.802 |
| raw eval 2019 | 2.61 | 2.61 |
| physics_no_cross eval 2018 | 16.94 | 16.94 |
| physics_no_cross eval 2019 | 2.7 | 2.695 |
| physics eval 2018 | 27.19 | 27.19 |
| physics eval 2019 | 15.85 | 15.85 |

### the two harnesses, and the setpoint search (passage `harness`)

Sources: `final/main.csv`, `n2_tune/tune_rb_n2.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| rule_based in the main harness | 1.206 | 1.206 |
| rule_based in the main harness (sign) | 1 | 1 |
| rule_based in the tuning harness | 1.226 | 1.226 |
| selected day setpoint | 22.9 | 22.92 |
| selected night setpoint | 14.4 | 14.38 |

### the paired comparisons around Table 7 (passage `paired`)

Sources: `final/main.csv`, `n2_tune/tune_rb_n2.csv`, `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| stock-in-tuning-harness delta mean | 3.49 | 3.488 |
| stock-in-tuning-harness delta sign | 1 | 1 |
| stock-in-tuning-harness wins | 0 | 0 |
| stock-in-tuning-harness n | 4 | 4 |
| signed-rank floor at n=4 | 0.125 | 0.125 |
| raw variants delta median | 0.011 | 0.01088 |
| raw variants delta median sign | 1 | 1 |
| raw variants p | 0.6 | 0.6011 |
| dense/lowthr mean |delta| | 0.026 | 0.02647 |
| dense four-season mean | 3.082 | 3.082 |
| lowthr four-season mean | 3.089 | 3.089 |
| dense/lowthr p | 0.012 | 0.01196 |

### the 17-feature library (passage `notuboil`)

Sources: `ladder_rerun/ladder_rerun.csv`, `ladder_rerun/ladder_rerun2.csv`, `notuboil/ladder_notuboil.csv`, `notuboil/main_notuboil*.csv`, `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| notuboil kappa | 52.3 | 52.28 |
| physics kappa | 53.4 | 53.43 |
| notuboil rollout median | 24.2 | 24.17 |
| notuboil divergence | 0.084 | 0.08417 |
| vs middle: mean paired difference | 1.83 | 1.831 |
| vs middle: wins | 62 | 62 |
| vs middle: n | 80 | 80 |
| vs full: median | 0.18 | 0.1763 |
| STLSQ arm not separable | 0.089 | 0.08896 |
| vs middle: p_Holm over the four contrasts | 4.4e-06 | 4.4e-06 |
| vs full: p_Holm over the four contrasts | 0.0064 | 0.006361 |

### what repricing the stage cost bought (passage `repricing`)

Sources: `final/main.csv`, `n7/main_n7.csv`, `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| repricing gain, dense | 2.74 | 2.738 |
| repricing gain, lowthr | 2.68 | 2.676 |
| repricing gain, raw_ens | 0.25 | 0.2455 |
| repricing gain, raw | 0.21 | 0.2143 |
| smallest gain ratio | 10.9 | 10.9 |
| largest gain ratio | 12.8 | 12.78 |
| violations before repricing | 6 006 | 6 006 |
| violations after repricing | 3 689 | 3 689 |
| priced gap vs full physics | 1.56 | 1.563 |
| raw_ens priced mean | 4.317 | 4.317 |
| phys_ens priced mean | 2.754 | 2.754 |

### the like-for-like comparison on the original objective (passage `likeforlike`)

Sources: `final/main.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| sindy_mpc_dense | 0.34 | 0.3439 |
| sindy_mpc_conf | 1.26 | 1.257 |
| rule_based | 1.21 | 1.206 |

### the sparsity levels that retain the boiler term (passage `levels`)

Sources: `final/mechanism.csv`, `priced_mech/mechanism_pricedMech.csv`, `priced_mech/mechanism_pricedMech2.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| priced retaining | 5.77 | 5.77 |
| priced not retaining | 3.47 | 3.465 |
| original retaining | 3.46 | 3.462 |
| original not retaining | 2.77 | 2.772 |

### the full-model planner's solver budget (passage `oracle`)

Sources: `final/main.csv`, `oracle_budget/main_orcbudget.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| oracle 2022 min season fraction | 0.936 | 0.9361 |
| oracle 2022 max season fraction | 0.987 | 0.9872 |
| oracle 2022 mean season fraction | 0.95 | 0.95 |
| oracle 2022 runs | 20 | 20 |
| raised-budget worse seed | 1.12 | 1.117 |
| raised-budget better seed | 0.56 | 0.5601 |
| raised-budget mean | 0.84 | 0.8387 |
| raised-budget failures (high) | 140 | 140 |
| raised-budget failures (low) | 103 | 103 |
| imputed four-season mean | 2.2 | 2.196 |
| three-season mean | 2.65 | 2.648 |

### replaying the surrogates along the planner's own trajectory (passage `replay`)

Sources: `v3_parity/parity_v3.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| confirmatory one-step RMSE | 1.89 | 1.889 |
| confirmatory one-step SD | 0.09 | 0.08988 |
| confirmatory R2 | 0.82 | 0.8199 |
| confirmatory rollout RMSE | 2.62 | 2.624 |
| confirmatory seeds | 5 | 5 |
| lowthr one-step RMSE | 1.82 | 1.822 |
| lowthr one-step SD | 0.04 | 0.03544 |
| lowthr R2 | 0.83 | 0.8327 |
| lowthr rollout RMSE | 2.49 | 2.494 |
| lowthr seeds | 5 | 5 |

### the horizon (passage `horizon`)

Sources: `ec_h8/main_ec_h8.csv`, `final/main.csv`, `n7/main_n7.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| sindy_mpc_raw_ens at h=8 | 4.58 | 4.577 |
| sindy_mpc_raw_ens at h=20 | 4.29 | 4.291 |
| sindy_mpc_raw_ens delta | 0.29 | 0.2865 |
| sindy_mpc_raw_ens wins | 33 | 33 |
| sindy_mpc_raw_ens n | 40 | 40 |
| sindy_mpc_lowthr at h=8 | 2.78 | 2.784 |
| sindy_mpc_lowthr at h=20 | 0.67 | 0.6702 |
| sindy_mpc_lowthr delta | 2.11 | 2.114 |
| sindy_mpc_lowthr wins | 40 | 40 |
| sindy_mpc_lowthr n | 40 | 40 |
| sindy_mpc_dense at h=8 | 2.65 | 2.646 |
| sindy_mpc_dense at h=20 | 0.53 | 0.529 |
| sindy_mpc_dense delta | 2.12 | 2.117 |
| sindy_mpc_dense wins | 40 | 40 |
| sindy_mpc_dense n | 40 | 40 |
| sindy_mpc_conf at h=8 | 0.9 | 0.8972 |
| sindy_mpc_conf at h=20 | 0.4 | 0.402 |
| sindy_mpc_conf delta | 1.3 | 1.299 |
| sindy_mpc_conf wins | 37 | 37 |
| sindy_mpc_conf n | 40 | 40 |

### the bootstrap draw of the ensemble optimizer (passage `draws`)

Sources: `ea_draws/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| raw leads in cells | 32 | 32 |
| seed x draw cells | 36 | 36 |
| leadership fraction | 0.89 | 0.8889 |
| sindy_mpc_raw_ens spread across draws | 0.26 | 0.2631 |
| sindy_mpc_conf spread across draws | 1.11 | 1.106 |
| sindy_mpc_conf_dagger spread across draws | 2.04 | 2.044 |
| five seeds below the threshold | 5 | 5 |
| threshold the five lie below | 0.25 | 0.2481 |
| the one contributing seed | 1.18 | 1.183 |

### on-policy re-identification and the EKF arm (passage `adapt`)

Sources: `final/adapt.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| on-policy mean | 0.39 | 0.3921 |
| static mean | 1.58 | 1.584 |
| on-policy paired delta | 1.19 | 1.192 |
| on-policy paired median | 0.4 | 0.4045 |
| on-policy wins | 380 | 380 |
| on-policy pairs | 600 | 600 |
| static violations | 5 424 | 5 424 |
| on-policy violations | 4 654 | 4 654 |
| EKF mean | 2.95 | 2.945 |
| EKF paired delta | 1.36 | 1.361 |
| EKF early terminations | 234 | 234 |

### the residual-based guard and its detector (passage `guard`)

Sources: `final/guard.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| guarded mean | 2.59 | 2.592 |
| unguarded mean | 1.91 | 1.905 |
| guard paired mean | 0.69 | 0.6863 |
| guard paired median | 0.19 | 0.1893 |
| guard wins | 335 | 335 |
| guard p | 0.0047 | 0.004709 |
| extra violation steps | 430 | 430 |
| violations worse in | 529 | 529 |
| guarded early terminations | 179 | 179 |
| completed-season difference | 0.33 | 0.3321 |
| completed-season p | 0.081 | 0.08075 |
| AUC distance | 0.663 | 0.6625 |
| AUC distance SD | 0.042 | 0.04234 |
| AUC spread | 0.627 | 0.6269 |
| AUC spread SD | 0.058 | 0.05842 |

### the sensitivity grids (passage `sens`)

Sources: `final/design.csv`, `final/tables/sensitivity_price_span.csv`, `priced_design/design_pricedDesign.csv`, `priced_design/design_pricedDesign2.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| perturbation p at 15% | 0.0059 | 0.005859 |
| perturbation p at 20% | 0.002 | 0.001953 |
| coarse grid at 10% | 1.67 | 1.671 |
| coarse grid at 20% | 13.41 | 13.41 |
| coarse grid at 30% | 4.77 | 4.771 |
| coarse grid span | 15.08 | 15.08 |
| threshold span (fine) | 5 | 5.002 |
| threshold span (canonical) | 1.87 | 1.866 |
| horizon span (fine) | 4.76 | 4.764 |
| horizon span (canonical) | 5.21 | 5.205 |
| horizon sweep h=8 | 6.11 | 6.113 |
| horizon sweep h=12 | 5.13 | 5.129 |
| horizon sweep h=20 | 3.63 | 3.628 |
| horizon sweep h=30 | 0.91 | 0.9078 |
| sweep SD at h=8 | 0.87 | 0.8746 |
| sweep SD at h=30 | 4.03 | 4.026 |
| price span min | 31.5 | 31.48 |
| price span max | 50.2 | 50.17 |
| price span median | 38.3 | 38.26 |

### where the two draw waves disagree (passage `survivaldiff`)

Sources: `ea_draws/*.csv`, `final/draws.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| 6x6 wave survival | 0 | 0 |
| canonical wave survival | 0.12 | 0.12 |
| canonical wave fits | 800 | 800 |
| canonical wave seeds | 20 | 20 |
| canonical wave draws | 10 | 10 |

### the open-loop series, restated (passage `disc-ladder`)

Sources: `ladder_rerun/ladder_rerun.csv`, `ladder_rerun/ladder_rerun2.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| raw kappa | 8.2 | 8.207 |
| raw rollout | 3.31 | 3.312 |
| raw divergence | 0 | 0 |
| physics_no_cross kappa | 24.5 | 24.52 |
| physics_no_cross rollout | 7.11 | 7.109 |
| physics_no_cross divergence | 0.011 | 0.01104 |
| physics kappa | 53.4 | 53.43 |
| physics rollout | 30.84 | 30.84 |
| physics divergence | 0.13 | 0.13 |
| physics one-step | 2.02 | 2.022 |
| physics_no_cross one-step | 2.17 | 2.174 |
| raw one-step | 2.14 | 2.137 |
| raw retained terms | 19.9 | 19.9 |
| no_cross retained terms | 28.25 | 28.25 |

### the non-monotone series and the survivors (passage `disc-mechanism`)

Sources: `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| phys_ens over conf, mean | 2.47 | 2.472 |
| phys_ens over conf, median | 2.39 | 2.393 |
| phys_ens over conf, wins | 63 | 63 |
| raw over phys_ens, mean | 1.56 | 1.563 |
| raw over phys_ens, median | 0.97 | 0.9711 |
| raw over phys_ens, wins | 67 | 67 |
| raw variants median | 0.01 | 0.01088 |
| raw variants mean | 0.48 | 0.4839 |
| raw variants wins | 33 | 33 |
| raw variants p | 0.6 | 0.6011 |
| ensembling on physics | 0.057 | 0.05689 |

### the observational splits and the term-deletion test (passage `disc-splits`)

Sources: `notuboil/main_notuboil*.csv`, `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| sindy_mpc_phys_ens first figure | 3.09 | 3.095 |
| sindy_mpc_phys_ens second figure | 2.48 | 2.475 |
| sindy_mpc_phys_ens first count | 9 | 9 |
| sindy_mpc_phys_ens second count | 11 | 11 |
| sindy_mpc_phys_ens split p | 0.25 | 0.2545 |
| sindy_mpc_conf first figure | 2.2 | 2.199 |
| sindy_mpc_conf second figure | 0.06 | 0.05653 |
| sindy_mpc_conf first count | 3 | 3 |
| sindy_mpc_conf second count | 17 | 17 |
| sindy_mpc_conf split p | 0.18 | 0.1789 |
| no-cross cost of losing the term | 2.26 | 2.256 |
| sindy_mpc_notuboil_ens margin | 2.11 | 2.113 |
| sindy_mpc_notuboil margin | 2.28 | 2.283 |
| notuboil survival | 0.4 | 0.4 |
| notuboil survivors | 8 | 8 |
| Wilson lower | 0.22 | 0.2188 |
| Wilson upper | 0.61 | 0.6134 |

### benchmarking safeguards, restated (passage `disc-safeguards`)

Sources: `final/main.csv`, `n2_tune/tune_rb_n2.csv`, `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| ppo violations | 1 330 | 1 330 |
| raw violations | 4 130 | 4 130 |
| ppo margin shortfall | 3.86 | 3.864 |
| single-replicate contrast | 2.55 | 2.551 |
| signed-rank floor | 0.125 | 0.125 |
| front-pair difference | 0.0066 | 0.006597 |
| front-pair p | 0.012 | 0.01196 |

### the caveats (passage `disc-caveats`)

Sources: `ec_h8/main_ec_h8.csv`, `final/adapt.csv`, `final/design.csv`, `final/main.csv`, `n2_tune/tune_rb_n2.csv`, `n7/main_n7.csv`, `priced_design/design_pricedDesign.csv`, `priced_design/design_pricedDesign2.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| span of means (default objective) | 12.2 | 12.24 |
| median at 20 per cent | 0.31 | 0.3141 |
| raw-library horizon gain | 0.29 | 0.2865 |
| physics-informed gain, low | 1.3 | 1.299 |
| physics-informed gain, high | 2.1 | 2.117 |
| largest harness gap | 0.038 | 0.03812 |
| EKF margin | 2.95 | 2.945 |
| static margin | 1.58 | 1.584 |
| EKF early-termination share | 39 | 39 |

### the framing claims (passage `intro`)

Sources: `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| raw_ens SD | 4.08 | 4.076 |
| lowthr SD | 2.71 | 2.707 |
| the difference | 1.23 | 1.228 |
| raw_ens in 2021 | 1.56 | 1.556 |
| lowthr in 2021 | 0.27 | 0.2654 |
| raw over phys_ens | 1.56 | 1.563 |
| raw runs that lost the term | 3.48 | 3.483 |
| physics runs that kept it | 2.52 | 2.516 |

### the conclusions (passage `conclusions`)

Sources: `design_priced_real/design_designPriced.csv`, `final/guard.csv`, `final/main.csv`, `n2_tune/tune_rb_n2.csv`, `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| survival stratification p (seed level) | 0.18 | 0.1789 |
| replicates that kept the term | 3 | 3 |
| replicates that lost the term | 17 | 17 |
| stratification points the same way (kept > lost) | 1 | 1 |
| raw vs physics-informed, seeds won | 16 | 16 |
| raw vs tuned heuristic, seeds won | 19 | 19 |
| seed counts | 20 | 20 |
| priced perturbation cost, mean | 7.97 | 7.973 |
| priced perturbation cost, median | 3.35 | 3.347 |
| priced perturbation p | 0.0043 | 0.00433 |
| guard paired mean | 0.69 | 0.6863 |
| guard extra violations | 430 | 430 |

### the measured constants of the method (passage `methods`)

Sources: `final/main.csv`, `n2_tune/tune_rb_n2.csv`, `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| marginal cost, boiler | 0.00293 | 0.002925 |
| marginal cost, lamps | 0.0087 | 0.0087 |
| marginal cost, CO2 | 0.00135 | 0.00135 |
| cost ratio, lamps | 2.97 | 2.974 |
| cost ratio, CO2 | 0.46 | 0.4615 |
| priced weights sum at u=(1,1,1) | 31.99 | 31.99 |
| weight ratio, lamps | 2.97 | 2.97 |
| weight ratio, CO2 | 0.46 | 0.4612 |
| main-harness mean | 1.206 | 1.206 |
| tuning-harness mean | 1.226 | 1.226 |
| harness discrepancy 2020 | 0.003 | 0.003096 |
| harness discrepancy 2021 | 0.013 | 0.01342 |
| harness discrepancy 2022 | 0.027 | 0.02665 |
| harness discrepancy 2023 | 0.038 | 0.03812 |
| discrepancy grows monotonically | 1 | 1 |
| front-pair p | 0.012 | 0.01196 |
| front-pair difference | 0.0066 | 0.006597 |

### the constants the method states (passage `constants`)

Sources: `article_experiment_utils.py`, `make_weather.py`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| latitude | 47.24 | 47.24 |
| longitude | 39.71 | 39.71 |
| Magnus coefficient | 0.6108 | 0.6108 |
| Magnus numerator | 17.27 | 17.27 |
| Magnus offset | 237.3 | 237.3 |
| fruit price | 1.6 | 1.6 |
| dry-to-fresh ratio | 0.065 | 0.065 |

### The last four statistics (passage `tail`)

Sources: `final/adapt.csv`, `final/main.csv`, `holdout/holdout_holdout.csv`, `ladder_rerun/ladder_rerun.csv`, `ladder_rerun/ladder_rerun2.csv`, `n2_tune/tune_rb_n2.csv`, `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| no_cross in the reversing direction | 2.687 | 2.687 |
| raw in the reversing direction | 2.722 | 2.722 |
| raw ensemble terms | 20.2 | 20.2 |
| physics_no_cross ensemble terms | 28.25 | 28.25 |
| physics ensemble terms | 37.2 | 37.2 |
| raw_ens under the family of 13 | 6.9e-11 | 6.95e-11 |
| lowthr under the family of 13 | 0.00047 | 0.00047 |
| EKF p-value | 7.4e-14 | 7.44e-14 |

### the knock-in ablation, in full (passage `knockin`)

Sources: `final/mechanism.csv`, `priced_mech/mechanism_pricedMech.csv`, `priced_mech/mechanism_pricedMech2.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| positive replicates | 16 | 16 |
| uncorrected p | 0.00059 | 0.000586 |
| Holm over the two knock tests | 0.0012 | 0.001171 |
| Holm over the four mechanism contrasts | 0.0018 | 0.001757 |
| effect median | 0.21 | 0.2134 |
| effect lower quartile | 0.02 | 0.02358 |
| effect upper quartile | 4.49 | 4.491 |
| effect mean | 1.92 | 1.917 |

### Integer-valued claims: violation counts (passage `violations`)

Sources: `final/design.csv`, `final/mechanism.csv`, `final/tables/faults.csv`, `priced_design/design_pricedDesign.csv`, `priced_design/design_pricedDesign2.csv`, `priced_mech/mechanism_pricedMech.csv`, `priced_mech/mechanism_pricedMech2.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| uVent_dead unsupervised | 9 131 | 9 131 |
| uVent_dead supervised | 5 292 | 5 292 |
| uBoil_stuck unsupervised | 5 198 | 5 198 |
| uBoil_stuck supervised | 2 660 | 2 660 |
| threshold 0.01 (finer rerun) | 6 167 | 6 167 |
| threshold 0.2 (finer rerun) | 9 569 | 9 569 |
| threshold 0.05 (finer rerun) | 5 155 | 5 155 |
| threshold 0.01 (canonical) | 6 263 | 6 263 |
| threshold 0.05 (canonical) | 5 423 | 5 423 |
| threshold 0.1 (canonical) | 8 440 | 8 440 |
| threshold 0.2 (canonical) | 9 219 | 9 219 |
| lambda sweep, lowest level | 3 850 | 3 851 |
| lambda sweep, highest level | 9 090 | 9 086 |

### Integer-valued claims: the structural counts of the grids (passage `counts`)

Sources: `*/regen_manifest.json`, `final/main.csv`, `holdout/holdout_holdout.csv`, `ladder_rerun/ladder_rerun.csv`, `ladder_rerun/ladder_rerun2.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| ladder labels | 72 | 72 |
| distinct fits | 54 | 54 |
| constrained and sr3 are bit-identical | 1 | 1 |
| seed-cells compared | 360 | 360 |
| ladder fits | 1 440 | 1 440 |
| ladder seeds | 20 | 20 |
| held-out fits | 240 | 240 |
| held-out seeds | 10 | 10 |
| retained runs in the canonical wave | 780 | 780 |
| oracle season completion per cent | 95 | 95 |
| wave manifests in the tree | 21 | 21 |
| distinct git_sha across manifests | 12 | 12 |
| manifests counted with the git_sha | 21 | 21 |
| no manifest carries an environment block | 0 | 0 |

### Integer-valued claims: the configuration constants (passage `config`)

Sources: `article_experiment_utils.py`, `final/main.csv`, `protocol_config.py`, `regen/experiments_support.py`, `regen/regen_config.py`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| control step (s) | 900 | 900 |
| control steps per season | 5 760 | 5 760 |
| search generator seed | 2.03e+07 | 2.03e+07 |
| PRBS amplitude | 0.3 | 0.3 |
| PRBS switching period (steps) | 16 | 16 |
| PRBS switching period (hours) | 4 | 4 |
| noise amplitude | 0.1 | 0.1 |
| noise refresh period (steps) | 5 | 5 |
| training steps per season | 5 760 | 5 760 |
| RL training steps | 2e+05 | 2e+05 |
| GreenLight-Gym reference RL budget (external constant) | 2e+06 | 2e+06 |
| RL budget in seasons | 35 | 34.72 |
| candidate columns, raw | 15 | 15 |
| candidate columns, physics_no_cross | 18 | 18 |
| candidate columns, physics | 22 | 22 |
| candidate columns, deletion library | 21 | 21 |
| candidate coefficients, raw | 45 | 45 |
| candidate coefficients, physics_no_cross | 54 | 54 |
| candidate coefficients, physics | 66 | 66 |
| candidate coefficients, physics_no_tuboil | 63 | 63 |

### The corridors, the horizons, and the abstract's percentages (passage `bounds`)

Sources: `article_experiment_utils.py`, `make_weather.py`, `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`, `regen/regen_config.py`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| CO2 corridor lower | 300 | 300 |
| CO2 corridor upper | 1 600 | 1 600 |
| temperature corridor lower | 15 | 15 |
| temperature corridor upper | 34 | 34 |
| humidity corridor lower | 50 | 50 |
| humidity corridor upper | 85 | 85 |
| rollout horizon 1 | 4 | 4 |
| rollout horizon 2 | 20 | 20 |
| rollout horizon 3 | 96 | 96 |
| raw survival per cent | 55 | 55 |
| physics_no_cross survival per cent | 15 | 15 |
| physics survival per cent | 55 | 55 |
| MPC temperature lower bound | 12 | 12 |
| MPC temperature upper bound | 35 | 35 |
| MPC ventilation upper bound | 0.4 | 0.4 |
| move-suppression weight uBoil | 10 | 10 |
| move-suppression weight uCO2 | 5 | 5 |
| move-suppression weight uThScr | 100 | 100 |
| move-suppression weight uVent | 50 | 50 |
| move-suppression weight uLamp | 1 | 1 |
| move-suppression weight uBlScr | 1 | 1 |
| outdoor CO2 | 400 | 400 |

### the observational association, library by library (passage `association`)

Sources: `final/main.csv`, `n7/main_n7.csv`, `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| physics_no_cross, priced | 0.0015 | 0.001496 |
| physics_no_cross, original | 0.0006 | 0.000636 |
| raw, priced | 0.136 | 0.1363 |
| raw, original | 0.316 | 0.3163 |
| physics, priced | 0.178 | 0.1784 |

### The figure 3 caption: the knock-in under both stage costs, and the knock-out (passage `knockcaption`)

Sources: `final/mechanism.csv`, `priced_mech/mechanism_pricedMech.csv`, `priced_mech/mechanism_pricedMech2.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| default knock-in wins | 17 | 17 |
| default knock-in p | 0.00032 | 0.000322 |
| default knock-in mean | 2.52 | 2.521 |
| priced knock-in wins | 16 | 16 |
| priced knock-in p | 0.00059 | 0.000586 |
| priced knock-in mean | 1.92 | 1.917 |
| default knock-in, Holm over four | 0.0013 | 0.001289 |
| priced knock-in, Holm over four | 0.0018 | 0.001757 |
| default knock-out median | 0 | 0 |
| default knock-out wins | 1 | 1 |
| priced knock-out median | 0 | 0 |
| priced knock-out wins | 1 | 1 |
| knock-out median as printed | 0 | 0 |
| knock-out positives as printed | 20 | 1 |

### the headline contrast by season and at seed level, and the seed-level (passage `seedlevel`)

Sources: `final/main.csv`, `n2_tune/tune_rb_n2.csv`, `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| headline paired mean | 1.23 | 1.228 |
| headline paired median | 1.58 | 1.577 |
| headline paired wins | 62 | 62 |
| headline paired n | 80 | 80 |
| headline paired p_Holm(15) | 0.00077 | 0.000771 |
| 2020 wins | 20 | 20 |
| 2023 wins equal 2020 wins | 20 | 20 |
| 2022 wins | 16 | 16 |
| 2021 wins | 6 | 6 |
| 2021 p | 0.0023 | 0.002325 |
| headline seed-level wins | 16 | 16 |
| headline seed-level n | 20 | 20 |
| headline seed-level p_Holm(15) | 0.0084 | 0.00845 |
| raw_ens seed wins | 19 | 19 |
| raw seed wins | 17 | 17 |
| raw_ens seed p_Holm | 7.4e-05 | 7.44e-05 |
| raw seed p_Holm | 0.044 | 0.04374 |
| lowthr seed wins | 13 | 13 |
| dense seed wins equal lowthr's | 13 | 13 |
| lowthr seed p_Holm | 0.103 | 0.1031 |
| dense seed p_Holm equals lowthr's | 0.1031 | 0.1031 |
| conf not significant at seed level | 1 | 1 |
| dense_dagger not significant at seed level | 1 | 1 |
| phys_ens, phys, conf_dagger not significant at seed level | 3 | 3 |

### Figure 1d: how far the surviving boiler coefficients sit above the cut (passage `paneld`)

Sources: `phys_lib/main_physlib*.csv`, `priced_dagger/*.csv`, `priced_main/*.csv`.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| raw survivors, low | 0.06 | 0.06155 |
| raw survivors, high | 0.08 | 0.08353 |
| raw survivors, median | 0.069 | 0.06852 |
| raw survivors, count | 11 | 11 |
| raw replicates | 20 | 20 |
| no-cross survivors, low | 0.06 | 0.05965 |
| no-cross survivors, high | 0.07 | 0.0743 |
| no-cross survivors, median | 0.061 | 0.06086 |
| no-cross survivors, count | 3 | 3 |
| physics survivors, count | 11 | 11 |
| physics survivors, low group | 5 | 5 |
| physics survivors, high group | 6 | 6 |
| physics survivors, high group ceiling | 0.19 | 0.194 |
| physics survivors, median | 0.143 | 0.143 |
| raw survivors restated | 11 | 11 |
| no-cross survivors restated | 3 | 3 |
| every raw and no-cross survivor is below 0.10 | 1 | 1 |

## Regenerating

The per-run tables are regenerated with `python run_regen.py --experiment <block> --seeds 0-19 --out <dir>` followed by `python run_regen.py --merge --out <dir>`; `python make_tables.py --out <dir>` rebuilds the derived tables and `tables/SUMMARY.md`; `python verify_regen.py --out <dir>` applies the acceptance gates. The comparisons above are re-run from the project repository, where the manuscript source lives, with `python paper/en/verify_manuscript.py`.
