# REMAINING — open items in `paper_en.tex`

Rewritten **2026-08-14**, after the mechanism rework that followed the
full-`physics` closed-loop wave (`regen/results/phys_lib/`).

**Structural state at this assembly** (`verify_paper_en.py`):
51/51 environments balanced · 1438/1438 braces · 2400 inline-math delimiters
(even) · 0 dangling `\ref` · **6 figures and 16 tables, all cited** ·
44 `\cite` keys against 44 `\bibitem` entries, none unused, none missing,
in first-citation order · abstract **198** words (MDPI limit 200) ·
15 699 words of narrative prose.

All six `\includegraphics` targets exist on disk and were regenerated from the
CSVs in this pass.

---

## 0. What changed in this pass, and why the register was rewritten

The previous REMAINING.md described a manuscript with ten unwritten figures and
an ill-conditioning mechanism. Both are gone. The mechanism is now
**actuator-term survival**; conditioning survives *only* as a predictor of
open-loop multi-step stability. Every item below is genuinely open — nothing
listed here is already done.

---

## 1. CLOSED — verified, no action

| Area | State |
|---|---|
| **Conditioning as the closed-loop mechanism** | Retracted everywhere it was load-bearing. §1 contribution (ii) now states the non-monotonicity and names the retraction; §3.1 scopes κ explicitly to open loop; §3.5 opens on survival; §4.1 breaks the chain in six moves; §5 lists it as the refuted explanation. κ remains as an open-loop diagnostic and as a reported column — that is correct and must not be removed. `grep -i "squeez"` returns nothing: the §4.1 paragraph that contradicted the new Finding 4 is gone. |
| **Controller count** | Fifteen throughout (§1 ×3, §2.3, §3.3, §4.4, §4.6, §5). The λ-grid's **thirteen levels** in §4.3 is a different quantity and is correct — `regen_config.LAMBDA_GRID` has exactly 13 entries. Do not "fix" it. |
| **Holm family** | 15 everywhere, declared at every corrected level. Recomputed: raw-vs-physics `4.6e-4` (was `7.7e-4` at family 13), heuristic `6.3e-11` (was `6.9e-11`). No controller crossed 0.05 when the family grew. |
| **Knock-in Holm family** | Now declared at all three sites. §1 and §4.1 said `1.2e-3` without naming the family; both now say "over the two knock tests", and §4.1 also gives `1.8e-3` for the four-contrast family that Figure 3 uses. |
| **Figure 2** | Was built from `load_priced_pool()` and drew **13** controllers while its caption and §3.3 said fifteen. Now `load_library_pool()`; front unchanged at five members. `make_fig2.py` raises if a controller arrives without a short label or a label placement. |
| **Graphical abstract** | Was a two-panel drawing with κ encoded as marker area, contradicting a caption already rewritten to three panels. Redrawn: (a) reversal, (b) the V against monotone κ with survival overlaid, (c) the front. Ends in a six-item self-check that fails the build if any caption claim stops holding. Same 13→15 fix as Figure 2. |
| **`figures/fig5_corrections_waterfall.pdf`** | Existed only as `fig5.pdf`. `make_fig5.py` now writes both stems, as `make_fig1.py` and `make_fig6.py` already did. |
| **`nn_mpc` survival** | `SPEC.md` recorded `0.00`; `xi_uboil` is empty in **all 65 of its rows**, so that was a NaN read as zero. Corrected in SPEC; the figure already drew no tick. |
| **`[UNSOURCED]` markers** | Zero remain. The Linux↔Windows magnitudes were **removed**, not softened — that wave is not under `regen/results` and no second machine exists. The claim now reads "never measured across environments", which is true and sourced. |
| **Bibliography** | 44 entries verified against publisher records; 26 DOIs added; four keys renamed to match the version of record. |

---

## 2. OPEN — must be resolved before submission

### 2.1 Author identity and back matter *(only the authors can supply these)*

Nothing has been invented anywhere. Seven red `[[…]]` markers remain:

