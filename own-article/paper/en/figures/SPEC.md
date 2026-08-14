# Figure specification — English *Agronomy* manuscript

Final set: **five numbered body figures plus an unnumbered graphical abstract**,
consolidated from the ten the manuscript currently declares.

Every panel below names its source CSVs and its filter. All paths are relative to
`own-article/regen/results/`. All loading goes through `_plotstyle.py`, which
applies the dedup key and the solver-abort rule in one place; no figure script
may read a CSV directly.

Verified against the tree on 2026-08-13: `python _plotstyle.py` reproduces every
number quoted here.

---

## Why six, and what was dropped

Four of the ten declared figures plotted the **same 240-row degree-1 undenoised
ladder block**: `fig01_selection_reversal` (a, b), `fig-ladder-scatter`,
`fig1_conditioning_vs_error`, and panel (a) of the graphical abstract. That is
four renderings of one result and the single most likely "consolidate your
figures" review comment. They collapse into **Figure 1**, whose three panels
carry everything the four had, including the open-loop → closed-loop bridge that
was panel (c) of `fig01`.

| Dropped | Why | Where its content now lives |
|---|---|---|
| `fig01_selection_reversal` | (a),(b) duplicate the ladder block; (c) duplicates two points of the Pareto plane | Figure 1a/1b/1c |
| `fig-ladder-scatter` | same 240 rows, same two axes as `fig1_conditioning_vs_error` | Figure 1a (the scatter, with the gate encoded as marker fill) |
| `fig-methods-design` | **fails the "information the text does not carry" test** — see below | nothing; the prose already states all four barriers |
| `fig-knockin-distribution` | same mechanism block, same season, same 20 replicates as the λ sweep | Figure 3c |

**On the methods schematic.** Its declared payload was the four information
barriers. Each is already an explicit sentence: year separation and the
post-freeze 2014–2017 block in §2.1 (`02-methods.tex:58–62`); "No closed-loop
quantity enters it" in §2.5 (`02-methods.tex:218`); heuristic tuning "selected on
the training seasons 2018–2019 only, the test seasons taking no part in
selection" in §3.2 (`03-results.tex:136`). A diagram that restates four sentences
is a fifth statement of them. Dropped — this is the one figure that could be
restored at zero cost to the argument if a reviewer asks for a design overview.

**Deviations from the editorial recommendation.** Two, both small:

1. Figure 1 is given a **third panel** (closed-loop margin of the two libraries
   that reached closed loop). Without it, dropping `fig01` would lose the only
   graphic that connects the open-loop selection criterion to the economic
   outcome — which is the paper's thesis. It costs one narrow panel.
2. The knock-in panel is folded into Figure 3, as recommended, which **moves it
   from §4.1 (Discussion) to §3.5 (Results)**. This is an improvement rather than
   a side effect: MDPI discourages new data in the Discussion, and §4.1 then
   argues from a cross-reference, consistent with the three passages already
   converted that way (REMAINING.md §5 item 9).

---

## Global conventions

- **Dedup key**, applied before any average (`_plotstyle.dedup`):
  closed-loop pools `(method, seed, test_year)`; `n2_tune` `(block, seed, test_year)`;
  ladder `(variant, degree, optimizer, denoise, seed)`;
  mechanism `(block, condition, seed, test_year)`;
  design `(factor, value, seed, test_year, rep)`.
- **Abort rule** (`_plotstyle.usable`): drop `stop_reason == "solver_aborted"`,
  or where that column is absent, `truncated AND solver_failures >= 100`.
  A simulator-terminated season is **kept** — it is an economic outcome.
- **Colour**: Okabe–Ito. Libraries fixed at raw = blue, physics-no-cross =
  orange, physics = vermilion, in every panel of every figure.
- **Type**: serif, 8 pt base, 7 pt ticks and legends. Widths 8.5 cm / 17.5 cm.
  Output vector PDF plus 600 dpi PNG, TrueType embedded (`pdf.fonttype = 42`).
