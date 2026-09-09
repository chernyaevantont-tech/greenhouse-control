# Review report — MDPI *Agronomy* submission

Manuscript: *Multi-step stability selects sparse surrogate models for economic greenhouse
climate control: an in silico study of feature-library design and actuator-pathway survival*

Reviewed 2026-09-07 against the requirements listed in `mdpi-requirements.md`.
Revised copy: `mdpi-review-output/manuscript-revised/`.

---

## Summary judgement

> **Updated after a fourth pass.** A plugin-driven review (four specialist agents plus the
> `academic-prose` and `humanizer` rule sets) found four further Critical items, all
> internal contradictions rather than formatting. **All four are now fixed** — C-3 and C-4
> against the regeneration data and the experiment driver, C-5 and C-6 by rewording and by
> giving the term-deletion probe its Methods. **All six figures were regenerated, three
> factual errors in them corrected, and five text/graphics overlaps removed.**
>
> Blocking items: **one action**. The pre-registration question is settled (C-2), and the
> only fact still missing is the Zenodo DOI — which fills the Data Availability Statement
> and the pre-registration pointer at once, via
> `python mdpi-review-output/apply-zenodo-doi.py <DOI>`. Add `EXPERIMENT_PROTOCOL.md` to
> the archive first: it is not in the built zip today.
>
> **The project's own numeric gate now passes on the revised manuscript** — 758 table cells
> and 336 prose values recomputed from `regen/results/`, 1,980 printed numbers walked,
> **0 unclaimed, 0 mismatches**. Reproduce with `python mdpi-review-output/verify-revised.py`.
> Full detail in **`plugin-review-findings.md`**.

This is a well-built manuscript. Its numeric apparatus is stronger than most published
work: **1,953 printed numbers, 758 recomputed table cells, 336 recomputed prose values,
zero mismatches and zero unaccounted numbers**, enforced by a gate that fails the build.
The reference list is exact — 48 cited, 48 defined, numbered in order of appearance, no
orphans. The prose carries almost none of the usual AI-writing tells.

**It is not yet submittable.** Two items are missing external facts (a data DOI, a
preregistration link). Four more are places where the manuscript contradicts itself: a
defined quantity whose reported values are impossible under that definition, a result the
Conclusions report and the Results say was never measured, a claim of replication under an
arm that was never run, and an entire experimental arm with no Methods.

**None of the six is a writing problem, and none can be fixed by an editor.** Every one
needs a fact or a decision only the authors have.

---

## CRITICAL — blocks submission

### C-1. Data Availability Statement names no publicly archived dataset

**Where:** back matter, `paper_en_revised.tex:3430`.

The statement is otherwise exemplary — it names the per-run result tree, the frozen
configuration hash `637c6b535a9e`, the regeneration commands, the acceptance gates, the
determinism self-test, the external dependencies, and it honestly limits the
reproducibility claim to one computing environment. But it points at
`own-article/regen/results/` **in the project repository**, with no public URL or DOI, and
the file still carries the author's own red marker:

> `[[REQUIRED BEFORE SUBMISSION: a public, citable location for this tree — a repository URL and an archived release with a DOI (Zenodo, figshare or equivalent)…]]`

MDPI: *"authors are required to provide details regarding where data supporting their
reported results can be found, **including links to publicly archived datasets**."*
Mandatory for Articles, with no exemption for computational work.

**The deposit is already prepared** — `ZENODO.md` gives the file
(`greenhouse-control-regen-data-v1.0.zip`, 5.97 MB, 625 entries), its SHA-256, and a
filled-in metadata form. What is missing is the act of depositing and pasting back the DOI.

**Action:** make the Zenodo deposit, then replace the placeholder with MDPI's recommended
wording: *"The original data presented in the study are openly available in Zenodo at
[DOI]."* **Nothing here can be written for you — inventing a DOI would be fabrication.**

### C-2. ~~"Pre-registered" is claimed five times with no preregistration link~~ — RESOLVED

**Settled; see `plugin-review-findings.md`, "The pre-registration question".** A real
pre-registration exists: `own-article/EXPERIMENT_PROTOCOL.md`, frozen 2026-06-26 to
2026-07-03, against an earliest reported result wave dated 2026-08-09 — five weeks of
margin. The substantive problem was not the missing link but that **four sites called the
*applied* criteria pre-registered**, contradicting Methods §2.5, which says in so many
words that "what was applied differs on both counts". Those four now say "applied", the
subsection title says "pre-specified", and the one honest mention in Methods stays and now
names the artefact.

Remaining: add `EXPERIMENT_PROTOCOL.md` to the archive (it is currently absent from it),
then run `python mdpi-review-output/apply-zenodo-doi.py <DOI>` to fill this placeholder and
C-1's together.