| Location | Marker |
|---|---|
| Title block | `[[AUTHOR 1 — FULL NAME REQUIRED]]`, `[[AUTHOR 2 — FULL NAME REQUIRED]]`, `[[ADD OR DELETE AUTHORS AS REQUIRED]]` |
| Title block | `[[ORCID REQUIRED]]` ×2 |
| Title block | `[[CORRESPONDING AUTHOR E-MAIL REQUIRED]]` |
| Title block | `[[AFFILIATION 1 REQUIRED …]]`, `[[AFFILIATION 2 REQUIRED, OR DELETE …]]` |
| Author Contributions | `[[REQUIRED — NOT SUPPLIED.]]` — CRediT roles per author |
| Funding | `[[REQUIRED — NOT SUPPLIED.]]` — every funder with grant numbers, or the MDPI "received no external funding" wording |
| Conflicts of Interest | `[[REQUIRED — NOT SUPPLIED.]]` — every author must declare |

IRB and Informed Consent are already correctly "Not applicable" (simulator
study, no human or animal subjects). Do not change those to placeholders.

### 2.2 Data availability DOI — **hard blocker**

The Data Availability Statement is otherwise complete: it names `config_hash
637c6b535a9e`, the per-wave `regen_manifest.json`, the eight-block regeneration
sequence, `--merge` + `make_tables.py` → `NUMBERS.md`, the `verify_regen.py`
gates, the `repro.py --selftest` digests, `gl_gym` 0.3.1 and the Open-Meteo/ERA5
weather. It lacks **a public, citable archive location**. Deposit the results
tree (Zenodo or equivalent) and insert the DOI. This is the one item that
genuinely prevents submission.

### 2.3 The graphical abstract prints as "Figure 6"

It is a numbered `figure` in §5, so the standard `article` class numbers it. At
submission either move it into the MDPI front matter or unnumber it in place.
Both fixes are recorded in `MDPI_SUBMISSION.md` §5. Its duplication with
Figures 1a and 2 is deliberate and acceptable **only** as front matter — as a
numbered body float it would read as a third rendering of the same results.

### 2.4 MDPI class conversion

`MDPI_SUBMISSION.md` carries the full mapping: `article` → `Definitions/mdpi`,
front/back-matter placement, and the bibliography-to-BibTeX notes including the
`ross2011dagger` re-key warning. Note the abstract sits at **198 of 200 words** —
two words of headroom is not a margin, so any addition must be paid for by a
deletion.

---

## 3. OPEN — scientific, and honestly disclosed rather than blocking

These are stated as limitations in the manuscript. They are listed here so they
are not mistaken for oversights.

### 3.1 The named experiment that was not run

Delete the single bilinear `t_uBoil` feature from the 18-feature `physics` set
→ a 17-feature library, same optimiser and threshold, 4 seasons × 20 seeds
closed loop. If the cross term is the detour, margin should fall back toward
`+0.28` while conditioning stays near `physics`. Until then the bilinear-detour
reading is flagged throughout as **a reading, not a result** — in §1
contribution (iv), §3.5, §4.1 and the Figure 1 and 6 scope guards.

The existing `cross` knock-out block **cannot** substitute: it edits coefficients
on a λ = 10⁻⁶ fit whose baseline boiler survival is 1.00 in all 20 replicates, so
sparsification never severs the pathway there. This is stated in §3.5 and §4.1.

### 3.2 The mechanism rests on three points, on one estimator

The three-library series exists as a complete triple **only under the ensemble
estimator**. Under STLSQ at threshold 0.05 only the two endpoints were run
(`+3.83` raw, `+2.48` full physics), because the two `physics_no_cross` STLSQ
recipes are frozen at 10⁻³ and 10⁻⁶. So the raw-over-physics *direction*
replicates on a second estimator but the *non-monotonicity* does not exist as a
three-point series there. Scoped that way in §1, §2.3, §3.5 and §4.6.

Survival is **measured, not manipulated** at library level; the only randomised
contrast anywhere is the `+0.21` ablation. A fourth library could disturb the
pattern as the third disturbed the one before it.

