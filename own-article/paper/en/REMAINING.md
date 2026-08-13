# REMAINING — what is still open in `paper_en.tex`

Assembled 2026-08-13 from the five verified sections in `own-article/paper/en/`.
Structural state at assembly: 51/51 environments balanced, 1116/1116 braces,
1958 inline-math delimiters (even), 0 dangling `\ref`, 10 figures and 15 tables
all cited in text, 44 `\cite` keys against 44 `\bibitem` entries with none unused
and none missing.

Everything below is an **open item**, not a defect already fixed. Items fixed
during the assembly consistency pass are listed at the end for the record.

---

## 1. `[UNSOURCED]` markers still in the manuscript

There is exactly **one** unsourced assertion left in the body text.

| # | Location | Claim | What is missing | Options |
|---|----------|-------|-----------------|---------|
| 1 | §2.9 *Reproducibility, provenance and its limits* | Closed-loop $J$ matched in **0 of 180 cells** between a Linux cluster and a Windows workstation, mean $\lvert\Delta\rvert$ 1.33 EUR m⁻², max 11.6, while the Mahalanobis threshold (2.8595) and AUC (0.6625 vs 0.6621) did match | The second machine's wave is **not** under `regen/results`. The figures live only in `paper/REVISION_LOG.md`, `paper/REVISION_PLAN.md` and a session memory note. `regen/results/raw/adapt.csv` was checked and is byte-identical to `final/adapt.csv` at draw = 0, so it is *not* the second machine's run. | **(a)** Re-run the adaptation wave on the second environment and commit it under `regen/results/`, then drop the marker; **or (b)** delete the three numbers and let the sentence rest on the in-tree evidence that already supports it — the deterministic heuristic scoring `-1.2061` in `final/main.csv` against `-1.2264` in `n2_tune/tune_rb_n2.csv` at identical `config_hash`, drifting by up to 0.038 EUR m⁻² per season. Option (b) costs nothing and is defensible today. |

§4.6 (*Limitations*) now **cross-references** this marker instead of repeating it,
so one decision settles both places. Do not resolve one and leave the other.

Two further `[UNSOURCED]` strings appear inside LaTeX comments (the §4 provenance
header and the §1 provenance block) and are pointers to item 1, not separate claims.

Other bracketed placeholders, all in the front matter:
`[AUTHOR ONE]`, `[AUTHOR TWO]`, `[AFFILIATION, …]`, `[CORRESPONDING AUTHOR E-MAIL]`,
and `[ACCESS DATE NEEDED]` in the `openmeteo2023` bibliography entry.

---

## 2. Figures that still need generating

**No figure file exists.** `own-article/paper/en/figures/` has not been created;
all ten `\includegraphics` paths are placeholders. Every panel specification is
already written as a LaTeX comment immediately above its `\begin{figure}`, with
the filter and dedup key; the table below is the index.