<details><summary>Original finding, kept for the record</summary>

**Where:** `02-methods.tex:235` (subsection title "Identification ladder and
**pre-registered** open-loop criteria"); `03-results.tex:83, 89, 93`;
`04-discussion.tex:235`.

MDPI, verbatim: *"Where authors have preregistered studies or analysis plans, **links to
the preregistration must be provided in the manuscript**."*

There is no such link anywhere in the manuscript. This is not a formatting slip: a
reviewer who reads "pre-registered gates" will expect a timestamped, third-party record,
and its absence invites a challenge to the study's central methodological claim — that the
open-loop selection criteria were fixed *before* the closed-loop results were seen.

**Two legitimate resolutions, and the author must pick:**
1. If the criteria were registered publicly (OSF, AsPredicted, a tagged repository commit
   with a timestamp), **add the link** at first use.
2. If they were fixed internally but never publicly registered, **change the word.**
   "Pre-specified" or "fixed in advance of the closed-loop comparison" says exactly what
   happened and claims no more than the evidence supports.

**Do not leave it as "pre-registered" without a link.**

</details>

### C-3 … C-6. Four internal contradictions found in the second pass

Full evidence, line references and suggested wording in **`plugin-review-findings.md`**.
Each was verified against the manuscript; two further agent claims were checked and
**rejected as wrong**, and are recorded there too.

| # | Finding | Why it blocks |
|---|---|---|
| ~~**C-3**~~ | ~~The violation axis is defined twice as "the seasonal count of steps in violation", but a season is 5760 control steps and the manuscript reports 9131, 9569, 6167 and ~9090.~~ | **RESOLVED AND FIXED** from the data: `violation_steps_total` equals the sum of the three per-variable counts in **100 % of 545 rows**. Both definitions now say "variable-steps, summed over the three corridor variables". Figure 2's axis label still needs regenerating. See `plugin-review-findings.md` D-1. |
| ~~**C-4**~~ | ~~The Conclusions report a **priced** ±15 % coefficient perturbation; Results §3.8 states the priced sensitivity was never measured.~~ | **RESOLVED AND FIXED**: the wave is **not** priced. `design_priced_real` merges 280/280 rows at identical EPI with the wave the code documents as original-objective, and the driver warns it "hard-coded `objective="full"` … SILENTLY ignored the driver's `--objective` flag". The Results sentence was correct; Table 16's label was wrong and has been corrected. No number changed. See D-2. |
| **C-5** | The Conclusions claim the non-monotone series holds "with the same shape under the other estimator", but under STLSQ the intermediate library is printed as **"(not run)"**, and the Methods say statements between the endpoints "rest on the ensemble arm alone". | A three-point shape cannot be reproduced from two points, on the paper's central non-monotonicity claim. |
| **C-6** | The 17-feature `physics_no_tuboil` library and its two controllers carry a headline contribution (the falsification of the retracted detour reading) but **appear first in the Results**: Methods §2.4 defines three libraries, Table 2 lists 15 controllers, and neither includes them. | An experimental arm with no Methods is not reproducible, which Agronomy requires explicitly. |

---

## MAJOR — decide before upload

### M-1. No GenAI disclosure, and the manuscript was produced with heavy tooling

MDPI requires disclosure **in Materials and Methods** of GenAI used "to generate text, data
or graphics or assist in study design or data collection, analysis or interpretation", and
explicitly exempts "superficial text editing (e.g., regarding grammar, spelling,
punctuation and formatting)".

The manuscript contains no such statement. **This review's own edits fall squarely in the
exempt category** — spelling consistency, numerals, punctuation — and do not require
declaring. But only the authors know the full history of how the text, figures and analysis
were produced.

**[AUTHOR CHECK: determine whether GenAI was used beyond superficial editing at any point.
If yes, add the disclosure to Materials and Methods and the Acknowledgments wording MDPI
specifies. If no, nothing is needed. This is an integrity item, not a formatting one.]**

### M-2. Three of nine authors have no ORCID

Present for Naumov (corresponding, `0000-0002-8582-3203`), Lyashov, Chernyaev, Zhdanova,
Chernyaeva, Merzlikina. **Missing for Mariya S. Kilina, Marina S. Kharina, Mariya N. Kulinich.**

MDPI's hard requirement — ORCID for the **corresponding** author — **is met**. Co-author
ORCIDs are strongly encouraged and are linked in the published article.

**[AUTHOR CHECK: collect the three missing iDs, or confirm those authors have none.]**

### M-3. Author contributions and author list need affirmative confirmation

The CRediT paragraph is complete and correctly worded, and the author block carries real
names, four numbered DGTU affiliations and institutional e-mails. But MDPI requires that
every listed author has approved the submitted version and agrees to be accountable.

