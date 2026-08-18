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

1. Figure 1 is given panels beyond the two the editorial recommendation
   allowed. Without them, dropping `fig01` would lose the only graphic that
   connects the open-loop selection criterion to the economic outcome — which
   is the paper's thesis. **Updated 2026-08-14**: this is now a 2 × 2 figure,
   because the closed-loop result no longer follows the conditioning series
   and both the open-loop ordering (which κ predicts) and the closed-loop one
   (which it does not) have to be visible for the correction to read.
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

## Figure 1 — Selection reversal and survival of the actuator pathway

> **REBUILT 2026-08-14.** The previous specification of this figure — three
> panels, conditioning as the mechanism, `physics` "not evaluated in closed
> loop" — is superseded. `regen/results/phys_lib/` closed that gap on
> 2026-08-13 and the closed-loop series turned out **non-monotone in κ**, so
> the conditioning mechanism, the monotone-in-κ claim and the old panel (c)
> are all retracted (REVISION_LOG 2026-08-13). The specification below is what
> `make_fig1.py` now draws.

- **File**: `fig1_selection_and_conditioning.pdf` (legacy stem — kept so that
  `03-results.tex:167` and every `\ref` stay valid; the name now understates
  the figure)
- **Label**: `fig:kappa` (unchanged)
- **Lives in**: §3.1 (`03-results.tex`)
- **Referenced from**: §1 (`01-introduction.tex:160`, repointed from `fig:reversal`),
  §2.5 (`02-methods.tex:229`, repointed from `fig:ladder`), §3.1 (`03-results.tex:38`)
- **Width**: 17.5 cm, **2 × 2**, four panels

| Panel | Content |
|---|---|
| (a) | Scatter, one marker per fit: one-step RMSE of `t_in` (x, linear) against 24-h rollout RMSE (y, **log**). Colour = library, marker = optimizer, **open face = fails the 0.05 divergence gate**. Median + IQR cross per library. The reversal, as raw data. Untouched by the correction. |
| (b) | What κ **does** buy: κ (x, **log**) against one-step RMSE (left y) and median rollout RMSE (right y, log). Monotone and clean — but **open loop only**. Annotate κ = 8.2 / 24.5 / 53.4. |
| (c) | The correction: four-season closed-loop EPI (y) against **boiler-term survival** (x) for the three nested libraries under the matched recipe, **plus the 17-feature term-deletion probe** `physics_no_tuboil` (green), which lands between at survival 0.40 — the falsification of the bilinear-detour reading, drawn. κ printed at each point, and a grey path joins them **in order of rising κ** so the reader sees conditioning order them wrongly. Open diamonds repeat the comparison under STLSQ (3 of 4 — see below). |
| (d) | Why `physics_no_cross` is the one that fails: identified \|ξ_uBoil\| per seed against the 0.05 cut, **symlog** so a cut coefficient sits at exactly 0. |

**Source** (a): `ladder_rerun/ladder_rerun.csv` + `ladder_rerun2.csv`
→ `load_ladder(degree=1, denoise="none", optimizers=("stlsq","ensemble"))`.
1440 rows → 120 in block, **n = 40 per library**.
**Source** (b): the same loader restricted to `optimizers=("ensemble",)` —
60 rows, n = 20 — so that (b) and (c) describe the *same* estimator.

**Source** (c),(d): `load_library_pool()` = `priced_main/*.csv` +
`priced_dagger/*.csv` + `phys_lib/main_physlib*.csv`, 867 → 760 rows,
**plus** `load_notuboil_pool()` = `notuboil/main_notuboil*.csv`, 160 rows
(joined inside `library_one_factor` only — the probe is not a benchmark
controller and never enters the Pareto pools).
The one-factor set is `LIBRARY_ONE_FACTOR`: degree 1, no denoising,
**threshold 0.05**, only `feature_variant` differing —
`sindy_mpc_raw_ens` / `sindy_mpc_conf` / `sindy_mpc_phys_ens` /
`sindy_mpc_notuboil_ens`, n = 80 each, **zero truncated runs**.