- **`*_dagger`** is a run label from the CSVs. Render it as
  "on-policy re-identification" — never as DAgger, expert or imitation
  (REVISION_LOG G-6).
- Wherever a mean and a median disagree, plot **both** (heavy tick = median,
  open symbol = mean). Two figures depend on the reader seeing that gap.

---

## Figure 1 — Selection reversal and conditioning

- **File**: `fig1_selection_and_conditioning.pdf`
- **Label**: `fig:kappa` (unchanged — keeps every existing `\ref` valid)
- **Lives in**: §3.1 (`03-results.tex`)
- **Referenced from**: §1 (`01-introduction.tex:160`, repointed from `fig:reversal`),
  §2.5 (`02-methods.tex:229`, repointed from `fig:ladder`), §3.1 (`03-results.tex:38`)
- **Width**: 17.5 cm, three panels

| Panel | Content |
|---|---|
| (a) | Scatter, one marker per fit: one-step RMSE of `t_in` (x, linear) against 24-h rollout RMSE (y, **log**). Colour = library, marker = optimizer, **open face = fails the 0.05 divergence gate**. Median + IQR cross per library. This is the reversal, shown as raw data. |
| (b) | κ (x, **log**) against one-step RMSE (left y) and median rollout RMSE (right y, log). Per-library means with SD bars. The two curves cross. Annotate κ = 8.21 / 24.52 / 53.43. |
| (c) | Four-season mean closed-loop EPI, SD whiskers: `sindy_mpc_raw_ens` +4.32 (SD 4.08), `sindy_mpc_lowthr` +3.09 (SD 2.71). Third bar for `physics` drawn **empty and hatched**, labelled "not evaluated in closed loop". Do not impute. |

**Source** (a),(b): `ladder_rerun/ladder_rerun.csv` + `ladder_rerun2.csv`
→ `load_ladder(degree=1, denoise="none", optimizers=("stlsq","ensemble"))`.
1440 rows → 120 in block, **n = 40 per library**.

**Source** (c): `priced_main/*.csv` + `priced_dagger/*.csv`
→ `load_priced_pool()`. 707 → 600, **n = 80 per controller**.

**Verified values**: κ 8.2070 / 24.5167 / 53.4254; one-step 1.8616 / 1.7281 /
1.6753 °C; rollout median 2.6683 / 10.5755 / 24.2678 °C; diverged 0.0000 /
0.0204 / 0.0758.

> **SCOPE — must appear in the caption.** The reversal holds in the degree-1,
> undenoised block under sparse estimators (2 of 72 configurations per library).
> Pooled over all 72 labels the **raw** library has the best mean one-step RMSE
> (2.7035 vs 2.9750 vs 3.4544) and there is no reversal. Do not widen it.
> Do not encode `sign_pass`: it is NaN in all 1440 rows — the declared
> transparency gate was never evaluated.

---

## Figure 2 — Pareto plane: margin against constraint pressure

- **File**: `fig2_pareto_margin_violations.pdf` (unchanged)
- **Label**: `fig:pareto` — **Referenced from**: §3.3 (`03-results.tex:185`)
- **Width**: 8.5 cm, single panel

Mean EPI (y) against mean `violation_steps_total` (x), one marker per
controller, SD bars where n > 4. Five non-dominated points joined by a step
line; everything else grey. Label the tuned heuristic explicitly as **dominated**.

**Sources, three harnesses, kept apart deliberately:**

| Controllers | File | Objective |
|---|---|---|
| 8 SINDy-MPC + `nn_mpc` | `priced_main/*.csv` + `priced_dagger/*.csv` | priced |
| `ppo`, `sac`, `oracle_mpc`, `rule_based` (stock) | `final/main.csv` | default |
| `rule_based_tuned` | `n2_tune/tune_rb_n2.csv`, `block == "tuned_test"` | default |

**Verified front** (exactly five): `sindy_mpc_raw_ens` +4.32 / 4130,
`sindy_mpc_lowthr` +3.09 / 3692, `sindy_mpc_dense` +3.08 / 3686,
`sindy_mpc_dense_dagger` +1.37 / 3615, `ppo` +0.45 / 1330.