### 3.3 Cross-environment reproducibility was never measured

No wave records an environment: `repro.py` can emit a fingerprint, but the `env`
block is absent from **all 20** `regen_manifest.json` files, from every
`run.log`, and `final/NUMBERS.md` prints `env_hash: n/a`. Waves are separated
only by `git_sha` (11 distinct values at one `config_hash`). The in-tree evidence
that survives is the deterministic heuristic drifting between two harnesses at
identical `config_hash`: `-1.2061` (`final/main.csv`) against `-1.2264`
(`n2_tune/tune_rb_n2.csv`), per-season |Δ| 0.0031 / 0.0134 / 0.0266 / 0.0381.

**Do not restore** the stronger figures (0 of 180 cells, mean |Δ| 1.33, max 11.6)
without committing that wave under `regen/results/`.

### 3.4 Standing scope limits

- No crop state in the surrogate, so terminal biomass is unpriced and the MPC
  objective is necessarily a proxy.
- Mechanism experiments are single-season (2020) and replication is unequal
  across controllers (`nn_mpc` 10 seeds / 40 runs; `oracle_mpc` has no 2022).
- One front point (`sindy_mpc_dense_dagger`) rests partly on 7 truncated runs;
  two others are one controller at two thresholds, 0.0066 EUR m⁻² apart.
- Simulation only, one location, one planting date, one computing environment.

---

## 4. Standing guards — do not undo

Each of these was a defect once and is now held in place by a comment, a
docstring or a build-time check.

| Guard | Where it lives |
|---|---|
| κ is not the closed-loop mechanism | §1 (ii), §3.1, §3.5, §4.1, `SPEC.md` Fig. 1 and graphical abstract, `make_fig6.py` self-check |
| `phys_lib/main_physlib.csv` loaded **explicitly** | A `main_phys*.csv` glob also picks up the 2-row smoke file `main_physchk.csv`; sorted-first dedup then silently returns `+2.65` instead of `+2.75`. Guarded in `_plotstyle.load_physlib_pool` and the §1 provenance block |
| `+3.05` is a **superseded** effect size | Permitted only in explicit before/after correction framing (§3.5 prose, §4.1 retraction sentence, Table 14 row). Never as a live comparator |
| Survival gates but does not order | §1 (iv), §3.5, §4.1, panel guards on Figures 1c and 6b. `conf_dagger` survives at 0.85 and scores `+1.66`, below `raw_ens` at 0.55 |
| No grey-box / DAgger / expert framing | `verify_paper_en.py` terminology guard. Current hits are all denials ("not a grey box", "not DAgger", "not an expert"), `*_dagger` run labels, and "limitation" false positives |
| "First in all four seasons" stays retracted | The raw library loses 2021 (`-1.56` against `+0.27`); stated in §1 and §3.3 |
| One-step reversal is scope-limited | Holds in the degree-1 undenoised sparse block only. Pooled over all 72 ladder labels the raw library has the best mean one-step RMSE and there is no reversal. Carried on the face of Figures 1a and 6a |
| Deterministic reference carries no error bar | The heuristic is `n = 1` per season; every test against it is one-sample against a constant, not paired |

---

## 5. How to re-verify

```bash
cd own-article/paper/en
PYTHONIOENCODING=utf-8 python figures/make_fig1.py   # 41/41 checks
PYTHONIOENCODING=utf-8 python figures/make_fig2.py
PYTHONIOENCODING=utf-8 python figures/make_fig3.py   # 63/63 checks
PYTHONIOENCODING=utf-8 python figures/make_fig4.py
PYTHONIOENCODING=utf-8 python figures/make_fig5.py   # waterfall closes to 0.00
PYTHONIOENCODING=utf-8 python figures/make_fig6.py   # 6/6 caption self-check
PYTHONIOENCODING=utf-8 python assemble_paper_en.py
PYTHONIOENCODING=utf-8 python verify_paper_en.py
```

Edit the **section files** and the assembler. `paper_en.tex` is generated and is
overwritten on every assembly.