| Fig. | Path | Called from | Source CSVs | Filter / dedup |
|------|------|-------------|-------------|----------------|
| 1 | `figures/fig01_selection_reversal.pdf` | §1, `fig:reversal` | `ladder_rerun/ladder_rerun.csv` + `ladder_rerun2.csv`; panel (c) `priced_main/*.csv` + `priced_dagger/*.csv` | (a),(b): `degree==1`, `denoise=="none"`, `optimizer in {stlsq,ensemble}`, dedup on (variant, degree, optimizer, denoise, seed), n = 40/library. (c): dedup on (method, seed, test_year), n = 80/controller |
| 2 | `figures/fig-methods-design.pdf` | §2.1, `fig:design` | — (schematic, no CSV) | Must mark the forbidden arrows: no closed-loop quantity feeds the ladder, test seasons never enter the ladder or the heuristic tuning |
| 3 | `figures/fig-ladder-scatter.pdf` | §2.5, `fig:ladder` | `ladder_rerun/ladder_rerun*.csv` | `degree==1`, `denoise=="none"`; marker fill encodes the 0.05 divergence gate |
| 4 | `figures/fig1_conditioning_vs_error.pdf` | §3.1, `fig:kappa` | `ladder_rerun/ladder_rerun*.csv` | degree-1 undenoised, 20 seeds/config; x = κ on a log scale |
| 5 | `figures/fig2_pareto_margin_violations.pdf` | §3.3, `fig:pareto` | priced pool + `final/main.csv` + `n2_tune/tune_rb_n2.csv` | Dedup (method, seed, test_year); abort rule; join the five non-dominated points, label the tuned heuristic as dominated |
| 6 | `figures/fig3_lambda_sweep_survival.pdf` | §3.5, `fig:lambda` | `priced_mech/*.csv` + `final/mechanism*.csv` | Season 2020 only, 20 seeds/level |
| 7 | `figures/fig4_coef_perturbation.pdf` | §3.8, `fig:perturb` | `priced_design/design_pricedDesign*.csv` | Dedup on (factor, value, seed, test_year, rep) — 307 rows → 280. **Original objective despite the directory name** |
| 8 | `figures/fig-corrections-waterfall.pdf` | §4.4, `fig:disc-corrections` | `n2_tune/tune_rb_n2.csv`, `n7/main_n7.csv`, `priced_main/*.csv`, `final/main.csv` | Panel (a) must take **both** ends from `n2_tune` so the waterfall closes exactly (5.5437 − 3.4878 = 2.0560). The 0.03 residual from mixing harnesses is drift, **not** a step |
| 9 | `figures/fig-knockin-distribution.pdf` | §4.1, `fig:disc-knockin` | `priced_mech/mechanism_pricedMech*.csv` + `final/mechanism*.csv` | `block=='knock'`, `test_year==2020`, n = 20; show median (heavy tick) and mean (open symbol) so the right skew is visible |
| 10 | `figures/fig-graphical-abstract.pdf` | §5, `fig:graphical-abstract` | ladder + priced pools + `final/main.csv` + `n2_tune` | Two panels: the reversal and the front |

**Editorial problem to settle first.** Figures 1, 4 and panel (a) of Figure 10 all
plot the same selection reversal from the same 40 fits per library. Three
renderings of one result invite a "consolidate your figures" review. Recommended:
keep Figure 1 (Introduction) and Figure 10a (graphical abstract), and convert
Figure 4 into the κ-versus-error scatter that Figure 3 currently duplicates — or
drop one of Figures 3 and 4 outright, since both are ladder scatters.

---

## 3. References

The bibliography holds 44 entries in first-citation order. 33 were carried over
from `paper/statya_ru.tex` and reformatted from the Russian GOST-style layout into
MDPI style with no change of content. **Eleven are new and were written from the
notes left in the section files, not from the publications themselves — verify
each against the original before submission:**

`vanhenten1994`, `rawlings2012`, `raissi2019`, `karniadakis2021`, `belsley1980`,
`hjalmarsson2005`, `hersbach2020`, `openmeteo2023`, `wachter2006`, `fiedler2023`,
`ross2011`.

Specific items:

- **`hersbach2020` and `fiedler2023`** carry truncated author lists (`; et al.`).
  MDPI requires full author lists; complete both from the originals.
- **`openmeteo2023`** needs an access date (`[ACCESS DATE NEEDED]`) and a decision
  on whether Open-Meteo is cited as a data service or as the ERA5 archive it
  redistributes. The weather provenance is now verified (see §5 below) —
  `weather_data_methodology.md` names the Open-Meteo Historical archive API over
  ERA5/ERA5-Land, so both citations are correct as used.
- **`ljung1991`** deliberately keeps its key while pointing at the **English 2nd
  edition** (Prentice Hall, 1999), not the Russian translation of 1991 the
  superseded manuscript cited. Rename the key to `ljung1999` if the mismatch
  between key and year is likely to confuse a copy-editor.
- **`ross2011`** already exists in `paper/build_ru/references.bib` under the key
  `ross2011dagger`. If the submission moves to BibTeX, re-key rather than adding a
  duplicate. It is cited in **exactly one place** (§3.7) and **solely to disclaim**
  the DAgger label — it is not an attribution and must never be reintroduced as one
  (REVISION_LOG G-6 struck `ross2011`, `tagliabue2021` and `espin2024` when the
  imitation-learning framing was retracted).
- `veremey2016` from `statya_ru.tex` is not cited in the English manuscript and was
  not carried over.