Project records note the CRediT split was **proposed by job title** and "подлежит
подтверждению каждым автором" — pending confirmation by each author. That confirmation is
not something this review can supply.

**[AUTHOR CHECK: confirm with all nine authors: final author order, the CRediT role
assignment, the corresponding-author designation, the English transliteration of every
name and department, and consent to display e-mail addresses.]**

### M-4. Open-Meteo citation year disagrees with the registry

`openmeteo2023` cites DOI `10.5281/zenodo.7970649` as 2023; DataCite reports
publicationYear **2024**. The weather source is central to the study, so this should be
exact. See `reference-audit.md`. **[AUTHOR CHECK]**

---

## MINOR

| # | Finding | Status |
|---|---|---|
| m-1 | `optimizer`/`optimiser` spelled both ways in running prose (15 US vs 6 GB), sometimes on adjacent lines. MDPI §4.3 requires consistency. | **Fixed** — normalised to British, matching the rest of the manuscript |
| m-2 | 24 numerals ≥10 spelled out mid-sentence, against MDPI §6.1 | **Fixed** — converted to digits; sentence-initial ones correctly left as words |
| m-3 | 13 of 48 references carry no DOI or URL | Not fixed — MDPI encourages but does not require. **[AUTHOR CHECK]** |
| m-4 | Software versions are incompletely named. MDPI requires "the name and version of any software used". IPOPT is named without a version; `gl_gym 0.3.1` appears only in the Data Availability Statement. CasADi and the Python version are not stated in Methods. | **[AUTHOR CHECK: add a versions sentence to Materials and Methods]** |
| m-5 | One 105-word sentence in the Discussion | Not changed — splitting it risks the argument. **[AUTHOR CHECK]** |

---

## STYLE

| # | Finding | Status |
|---|---|---|
| s-1 | 6 paired ` -- X -- ` inserts — the strongest AI-writing tell present in the text | **Fixed** — recast with commas or parentheses |
| s-2 | 132 spaced en dashes total used as the universal clause connector | **Partly addressed (118 remain) — and this conflicts with MDPI house style.** MDPI §5.3 *prefers* em dashes to colons and asks only that they be used "sparingly". At ~1 per 260 words the remaining density is defensible. Driving it to zero is the author's call; see `anti-slop-audit.md`. |
| s-3 | Sentence rhythm and openers | **No action needed** — mean 29.8 words, range 4–105, driven by content. No mechanical uniformity, and none was introduced. |
| s-4 | Fourteen anti-slop categories from the brief (hype words, metadiscourse, vague attribution, "to the best of our knowledge", contractions, hedge stacking, rule-of-three padding, significance-instead-of-result…) | **Zero occurrences.** Nothing to fix. |

---

## What was verified as already correct

Worth recording, because it is the bulk of the manuscript:

- **Numbers:** 1,953 printed numbers walked, 758 table cells and 336 prose values
  recomputed from source data, **0 mismatches, 0 unclaimed** — before and after revision.
- **Abstract:** 190 words (MDPI limit ~200), single paragraph, follows the structured
  Background/Methods/Results/Conclusion shape without headings, defines MPC on first use,
  and its scope claim ("establish comparative simulation evidence rather than field
  performance") does not overstate the results.
- **Keywords:** 8 (MDPI requires 3–10).
- **Structure:** Introduction, Materials and Methods, Results, Discussion, Conclusions —
  five numbered sections, matching MDPI's Article layout. Agronomy's specific demand for a
  Methods subsection on experimental design and statistics is met by *"Simulation study
  design, site, weather and cropping season"* and *"Statistical treatment"*.
- **Back matter:** all eight statements present in MDPI's order, including the two ethics
  statements correctly answered "Not applicable" for a study with no human or animal
  subjects, and a funding statement with a real agreement number (075-15-2025-592).
- **References:** order of appearance matches the list exactly; 0 citations placed after
  punctuation; 25 of 32 DOIs verified clean at Crossref, 5 more resolved as checker
  artefacts.
- **Figures:** 5 numbered figures plus an unnumbered graphical abstract, all PNG at
  **600 dpi**, graphical abstract 4013 × 1514 px against MDPI's 1100 × 560 minimum.
- **Package:** the rebuilt `.docx` passes all 14 of the project's own validation checks
  (16 table captions, 5 numbered figures, 3 numbered equations, repeating header rows,
  back-matter order, field refresh) plus 9 pandoc-stage checks.
- **Honesty of the scientific claims:** the Conclusions do not exceed the Results. The
  Limitations section is specific rather than ritual — it names uneven replicate coverage,
  the observational status of the library-level mechanism, and a retracted earlier reading
  ("Ill-Conditioning, Not Sparsity") that the authors withdrew rather than quietly dropped.
  Negative and null results are retained ("the complementary knock-out is null").