> **Caveats for the caption.** `dense` and `lowthr` are **one controller under
> two thresholds**, 0.0066 EUR m⁻² and 5 violation steps apart. `dense_dagger`
> owes part of its position to **7 truncated runs of 80**; over completed runs
> its violation lead over `dense` narrows from 71 to 26 steps. Replication is
> unequal: n = 80 for SINDy and RL, 60 for `oracle_mpc` (2022 removed by the
> abort rule), 40 for `nn_mpc`, **4** for either heuristic.

---

## Figure 3 — Sparsity sweep, boiler-term survival, knock-in

- **File**: `fig3_lambda_survival_knockin.pdf`
- **Label**: `fig:lambda`
- **Lives in**: §3.5 (`03-results.tex`)
- **Referenced from**: §3.5 (`03-results.tex:425`), §4.1 (`04-discussion.tex:79`,
  repointed from `fig:disc-knockin` — cite as "Figure 3c")
- **Width**: 17.5 cm, three panels

| Panel | Content |
|---|---|
| (a) | Mean EPI against λ, two curves (priced, default), ±1 SD shaded. 13 levels, 20 seeds each. |
| (b) | Boiler-term survival fraction against λ on the same x-axis. Plus horizontal ticks for per-controller survival in the priced main pool. |
| (c) | Knock-in effect per replicate, two paired strips (default, priced), lines joining the same seed, IQR box, **median as a heavy tick, mean as an open symbol**. |

**Source** (a),(b): `priced_mech/mechanism_pricedMech*.csv` (405 → 400) and
`final/mechanism.csv` (400). Filter `block == "lambda"`, `test_year == 2020`,
n = 20 per level. Survival = `xi_uboil != 0`.

**Source** (b) ticks: `load_priced_pool()` → `boiler_survival()`. Verified:
`conf` 0.15, `raw` 0.50, `raw_ens` 0.55, `conf_dagger` 0.85,
`dense`/`lowthr`/`dense_dagger` 1.00, `nn_mpc` 0.00.

**Source** (c): same two mechanism pools, `block == "knock"`,
`test_year == 2020`, paired on seed, n = 20.

**Verified**: survival falls 0.95 → 0.35 → 0.10 → 0.00 across λ = 0.03, 0.04,
0.05, 0.06 under **both** objectives. Knock-in median **+3.05** (default) and
**+0.21** (priced); means +2.52 and +1.92; positive in 17/20 and 16/20.
Holm-corrected p = 6.4 × 10⁻⁴ and 1.2 × 10⁻³. Knock-out median 0.0000 both ways.

> **RETRACTION GUARD.** +3.05 is the superseded magnitude (REVISION_LOG G-6) and
> may appear **only** beside its +0.21 replacement. Under the priced objective
> the mean is nine times the median — plotting the mean alone would restate the
> retracted number in disguise. The heavy tick must dominate the panel visually.

---

## Figure 4 — Sensitivity: coefficient perturbation and price grid

- **File**: `fig4_sensitivity_perturbation_prices.pdf`
- **Label**: `fig:perturb` — **Referenced from**: §3.8 (`03-results.tex:671`)
- **Width**: 17.5 cm, two panels

| Panel | Content |
|---|---|
| (a) | Run-level EPI strip per perturbation level (0.02 … 0.20), median heavy tick, mean open symbol, early-termination count annotated per level. The mean collapses while the median holds — the failure is a growing lower tail, not a uniform decline. |
| (b) | Price grid: EPI against the nine (fruit price × energy scale) cells, one line per controller, front-runners highlighted. |

**Source** (a): `priced_design/design_pricedDesign*.csv` → `coef_perturbation()`.
307 → 280 dedup, 200 `coef_perturb` rows, 40 per level.
**Verified**: mean +4.11 / +4.03 / +2.96 / −3.86 / −8.13; median +4.47 / +4.35 /
+5.40 / +1.12 / −0.31; early terminations 0 / 0 / 0 / 4 / 12. Span 12.24 mean
against 5.72 median.