- If the manuscript moves to `mdpi.cls`, the manual `thebibliography` block must be
  replaced by a `.bib` file; the entries are already in MDPI field order.

---

## 4. What a reviewer will most likely challenge

Ranked by how much of the paper each one moves.

### 4.1 The headline reversal is narrower than the headline

The one-step/multi-step inversion holds in the **degree-1, undenoised, sparse-estimator
block** (2 of 72 configurations per library, n = 40 fits). Pooled over all 72 labels
the raw library has the **best** mean one-step RMSE (2.7035 against 2.9750 and 3.4544),
so there is no reversal at whole-grid scope. Every section now states the scope, and
the held-out block (`holdout/holdout_holdout.csv`) replicates it independently, but a
reviewer who reads only the abstract will feel the claim is broader than the evidence.
**Do not widen it.** SCOPE WARNING comments sit above the claim in §1 and §5.

### 4.2 The economic gap is small against its own dispersion

+4.32 against +3.09 EUR m⁻² is a 1.23 gap with run-level SDs of 4.08 and 2.71, and it
**reverses in 2021** (−1.56 against +0.27). Both facts are in §1 and §3.3. Expect
"is this a real effect?" The defences available are the 62/80 win rate at
$p_{\text{Holm}} = 7.7\times10^{-4}$, the unseen-season block, and the ladder
prediction made before any closed-loop run.

### 4.3 Only two of the three ranked libraries reached closed loop

The full `physics` library has **no controller** in the main comparison. The
closed-loop evidence therefore separates raw from physics-*without*-cross-terms, not
from full physics. Stated in §1 and §4.5. A reviewer may reasonably ask for the
missing arm; it is one 20-seed × 4-season wave.

### 4.4 The comparison against the heuristic is not a paired test

Both rule-based references are deterministic. Every signed-rank test against them is a
**one-sample test against a constant**, and at n = 4 the minimum attainable two-sided
$p$ is 0.125. Disclosed in §2.8, §3.3, §4.6, the `tab:wilcoxon` caption, the `tab:main` note and
the abstract. Nothing to fix, but expect the question.

### 4.5 The Pareto front is softer than "five controllers" sounds

`sindy_mpc_dense` and `sindy_mpc_lowthr` differ by **0.0066 EUR m⁻²** and 5 violation
steps — two front points, one controller under two thresholds — and yet separate at
$p = 0.012$. `sindy_mpc_dense_dagger` owes part of its position to 7 truncated runs of
80; over completed runs its violation lead over `dense` narrows from 71 to 26 steps.
Both caveats are in §3.3, §4.6 and §5.

### 4.6 Objective coverage is uneven, and one directory is mislabelled

Only the main closed-loop comparison and the mechanism block ran under the priced
stage cost; `experiments_support.py` hard-codes `objective="full"` in every supporting
block, so unseen seasons, the h = 8 sweep, the draw axis, design/sensitivity,
adaptation, guard and faults are **default-objective results** — including everything
written to `regen/results/priced_design/`, whose name is wrong. The consequence stated
in §3.8 and §4.6 is that the coefficient- and threshold-sensitivity analyses have
**never** been measured under the priced weights. A reviewer may ask for them.

### 4.7 A pre-registered gate was declared but never evaluated

`EXPERIMENT_PROTOCOL.md` §E2 declares two gates, MPC-embeddability and a
sign-and-dimension transparency check. `sign_pass` is **NaN in all 1440 rows** of the
ladder, so the transparency gate was never run; and the divergence criterion, declared
only qualitatively, was applied as a hard 0.05 threshold hard-coded in
`make_tables.py:318`. §2.5 reports declared-versus-applied honestly. This is a
pre-registration deviation and reviewers of registered work look for exactly this.

### 4.8 The objective is a proxy, and "season" is 60 days

The surrogate carries no crop state, so terminal biomass cannot be priced and a
controller that harvests inside the window is rewarded over one that builds a crop for
a later one. The "season" is the 60-day window from 1 March, not a growing season.
Both in §2.2 and §1. A horticultural reviewer will press on whether a 60-day margin
means anything agronomically.

