# Remote distributed E3 run — status & continuation

Heavy article-grade compute runs on two LAN Ubuntu boxes (RTX 3050, 16 cores) as
detached `nohup` jobs that **survive local session/agent restarts**. Results live on
the servers and are pulled to this PC with `remote_sync.sh`.

## Servers (SSH config aliases, key `~/.ssh/swarm_deploy`)
- `server0` (user agroengeneer) — venv `~/greenhouse-control/.venv` (CPU torch 2.12).
  Runs E0–E2 + the **cheap** controllers (rule_based, sindy_mpc, grey_box_mpc, nn_mpc) × 10 seeds.
- `server1` (user lab) — same venv. Runs the **long poles**: oracle×2, PPO×3, SAC×3.
- Job logs: `~/e3logs/*.log` on each. Launchers: `~/launch_server{0,1}.sh`.

## Check status / pull results to PC (re-runnable, no live session needed)
```bash
bash own-article/remote_sync.sh
```
Prints jobs-running + partial counts per server; pulls `e3_seeded_*.csv`, E0–E2 tables,
`recipe_frozen.json`, figures, and all logs into `own-article/results_scenarios/`;
and salvages completed `(controller, seed)` results from the logs into
`results_scenarios/tables/e3_salvage_from_logs.csv` (so finished work is saved even if a
job hasn't written its CSV yet). `run_e3_seeds.py` now also writes its CSV **incrementally**.

## State as of 2026-06-29 (corrected run v2)
- E0/E1/E2 **done**. Frozen recipe = **physics_no_cross / degree 1 / ensemble / none**.
- **MPC objective fixed → EPI-aligned** (was the real problem): instead of tight setpoint
  tracking (T=20/CO2=800, which over-spent → every tracking-MPC incl. the oracle went
  EPI<0), the objective now keeps climate in a **day/night productive band at minimum
  resource cost** (`build_mpc_controller`, `rollout_oracle_mpc`, `rollout_mpc_nn`).
  Validation (3-day): `sindy_mpc` EPI **+0.43** (was −11.5), now competitive with
  `rule_based` (+0.34); grey-box weaker (exposes model quality). `run_e3_seeds.py` pins
  torch to 1 thread (fixes nn_mpc ~3 h → ~15 min under concurrency).
- **v2 jobs running:** server0 = `mpc_s0..s9` (rule_based, sindy_mpc, grey_box_mpc, nn_mpc,
  new objective); server1 = `orcv_0/1` (oracle, new objective) + **reused** `ppo0..2`,
  `sac0..2` (RL is objective-independent → not re-run). Old `cheap_*`/`orc*` partials and
  logs were deleted/archived. Oracle (~2 h) is the bottleneck.
- Note: oracle still tends to over-spend (perfect model + band ⇒ heats to the band; the
  marginal fruit may not pay for it on a short horizon) — documented economic-MPC nuance.

## When all jobs are done (target: 18 `e3_seeded_*.csv` partials = 10 mpc_s* + 2 orcv_* + 3 ppo* + 3 sac*)
```bash
bash own-article/remote_sync.sh        # pull final partials
"C:/Users/zergu/repos/greenlight/sindylom/.venv/Scripts/python.exe" own-article/merge_e3.py
```
Produces `e3_main_table.csv` (EPI mean±std, gap-to-oracle), `e3_stats_vs_rulebased.csv`
(Wilcoxon+Holm+bootstrap CI), `e3_pareto_epi_violations.png`.

## Tomorrow's quick path
1. `bash own-article/remote_sync.sh` → see what finished.
2. If oracle/RL/nn done → re-run sindy_mpc with frozen recipe (above) → `merge_e3.py`.
3. Then continue with E4–E8 (next protocol phase).