**Source** (b): recomputed from `final/main.csv` (`test_year == 2020`) by the
formula in `make_tables.table_prices`, cross-checked against
`final/tables/sensitivity_prices.csv` — agreement to 3.6 × 10⁻¹⁵.

> **TWO LABELS THE CAPTION MUST CARRY.**
> (i) Despite the directory name, `priced_design/` holds **original-objective**
> runs — `experiments_support.py` hard-codes `objective="full"` in every
> supporting block. Never caption panel (a) as priced.
> (ii) The price grid **re-scores** fixed trajectories rather than re-optimising,
> and covers only the ten canonical-wave controllers: **neither raw-library
> controller is in it**. It therefore says nothing about the ranking the paper
> reports. Name both raw controllers as absent, in the panel.

---

## Figure 5 — Corrections waterfall

- **File**: `fig5_corrections_waterfall.pdf`
- **Label**: `fig:disc-corrections` — **Referenced from**: §4.4 (`04-discussion.tex:165`)
- **Width**: 17.5 cm, two panels

| Panel | Content |
|---|---|
| (a) | Raw-library advantage over the heuristic. Start **+5.54**, one descending bar "16-trial tuning of the baseline" **−3.49**, end **+2.06**. Annotate 75/80 wins. |
| (b) | Raw-minus-physics library gap. Start **+3.66** (default objective), descending bar "stage cost priced to the criterion" **−2.43**, end **+1.23** (priced). Annotate 62/80 wins. |

**Source** (a): both ends from `n2_tune/tune_rb_n2.csv` — `stock_test` −1.2264,
`tuned_test` +2.2613 — against `sindy_mpc_raw_ens` +4.3173 from the priced pool.
**Verified to close exactly**: 5.5437 − 3.4878 = 2.0560.

**Source** (b): `n7/main_n7.csv` `sindy_mpc_raw_ens` +4.0718 minus
`final/main.csv` `sindy_mpc_lowthr` +0.4132 = **+3.6585** default; priced pool
+4.3173 − +3.0888 = **+1.2285**. Step −2.4301.

> **DO NOT DRAW THE DRIFT AS A STEP.** Using the canonical `rule_based` from
> `final/main.csv` (−1.2061) for the start bar of (a) gives +5.52 and leaves a
> 0.03 residual. That is cross-harness drift, not an effect. Both ends of (a)
> come from `n2_tune`.
> **DO NOT CALL 75/80 PAIRED.** Both heuristics are deterministic; these are
> one-sample counts against a per-season constant. 62/80 in (b) *is* paired
> (mean +1.2285, median +1.5769, p_Holm = 7.7 × 10⁻⁴).

---

## Graphical abstract — unnumbered

- **File**: `fig-graphical-abstract.pdf` (unchanged)
- **Label**: `fig:graphical-abstract` — **Referenced from**: §5 (`05-conclusions-abstract.tex:19`)
- **Width**: 17.5 cm, two panels

| Panel | Content |
|---|---|
| (a) | The reversal: one-step RMSE (x) against median 24-h rollout RMSE (y, log), marker **area ∝ κ**, arrow raw → physics, annotate κ = 8.2 / 24.5 / 53.4. |
| (b) | The Pareto front, as Figure 2 but stripped of error bars and minor labels. |

**Sources**: identical to Figures 1a and 2. Duplication with the body is
expected and acceptable here — the graphical abstract is front matter, not a
numbered float.

> **TYPESETTING ACTION.** The environment is currently a numbered `figure` sitting
> in §5, so as drawn it would print as "Figure 6". It must move to the MDPI front
> matter, or be made unnumbered in place. Flagged for the next phase.

---

## Provenance guards carried in code

`_plotstyle.py` holds these as docstrings on the loaders so they travel with the
data rather than living only here: the scope limit on the ladder reversal, the
all-NaN `sign_pass` gate, the mislabelled `priced_design` directory, the price
grid's two restrictions, the deterministic-reference test type, the two-harness
stock heuristic, the retracted +3.05 magnitude, and the `*_dagger` naming rule.