### 4.9 The two reinforcement-learning agents are trained on a different objective

`gl_gym/components/rewards.py` returns scaled profit minus scaled violation penalties;
EPI sums the unscaled `profit` field alone. PPO and SAC therefore optimise a penalised
reward and are scored on the unpenalised $J$ — which partly explains PPO's position on
the violation axis and hence its Pareto-front membership. Disclosed in §2.2. Expect
"your RL baselines are handicapped/advantaged".

### 4.10 Two harnesses are mixed inside Table 3

The main comparison table (`tab:main`) quotes the stock heuristic from
`final/main.csv` (−1.21, 2810 violation steps)
and the tuned heuristic from `n2_tune` (+2.26, 4339), because the tuning gain must be
internally consistent within one harness. The 0.02 EUR m⁻² and 3-step discrepancies
are disclosed in the table note and are themselves evidence for §2.9. It is honest but
a reviewer may still ask for one harness throughout — which would require re-running
the tuned setpoints in the main harness.

### 4.11 Replication is unequal, and it is not always stated in the same sentence

20 seeds for the SINDy and RL controllers; **10 seeds / 40 runs** for `nn_mpc` under
the priced objective (20 under the default); **n = 4** for either heuristic; **n = 60
over three seasons** for `oracle_mpc`, whose whole 2022 season was removed by the
solver-abort rule. Supporting blocks use 5–10 seeds. All stated, but scattered.

### 4.12 The price grid excludes the paper's own leading controller

`final/tables/sensitivity_prices.csv` covers only the ten canonical-wave controllers;
**neither raw-library controller is in it**, and it re-scores rather than re-optimises.
So the "two distinct controllers win across nine price points" statement says nothing
about the ranking actually reported. Restriction stated in §3.8 and §4.6.

### 4.13 Cross-environment reproducibility

Closed-loop margins do not reproduce across operating systems. See item 1 of this
document — the strong figures are unsourced; the weak in-tree evidence is solid.

### 4.14 Wording that sits next to a retracted claim

The abstract and Finding 3 say the raw-library controller "led in all four" of the
**unseen** seasons 2014–2017. That is true and verified. The superficially similar
claim "first in all four seasons" about the **main** test seasons 2020–2023 was
retracted (REVISION_LOG G-6) and is false — 2021 reverses. Keep the qualifier "never
used at any stage" adjacent to the phrase in every future edit, or a copy-editor will
collapse the two.

### 4.15 Length

| Part | Words | Note |
|------|-------|------|
| Abstract | **248** | MDPI limit is **200** — a hard submission blocker |
| Introduction | 1425 | |
| Materials and Methods | 3035 | |
| Results | 4083 | |
| Discussion | 2382 | |
| Conclusions | 681 | |
| **Body total** | **11 640** | excludes floats, equations, abstract and bibliography |

The abstract has not been trimmed here, because every sentence in it carries either a
sourced number or a caveat that a verification pass put there deliberately. The
lowest-cost 48 words, in order of least damage: the opening framing sentence (38
words) compresses to roughly 25; "better in 75 of 80 runs" can go while "against this
deterministic reference" stays; "also the sparser one" can move to the Conclusions.
**Do not** cut "in the first-order, undenoised block under sparse estimators",
"against three comparators", "deterministic reference", or the Pareto sentence — each
is a scope limit that was added to fix an overstatement.

---

## 5. Fixed during the assembly consistency pass (for the record)

1. **Tuning-budget attribution.** Four places said the heuristic was tuned under
   "the budget the learned controllers received". `experiments_support.py:537` matches
   the **reinforcement-learning agents only**; the MPCs received no hyper-parameter
   search at all, and the h = 8 sweep shows the asymmetry runs *against* the MPCs.
   Corrected in §3.2, the `tab:tune` caption, §4.4, the `tab:disc-defects` repair row
   and the abstract; §1 and §2.3 were already right.
2. **Condition number quoted at two values.** §4.1 quotes 8.2 / 25.4 / 56.2 from the
   **held-out** block while §1, §3.1 and §5 quote 8.2 / 24.5 / 53.4 from the **ladder**.
   Both recomputed and correct; §4.1 now names its block, cross-references §3.1 and
   states that the two sets must not be mixed. The same applies to its one-step
   (1.84→1.64), rollout (2.62→21.88) and divergence (0.000→0.078) figures.
