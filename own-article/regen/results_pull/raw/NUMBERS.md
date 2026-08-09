# NUMBERS — every stated result and where it comes from

- config_hash: `637c6b535a9e`
- git_sha: `unknown`
- env_hash: `n/a`

| Claim | Value | Source |
|---|---|---|
| Cross-season leader | ppo: +0.45 EUR/m2, wins 2/4 seasons, season-bootstrap CI [-1.63, +2.54] | `tables/main_pooled.csv` |
| Test used against the rule-based reference | one_sample_signed_rank_vs_constant | `tables/main_stats_vs_rule_based.csv` |
| Ranking stability across the price grid | 2 distinct winner(s): ['rule_based', 'sindy_mpc_dense_dagger'] | `tables/sensitivity_prices.csv` |
| Short seasons: kept vs excluded | 20 of 800 excluded (solver aborts); 42 simulator-terminated seasons KEPT as outcomes | `main.csv (`stop_reason`)` |
| EPI monotone in the boiler coefficient? | min EPI with xi!=0 = +1.59; mean EPI with xi==0 = +2.77 -> NOT monotone | `tables/lambda_sweep.csv` |
| Single-coefficient knock-in effect | median +3.05 EUR/m2, CI [+1.57, +3.50], p=0.00032, positive 17/20 | `tables/knock_effect.csv` |
| Cross-term (t_uBoil) interaction | delta -0.10, p=0.52 -> adds nothing | `tables/cross_interaction.csv` |
| Configurations evaluated / passing the open-loop gates | 72 evaluated, 30 pass; frozen recipe physics_no_cross/d1/ensemble/none is NOT among them | `tables/ladder.csv` |

Regenerate with:

```bash
python run_regen.py --merge --out <out> && python make_tables.py --out <out>
```
