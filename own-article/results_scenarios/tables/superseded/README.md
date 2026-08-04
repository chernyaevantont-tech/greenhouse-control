# Superseded result tables (do NOT cite in the manuscript)

These E3/E4 summary tables belong to earlier result generations (10-seed E3;
pre-spring-OOD E4). They were superseded by the 20-seed / spring-OOD canon on
2026-07-03 and are kept only for provenance/history. **Every headline number
must come from the canonical files below, never from this folder.**

| Archived file | Generation | Canonical replacement |
|---|---|---|
| `e3_main_table.csv` | E3, 10 seeds, 5 methods (no oracle/nn) | `../e3_main_table_20seed.csv` (20 seeds, 8 methods) |
| `e3_pareto_table.csv` | E3 Pareto, 10 seeds (conf_dagger +5.98) | Pareto columns (`dominated_by`, `on_frontier`, `scaled_pen`) inside `../e3_main_table_20seed.csv`; figure `../../figures/e3_pareto_20seed.png` |
| `e3_stats_vs_rulebased.csv` | E3 stats, 10 seeds | `../e3_stats_20seed.csv` (Wilcoxon+Holm+bootstrap, 20 seeds) |
| `e4_adaptation_20seed.csv` | E4, 20-seed batch on the OLD shift definition (single row/method; rule_based +0.19 > offline) | `../e4_adaptation_springOOD.csv` (per-shift 2021/2022/2023-03, 20 seeds — the authoritative E4) |
| `e4_adaptation_table.csv` | E4, original 3-shift × 3-seed, 30-day (n=9) | `../e4_adaptation_springOOD.csv` |

## Why E4 had two 20-seed tables
The "20-seed regen" commit (`2d5eb9a`, 2026-07-03 09:50) emitted BOTH
`e3_main_table_20seed.csv` and `e4_adaptation_20seed.csv`. ~1.5 h later the E4
run was reframed onto spring OOD shifts (`8bceff9`, 11:16) because the earlier
E4 shift was pathological (ODE truncation on summer shift; see
`EXPERIMENT_PROTOCOL.md` §E4). So the newest E3 and the newest E4 come from
DIFFERENT commits — pair `e3_main_table_20seed.csv` (E3) with
`e4_adaptation_springOOD.csv` (E4), not the same "20-seed" batch.

## NOT archived here (handled by the plan, not by archival)
- `e8_stats_*.csv` — the statistical-validity capstone still references the old
  E3 world (oracle n=2, ppo −13/−17). It must be **regenerated** against the
  20-seed canon, not archived (archiving would leave no E8).
- `e3_salvage_from_logs.csv` — pre-freeze salvage scaffolding (grey_box −0.016);
  diagnostic only.
- `../../results_e0_e3_final/E0_E3_SUMMARY.md` — dated 06-30 snapshot; its E3
  block is stale but it also documents valid E0/E1/E2 setup. Update or banner it.