3. **Arithmetic error.** The physics/term-kept cell of the 2×2 is **2.3647**, which
   rounds to **+2.36**, not +2.37. Corrected in the `tab:twobytwo` cell, the §3.5 prose
   and §4.1; §1 already had +2.36. Recomputed from the 600-row priced pool.
4. **Cross-environment claim asserted in one section and flagged in another.** §2.9
   stated the 0-of-180 figures as fact while §4.6 marked them `[UNSOURCED]`. §2.9 now
   carries the marker and §4.6 cross-references it.
5. **Weather provenance.** A note in §1 speculated that the weather came from the
   GreenLight-Gym stock pipeline (NASA POWER, PCHIP-resampled) and flagged §2.1 as
   possibly mis-citing. Verified against `own-article/weather_data_methodology.md` and
   `make_weather.py`: it is the **Open-Meteo Historical archive API over ERA5/ERA5-Land**,
   hourly, linearly resampled to 5 min, with sky temperature derived by Brunt clear-sky
   emissivity blended by cloud cover. §2.1 was correct; the note is retracted and the
   verified provenance is now recorded in both files.
6. **Stale provenance warning.** §3.3 warned that `main_pricedNN2.csv` and
   `main_pricedNN3.csv` were untracked in git, making the `nn_mpc` row non-regenerable.
   All sixteen files under `priced_main/`, `priced_dagger/`, `priced_mech/` and
   `priced_design/` are now tracked; the warning is marked resolved.
7. **Row-count provenance.** The priced pool comment said 615 rows before dedup; the
   eight source files hold **707**, because `main_priced_seeds0-3.csv` was omitted from
   the list. It is a strict subset after dedup, so no value changes; both figures are
   now recorded. Dedup 707 → 600 and the abort rule removing 0 rows were re-verified.
8. **Uncited floats.** `fig:design`, `fig:ladder`, `fig:disc-corrections`,
   `fig:disc-knockin`, `fig:graphical-abstract` and `tab:headline` had labels but no
   in-text reference; `eq:mpc` had none either. All now referenced.
9. **Results/Discussion duplication.** Three passages restated Results numbers
   verbatim in the Discussion: the ladder dominance triple (§4.2), the λ-sweep
   endpoints (§4.3) and the guard statistics (§4.6). Each now argues from a
   cross-reference. No caveat was removed — all three sets of numbers remain in
   Results, where they belong.
10. **Rounding.** Retained terms of the frozen recipe were 28.25 in §3.1 and 28.3 in
    §4.3; both now 28.25.
11. **Terminology, re-checked across the assembled file.** No "grey-box" for the
    low-threshold variant (the only two occurrences deny the label); no "DAgger",
    "expert" or "imitation" framing (the only occurrences are explicit disclaimers, the
    `*_dagger` run labels, which are the names in the CSVs, and the word "limitation");
    no "twelve controllers"; no "first in all four seasons"; no "only the raw library
    beats the tuned heuristic"; +3.05 appears only as the superseded value beside its
    +0.21 replacement.

---

## 6. Regenerating this manuscript

`paper_en.tex` is assembled by concatenation from the five section files, with the
Abstract and Keywords lifted into the front matter and the bibliography emitted in
first-citation order. **Edit the sections, not `paper_en.tex`** — direct edits are lost
on the next assembly.

```
python own-article/paper/en/assemble_paper_en.py   # rebuild paper_en.tex
python own-article/paper/en/verify_paper_en.py     # structural + terminology check
```

Both scripts use absolute paths and can be run from anywhere. `assemble_paper_en.py`
holds the preamble, the placeholder author block and all 44 bibliography entries;
`verify_paper_en.py` reproduces the structural counts quoted at the top of this file
and re-runs the terminology guard (grey-box / DAgger / expert / imitation / twelve /
the two retracted claims). Neither has been run through a LaTeX compiler — **no
TeX distribution is installed on this machine**, so the structural checks are a
substitute for, not a confirmation of, a successful `pdflatex` run. Compile once
before submission.