**Verified values.** κ 8.2070 / 24.5167 / 53.4254 (identical across optimizers);
one-step 1.8611 / 1.7284 / 1.6750 °C; rollout median (ensemble) 2.6652 /
10.9872 / 24.2661 °C; diverged 0.0000 / 0.0208 / 0.0767.
Closed loop: EPI **+4.3173 / +0.2818 / +2.7540**, seed-level SE 0.1989 / 0.6478 /
0.2778, median +5.2855 / −1.2543 / +3.3856; survival **0.55 / 0.15 / 0.55**
(Wilson 95 %: [0.34, 0.74] / [0.05, 0.36] / [0.34, 0.74]).
STLSQ replicate: raw +3.8333 at 0.50, physics +2.4762 at 0.55.
**Deletion probe** (`physics_no_tuboil`, 17 of 18 terms, `t_uBoil` removed):
κ 52.28 (49.4–57.3 across seeds, `notuboil/ladder_notuboil.csv`), rollout median
24.17 °C, diverged 0.084; closed loop EPI **+2.11 ± 3.51** (ensemble) and
**+2.28 ± 3.55** (STLSQ), survival **0.40** (8/20, Wilson [0.22, 0.61]).
The registered detour prediction was collapse onto `physics_no_cross`
(≈ +0.3 / ≈ 0.15) — falsified 2026-08-18 (`notuboil/analysis_notuboil.md`).
Surviving \|ξ_uBoil\|, median 0.0685 / 0.0609 / 0.1430; libraries 11 / 14 / 18
terms, and only `physics` contains the bilinear `t_uBoil`
(`article_experiment_utils.py`, parsed by `library_feature_names()`).

> **THREE THINGS THE CAPTION MUST CARRY.**
> (i) **Scope of the reversal.** It holds in the degree-1, undenoised block
> under sparse estimators (2 of 72 configurations per library). Pooled over all
> 72 labels the **raw** library has the best mean one-step RMSE (2.7035 vs
> 2.9750 vs 3.4544) and there is no reversal. Do not widen it. Do not encode
> `sign_pass`: it is NaN in all 1440 rows.
> (ii) **Survival is not a universal ranking variable.** It orders these three
> because they differ in nothing else. Across the wider pool it does not:
> `sindy_mpc_conf_dagger` survives at 0.85 and scores +1.66, below
> `sindy_mpc_raw_ens` at 0.55.
> (iii) **The STLSQ row is 2 of 3.** No `physics_no_cross` controller exists at
> STLSQ/0.05 — `dense` is 1e-3 and `lowthr` 1e-6. Never draw or imply a third
> diamond.
> **AND ONE THING PANEL (d) MUST NOT CLAIM.** A cut coefficient is written as
> exactly 0.0, so the pre-threshold magnitude of a cut term is not in these
> files. The panel may say how far the *survivors* sit above the cut; it may
> not say how far the cut ones sat below it.
> **DO NOT RESTORE** the "not evaluated in closed loop" bar, the κ-as-mechanism
> framing, or any monotone-in-κ statement about closed-loop EPI.

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
| 7 SINDy-MPC + `nn_mpc` | `priced_main/*.csv` + `priced_dagger/*.csv` | priced |
| `sindy_mpc_phys`, `sindy_mpc_phys_ens` | `phys_lib/main_physlib.csv` | priced |
| `ppo`, `sac`, `oracle_mpc`, `rule_based` (stock) | `final/main.csv` | default |
| `rule_based_tuned` | `n2_tune/tune_rb_n2.csv`, `block == "tuned_test"` | default |

> **FIFTEEN controllers, via `load_library_pool()` — not `load_priced_pool()`.**
> Until 2026-08-14 this figure called `load_priced_pool()` and therefore drew
> **thirteen**, while §3.3 and the caption both said fifteen. The front is
> unchanged at five members: `sindy_mpc_phys_ens` (+2.75, 4193) and
> `sindy_mpc_phys` (+2.48, 4174) are dominated by `sindy_mpc_raw_ens` (+4.32,
> 4130) on **both** axes, which is a stronger statement than "off the front" and
> is what the text says about them. `make_fig2.py` now raises rather than falling
> back if a controller reaches the pool without a short label or a label
> placement, so the same silent divergence cannot recur.

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
| (b) | Boiler-term survival fraction against λ on the same x-axis, plus a right-hand strip of per-controller survival, one tick per (survival, library) group, coloured by library. |
| (c) | Knock-in effect per replicate, two paired strips (default, priced), lines joining the same seed, IQR box, **median as a heavy tick, mean as an open symbol**. |

**Source** (a),(b): `priced_mech/mechanism_pricedMech*.csv` (405 → 400) and
`final/mechanism.csv` (400). Filter `block == "lambda"`, `test_year == 2020`,
n = 20 per level. Survival = `xi_uboil != 0`.

**Source** (b) ticks: `load_library_pool()`, survival taken per SEED (one fit
per seed), so `phys`/`phys_ens` appear alongside the eight of the priced
comparison. Verified: `conf` 0.15, `raw` 0.50,
`raw_ens`/`phys`/`phys_ens` 0.55, `conf_dagger` 0.85,
`dense`/`lowthr`/`dense_dagger` 1.00.

> **`nn_mpc` CARRIES NO TICK.** An earlier version of this line recorded its
> survival as `0.00`. That was a NaN read as zero: `xi_uboil` is empty in **all
> 65 of its rows** (0 non-null), because the neural surrogate has no thresholded
> coefficients at all. Drawing it at 0.00 would assert a measured loss of the
> boiler term where nothing was ever measured. Corrected 2026-08-14.

**Source** (c): same two mechanism pools, `block == "knock"`,
`test_year == 2020`, paired on seed, n = 20.

**Verified**: survival falls 0.95 → **0.35** → 0.10 → 0.00 across λ = 0.03,
0.04, 0.05, 0.06 under the **priced** objective and 0.95 → **0.30** → 0.10 →
0.00 under the default one. (The earlier "0.35 under both" was wrong at
λ = 0.04; corrected 2026-08-14.) Knock-in median **+3.05** (default) and
**+0.21** (priced); means +2.52 and +1.92; positive in 17/20 and 16/20;
Wilcoxon p = 3.2 × 10⁻⁴ and 5.9 × 10⁻⁴. Knock-out median 0.0000 both ways,
positive in 1/20 both ways.

> **NAME THE FAMILY WHENEVER A CORRECTED p IS QUOTED.** Holm over the two
> knock-in tests gives 6.4 × 10⁻⁴ for both; Holm over the four mechanism tests
> (knock-in and knock-out × two stage costs), which is what the figure draws,
> gives **1.3 × 10⁻³** and **1.8 × 10⁻³**. The earlier pair "6.4 × 10⁻⁴ and
> 1.2 × 10⁻³" mixed the two families and is not reproducible as one.

**Axis note.** The 13 λ levels are drawn **evenly spaced, not on a log axis**:
on a log axis four of the six decades carry a flat plateau and the collapse —
which is the point of the panel — occupies two millimetres. Every level is
tick-labelled and the axis label says so.

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

- **File**: `fig-graphical-abstract.pdf` — **REDRAWN 2026-08-14**
- **Label**: `fig:graphical-abstract` — **Referenced from**: §5 (`05-conclusions-abstract.tex:19`)
- **Width**: 17.5 cm, **three** panels

| Panel | Content |
|---|---|
| (a) | The selection reversal: one-step RMSE (x) against median 24-h rollout RMSE (y, log), arrow raw → physics, divergence rate annotated per library. Marker area is **uniform**. |
| (b) | The non-monotonicity and what tracks it: the three nested libraries **plus the 17-feature deletion probe** on an ordinal x axis in κ order (κ printed under each tick: 8.2 / 24.5 / 52.3 / 53.4, read from the ladder), closed-loop EPI tracing a **V** on the left axis with seed-level SE, boiler-term survival (0.55 / 0.15 / 0.40 / 0.55) overlaid on the right axis reproducing the V. The probe staying at the full library's level is the falsified bypass reading, drawn. |
| (c) | The Pareto front, as Figure 2 but with only the five front members labelled. |

**Sources**: (a) as Figure 1a, (b) as Figure 1c, (c) as Figure 2. Duplication
with the body is expected and acceptable here — the graphical abstract is front
matter, not a numbered float.

> **DO NOT RESTORE** the two-panel version or the **κ-as-marker-area** encoding
> in panel (a). Both were drawn when ill-conditioning was the paper's mechanism.
> That mechanism is retracted: κ is monotone (8.2 / 24.5 / 53.4) while
> closed-loop margin is not (+4.32 / +0.28 / +2.75), so encoding κ as a visual
> weight asserts the retracted claim. The committed PDF contradicted its own
> caption from 2026-08-13 until the redraw.
>
> `make_fig6.py` ends in an **eight-item self-check** that fails the build if the
> caption's claims stop holding: κ monotone, EPI not monotone, EPI V-shaped,
> survival reproducing the V, survival tying the two outer libraries, the
> deletion probe landing in survival order, the deletion probe keeping
> physics-level EPI, and the front having five members.

> **SCOPE GUARD for panel (b)**, carried on the panel face: survival ranks
> *these four* libraries because nothing else differs between them (the probe
> removes exactly one feature from `physics`). It does not
> rank the wider pool — `conf_dagger` survives at 0.85 and scores +1.66, below
> `raw_ens` at 0.55. The bilinear-detour *explanation* is **falsified**
> (2026-08-18) and the probe that falsified it is drawn at κ = 52.3.

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
