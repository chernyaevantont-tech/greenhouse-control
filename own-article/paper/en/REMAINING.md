# REMAINING — open items in the English manuscript

Rewritten **2026-08-28** and extended **2026-09-14** (Section 0), after the Word build was made the submission route and
the figure and equation defects it exposed were fixed.  The previous rewrite was
2026-08-14, before the `notuboil` wave and before the retarget at *Agronomy*.

**Structural state at this assembly** (`verify_paper_en.py`):
51/51 environments balanced · 1478/1478 braces · 2520 inline-math delimiters
(even) · 0 dangling `\ref` · **5 numbered figures + the graphical abstract, and
16 tables, all cited** · 48 `\cite` keys against 48 `\bibitem` entries, none
unused, none missing, in first-citation order · abstract **191** words (MDPI
limit 200) · 16 465 words of narrative prose.

**Word state** (`make_docx.py` 16/16, `format_mdpi_docx.py` 14/14, then
`.codex-tmp/mdpi-format/audit_mdpi.py`):
every check and the full package audit pass — 16 three-line tables
with repeating header rows, 3 equation components with right-aligned numbers,
6 figure captions, 48 references in MDPI style, back matter in MDPI order, A4
geometry, continuous line numbering and the template's own headers, footers and
logos byte-preserved.  The only text the audit still finds in brackets is the
eleven author-supplied fields listed in §2.1.

All six `\includegraphics` targets exist on disk and were regenerated from the
CSVs in this pass.

---

## 0. 2026-09-23 — pre-deposit fixes

A pre-submission check found, beyond the data DOI, one scope defect in the abstract, figure
labels over data, and the review's minor items still open. All applied; nothing committed.
Gates: `verify_paper_en` balanced (50/50), 0 dangling, 48/48, abstract **198**, 17 255 words
of prose; `verify_tables` 800/0; `verify_prose` 410/0; `verify_manuscript` 2102 numbers,
0 unclaimed; figure self-checks 48/48 (Fig. 1), VERIFY OK (Fig. 4), 8/8 (graphical
abstract); `make_docx` and `format_mdpi_docx` all checks; `AUDIT_OK`, one placeholder (data
DOI); Word render 42 pages, pages 1, 15, 28, 36, 39 and 41 read. Tables 1–16 and Figures 1–5
are now first cited in ascending order in the Word text. `make_numbers_md.py` re-run
(date only). Archive rebuilt twice, deterministic: `f3cdd9cc…`, 630 entries; against
`89504527…` exactly four entries differ (`make_fig1/4/6.py`, `NUMBERS.md`).

| Item | What changed |
|---|---|
| Abstract scope | The abstract said "one-step accuracy and multi-step stability ranked the feature libraries oppositely" with no scope, while §3.1 and Finding 1 confine the reversal to the first-order, undenoised block under the two sparse estimators (pooled over all 72 labels the raw library also wins one step ahead). `MDPI_SUBMISSION.md` §3 listed that qualifier as not to be cut; it fell out when the abstract was restructured for MDPI. Now "Among first-order, undenoised configurations under sparse estimators, …" (+7 words, 191 → 198). |
| Cover letter | Same scope in paragraph 3; "the criterion the literature most often reports is the wrong one" → "can point to the wrong model"; "the criterion ranks candidate models in the opposite order to the one that decides the closed-loop outcome" → "among those configurations the one-step criterion ranks the closed-loop winner last, while multi-step stability selects it" (R-3: neither criterion reproduces the full closed-loop ordering). `make_cover_letter.js` was stale since the D-8 edits of 09-15 (made in the docx only); its four paragraph strings now match the docx. |
| Table order (M-20, wider than the review saw) | Table 7 was first cited in Methods §2.8 and Table 6 twice in §3.1, so first citations ran 1, 2, 3, 7, 4, 6, 5. The three forward pointers now name Section 3.3 instead. |
| Graphical abstract | Panel (b): the margin line crossed "+0.28" and "0.55"; the V-bottom value now sits below its bar and the first survival value above its marker. Panel (c): y label "mean closed-loop EPI", as in (b); the longer label ran into the panel letter. |
| Figure 1a | Legend moved to the empty upper-right corner; in the lower left its text ran over two `physics_no_cross` fits and into the raw cluster at 1.80. |
| Figure 4b | The opaque legend hid the lowest point of the heuristic curve; the bottom band is widened (0.34 → 0.62 of the data range) and the legend and note sit below the data. "-- wins" → ": wins"; the excluded-controller list is joined with semicolons; the note is three lines inside the axes; "31.5-50.2" → "31.5 to 50.2". |
| Figure 5a | Caption now explains the four short lines at the correction bar (where the contrast would end under a single season's tuning gain). |
| `wei2024` | TMLR has no volume, pages or DOI; OpenReview forum `tQVZgvXhZb` added as the locator (checked against the ML Anthology record), with an accessed-on date. |

Still open, and not for this pass: the data DOI; the authors' confirmations in §2.1 below;
the review's content items M-9, M-15, M-16, M-18, the notation pass and the Introduction
length (each changes a claim or the structure); the GenAI-disclosure decision (D-10).

---

## 0. 2026-09-16 (evening) — deposit archive text audit applied

Source: `mdpi-review-output/archive-text-audit-2026-09-16.md` §6, all six items. The manuscript
source, the Word file (`08509bdf…`) and every figure PNG are unchanged; `make_numbers_md.py`
re-run afterwards reproduces `results/final/NUMBERS.md` byte for byte (800 table cells,
410 prose values, 0 mismatches). Archive rebuilt, deterministic (`89504527…`, 630 entries,
5.99 MB); `ZENODO.md` carries the hash. Nothing committed.

| Item | What changed |
|---|---|
| 1 NUMBERS.md | `make_tables.py` no longer writes a file of that name: its 14-row summary of the default-objective tree is `tables/SUMMARY.md` (also under `results_pull/raw/`, `git mv`). `results/final/NUMBERS.md` is now written by `paper/en/make_numbers_md.py` from `verify_tables.CHECKS` and `verify_prose.CHECKS`: every table cell and prose value, the recomputed value, the source files (parsed from the tex `\source` lines and from the checkers' loader calls) and the mismatch count. The four contradictions (ppo leader, knock-in +3.05, 30/72, 12 %) are gone with the old file. |
| 2 pre-registered | `pre-specified` in the 11 code and doc sites; `analysis_notuboil.md` regenerated (heading "Verdict against the prediction stated in advance"). |
| 3 SPEC.md | Out of the archive (`make_archive.FIGURE_FILES`); `README.txt` gained "Figures, and the files they are drawn from". `CLUSTER_REGEN_PLAN.md` (shelved plan, private hosts) excluded via `SKIP_NAMES`. |
| 4 Docstrings | Revision history, `REVISION_LOG`/`REMAINING.md`/`*.tex:N` pointers, "reviewer item", "RETRACTION GUARD", dated notes and the assistant register (honest, genuinely, which is the point, worth recording, Do not restore/reintroduce) removed from `regen_config.py`, `run_regen.py`, `experiments_support.py`, `exp_draws.py`, `verify_regen.py`, `repro.py`, `analyze_notuboil.py`, `run_knockout_ablation.py`, `article_experiment_utils.py`, `e3_dagger_compare.py`, `_plotstyle.py`, `make_fig1..6.py`. Comments only; `config_hash` still `637c6b535a9e`; all six figure scripts re-run, self-checks pass, PNGs byte-identical to the embedded ones. |
| 5 Private infrastructure | Two lines dropped from `requirements-cluster.txt`; `.venv-regen/Scripts/python.exe` paths in three docstrings became `python …`. |
| 6 Archive | Rebuilt twice, same hash. Residual scan hits are literal uses (`superseded` for the two superseded trees, "shipped" for gl_gym data, "steps, not seasons") and the protocol's translated wording, which stays. |

---

## 0. 2026-09-16 — review items R-1…R-7 applied, environment wording reduced

Source: `mdpi-review-output/review-2026-09-15.md` §3. Gates after this pass:
`verify_paper_en` balanced (50/50), 0 dangling, 48/48, abstract 191, 17 257 words of prose;
`verify_tables` **800**/0 (Table 7 gained a seed-level block); `verify_prose` **410**/0
(passages `seedlevel`, `paneld` added, `config`/`bounds`/`conclusions` extended);
`verify_manuscript` 2102 numbers, 0 unclaimed; `make_docx` 16/16, `format_mdpi_docx` 14/14,
`AUDIT_OK`, one placeholder (data DOI); Word render 42 pages, equation (3) and Table 7
inspected. Archive rebuilt, deterministic (`86f5bed3…`, 630 entries). Nothing committed.

| Item | What changed |
|---|---|
| R-1 unit of analysis | §2.8 names the seed as the unit at which surrogates are independent and the seasons as repeated measures. Table 7 carries two new columns (wins/seeds, Holm over the same family of 15 on per-seed four-season means); `verify_tables.check_wilcoxon` verifies them. §3.3 reports the headline paired contrast (mean +1.23, median +1.58, 62/80, Holm 7.7·10⁻⁴) by season (20/20, 6/20 in 2021 with p = 2.3·10⁻³, 16/20, 20/20) and at seed level (16/20, Holm 8.4·10⁻³), and states that the count of controllers above the tuned heuristic is four at run level and two at seed level. Contribution (iii), Finding 2 and §4.6 say the same. |
| R-2 RL budget | §2.3: 2·10⁵ steps (≈35 seasons) against the 2·10⁶ with tuned hyper-parameters of the GreenLight-Gym reference (Table 2 of arXiv:2410.05336); §4.6: PPO/SAC positions are conditional on that budget. The reference budget is recorded in `verify_prose.check_config_constants` as an external constant. |
| R-3 | Contribution (i): "the closed-loop winner is the library that multi-step stability selects; neither criterion reproduces the full closed-loop ordering". |
| R-4 | §3.6 opens with "A perfect model does not by itself secure a high margin"; the planner's rank is framed as a bound on what fidelity can show; the two prose uses of "oracle" became "full-model planner" (the `oracle_mpc` label is unchanged). |
| R-5 | Conclusions: the stratification p is the seed-level 0.18 (3 against 17), the run-level 0.053 is gone; the headline test now has a Results home (§3.3). |
| R-6 | §2.1: two 60-day training trajectories per replicate, PRBS ±0.3 redrawn every 16 steps (4 h), Gaussian 0.1 redrawn every 5 steps, actions clipped, `GreenLightTomato-v0` defaults; §2.4: the three states and a constant enter every library (15/18/22/21 columns per equation, 45/54/66/63 coefficients); equation (3) carries the move-suppression term with R = diag(10, 5, 100, 50, 1, 1) and the hard bounds. All read from code by new `config`/`bounds` checks. |
| R-7 | §3.5 paragraph on Figure 1d: surviving |ξ| 0.06–0.08 (raw, median 0.069, 11/20), 0.06–0.07 (no-cross, median 0.061, 3/20), the full library split 5 in [0.05, 0.07] and 6 in [0.14, 0.19] (median 0.143); cut coefficients are stored as zero, so nothing is claimed about them. |
| Environment wording | §2.9, §3 preamble, §4.6 and the DAS no longer name the `image` field, the container image, the base image or the OS: "a Linux compute cluster under Python 3.11" and "a workstation under Python 3.14", "every result row records which". The deposit README keeps the `image` values because the CSV column exists; "Windows" was dropped there too. |
| Build | `make_docx.py` strips `\cmidrule` lines before pandoc (they leaked as "2-5(lr)6-7" into the first header cell of Table 7); the hard-coded "2-3(lr)4-5 Library" patch in `format_mdpi_docx.py` became an assertion. |

---

## 0. 2026-09-15 (afternoon) — readiness re-check applied

Source: `mdpi-review-output/review-2026-09-15.md`. Every gate re-run afterwards:
`verify_paper_en` balanced, 0 dangling, 48/48, abstract 191; `verify_tables` 758/0;
`verify_prose` **340**/0 (four checks added); `verify_manuscript` 1975 numbers, 0 unclaimed;
Word build 14/14, `AUDIT_OK`, one placeholder (the data DOI). Archive rebuilt, deterministic
(`b314d528…`, 630 entries).

| Item | What changed |
|---|---|
| D-1 glyph | pandoc drops `{\DJ}`; the submission file printed **Ećim-urić** three times. `Đ` is now a literal in `01-introduction.tex`, `04-discussion.tex` and the `ecimduric2024` bibitem. Rule: non-ASCII letters as literals, never as letter macros — `audit_mdpi.py` and `verify_*` cannot see this class of defect. |
| D-2 counts | §2.9: 20 manifests / 11 SHAs → **21 / 12** (the `notuboil` wave). `verify_prose.check_structural_counts` now counts manifests, distinct `git_sha` and the absence of an env block from the tree, because the coverage walk claims by value and 20/11 collided with 20 seeds / 11 features. |
| D-11 environments | The `image` column of every result row (from `REGEN_IMAGE`, default `local`) shows **two** environments, not one: `final/main.csv`, `mechanism*`, `faults`, `design*`, `parity`, `ladder*` carry `greenhouse-regen:v1` (cluster container, `python:3.11-slim`; `draws.csv` is `v4`), everything else including `final/adapt.csv` and `final/guard.csv` is `local` (workstation, Python 3.14). So the "two harnesses" of the heuristic drift (−1.2061 vs −1.2264) are the two platforms, and the seed-matched priced−default deltas of §3.3 cross them for the five `physics_no_cross` controllers and `nn_mpc` (the raw pair is within-environment). §2.9, §3 preamble, §4.6 and Conclusions Finding 5 now say this; the "single environment" wording is gone. The DAS, `regen/README.md`, `ARCHIVE_README.txt` and `ZENODO.md` agree. **Authors to confirm** that `local` is the Windows workstation for every local wave. |
| D-5 versions | §2.9 opens with the full pinned stack (NumPy … gl_gym 0.3.1); `cluster/requirements-cluster.txt` is now shipped at the archive root and named in `README.txt`. |
| D-6 CoI | `authors.json → conflicts_of_interest` carries MDPI's funder-role sentence. |
| D-7 DAS | Cut from ~400 words of run commands to five sentences; the DOI sentence still arrives through `@@DATA_LOCATION@@`. Table 16's caption no longer names `own-article/regen/results/`. |
| D-8 letter | `cover_letter.docx`: Special Issue → *Intelligent Control of Greenhouse Climate* (Guest Editor Dan Xu, deadline 31 Dec 2026); "registered a prediction" → "stated the prediction in advance"; "confirms the mechanism" → "establishes that the closed-loop outcome depends on survival of that term". Degrees in the signature block are still the authors' to confirm. |
| D-9 | `paper_en_mdpi_simulation_short_captions.docx` removed (`git rm`, not committed). |

Not applied, by design: the scientific items R-1…R-7 of the review (unit of analysis, RL
budget, contribution (i) wording, §3.6 opening, headline test in Results, Methods detail,
Figure 1d) and the GenAI-disclosure decision. Nothing is committed.

---

## 0. 2026-09-15 — table typography in the Word build

Table 16 (the headline-quantities table) was unreadable in `paper_en_mdpi.docx`: every cell
centred, the panel headings split over two or three rows exactly where the LaTeX source had
broken them by hand, three equal columns, file paths carrying a stray space
(`ladder_rerun/ ladder_rerun*.csv`) and hyphenated by Word (`phys-lib.csv`), and the notes set
as body text. The same centring and autofit defects were visible in the three other prose
tables (1, 2 and 15). Fixed at the source of each:

| Where | What changed |
|---|---|
| `05-conclusions-abstract.tex` | The five panel rows of `tab:headline` are one wrapping row each (`\multicolumn{3}{@{}p{\panelwidth}@{}}`, `\panelwidth` = the three column widths plus the two gaps) instead of hand-broken `@{}l` lines; the four break-hint spaces inside paths became `\allowbreak`; column widths 0.34/0.28/0.32 (were 0.36/0.24/0.34) so the p-values do not wrap inside the maths. No number or word changed. |
| `make_docx.py` | Any `\multicolumn` spec pandoc cannot read (`@{}`, a p-column) is mapped to `l`; a tabular with a p-column gets a width for every column (p-widths kept, l/c/r columns at their LaTeX natural width, normalised to the full width) so pandoc emits fixed columns — Tables 1, 2, 15, 16; the five note blocks under tables become a `tablenotes` Div that a Lua filter maps onto `MDPI_4.3_table_footer`; `\allowbreak` becomes a zero-width space. Two post-checks added (16/16). |
| `format_mdpi_docx.py` | Alignment follows the cells: a table with a prose column (a body cell over 40 characters) sets its first column and every prose column flush left and its cells to the top; numeric tables stay centred. Panel rows are flush left in every table, spaced 3 pt off the block above and kept with the row they label. Automatic hyphenation is off inside table cells; prose-table rows get 2 pt after. |

Rendered through Word (COM → PDF) and read page by page: Table 16 now sits on one page with
its caption and notes, the paths break after the directory without a hyphen, the numeric
tables are unchanged apart from the flush-left panel labels, and the page count is still 40.
Gates: `verify_paper_en` balanced; `verify_tables` 758/0; `verify_prose` 336/0;
`verify_manuscript` 1974 numbers walked, 0 unclaimed; `AUDIT_OK` with the single data-DOI
placeholder. Not done, and worth a look: `\texttt` has no character style in the Word build
(the template defines no `Verbatim Char`), so every path and identifier prints in Palatino —
defining one (Courier New at the body size) would make the *Source file* column and the
controller labels read as code, as the LaTeX intends.

---

## 0. 2026-09-14 — the 07.09 review is now in the canonical source

The MDPI review of 2026-09-07/08 (`mdpi-review-output/`) edited **copies** of the five
section files; the canonical files were then edited separately on 2026-09-09 (pre-specified
wording, italics removal, reference re-check), so the two trees diverged and the submission
file still carried the review's two Critical findings. This pass three-way-merged the
review copies onto the canonical files (base: the tree at `998014a`), resolved 12
conflicts by hand, and rebuilt everything.

**Ported, and now in `paper_en_mdpi.docx`:**

| Item | What changed |
|---|---|
| **C-3** | Violation axis defined as *variable-steps summed over the three corridor variables* (Methods §2.2, Results §3 preamble, Figure 2 caption and regenerated axis label). |
| **C-4** | Table 16 row relabelled *default objective* (the `design_priced_real` wave was scored on the hard-coded weights); provenance comment corrected. |
| **C-5** | Conclusions: "same shape under the other estimator" → the raw-over-physics *direction* reproduces; the intermediate library was not run under STLSQ. |
| **C-6** | `physics_no_tuboil` (17 features) defined in §2.4; its two controllers added to Table 2 below a rule, outside the 15-controller comparison and the Holm family. |
| M-21 / M-22 / M-23 / M-25 / M-26 | Span sentence recast (max − min, peaking at +5.40); Figure 2 caption quotes 5.3 steps; `nn_mpc` removed from the Figure 3 survival strip; Figure 2 caption gained the marker→controller key; the non-priced objective is *default* everywhere (the review had left ten *original* sites in Results). |
| A-7 … A-23 | Five (not four) one-factor labels; three (not two) things follow for practice; "declared" not "pre-declared" family; RMSE/PPO/SAC expanded at first use; A-17 stale "untested experiment" sentence; unit spacing `EUR\,m$^{-2}$`; tense and antecedent fixes. |
| Language / MDPI | optimizer → optimiser (15), numerals ≥10 as digits mid-sentence (24), overlong sentence split, bold-for-emphasis removed. |
| Anti-slop | Paired ` -- X -- ` inserts in prose 29 → **0** (three the review's scan had missed included); dashes before conjunctions removed; single ` -- ` connectors in prose 116 → 32, tables and comments excluded. Eight sentences where the review's dash→comma rule had left a *dangling* opening dash were recast with parentheses or a colon. |
| Bold lead-ins (owner, same day) | The run-in bold sentences that opened the five Conclusions findings, the four Introduction contributions, the term-deletion paragraph in §4.1 and the fifteen Limitations items, plus one mid-sentence bold in §2.8, were removed as an AI tell; the Conclusions enumerate became five prose paragraphs, the contributions keep their (i)–(iv) signposts, the Limitations list keeps its items. Bold now occurs only in table headers, best-value cells and panel labels. Wording and every number unchanged. |
| Figures | `make_fig1/2/3/4/6.py`, `_plotstyle.py`: axis labels (variable-steps, *indicator*), `nn_mpc` tick removed, coefficient spelling unified, label halos/legend frames against overlaps. All six regenerated: 48/48, 61/61, VERIFY OK, waterfalls close, graphical-abstract self-check OK. |

**Decided differently from the review copy — check if you disagree:**

- Results §3.1 (×3) and Discussion §4.2 say **"applied (open-loop) gates/axes"**, the
  review's wording, not the 09.09 "pre-specified". Reason: Methods §2.5 states that what
  was applied (the 0.05 threshold, the active-term axis) differs from what the protocol
  pre-specified, so calling the applied axes pre-specified contradicted §2.5. The Methods
  §2.5 title keeps *pre-specified*. `verify_prose.py` anchors moved with the wording.
- §2.5 carries **one** protocol pointer, naming `EXPERIMENT_PROTOCOL.md` in the archived
  package "named in the Data Availability Statement". The review's second red
  `[[ARCHIVE DOI REQUIRED]]` placeholder was **not** adopted: the canonical build fills the
  DOI once, from `authors.json → data_location`, and `apply-zenodo-doi.py` targets the
  review copy, not this tree. The review's "committed before any wave was generated"
  clause was also left out — true of the Russian original (2026-06-26), but the deposited
  file is the 09.09 English translation and does not itself record that date.
- The review's °C normalisation residues were reverted to the canonical spellings
  (`verify_prose.py` anchors on them), and the Figure 2 caption key uses quotes, not
  `\emph`, in line with the 09.09 italics decision.

**Gates after the merge:** `verify_paper_en` balanced, 0 dangling refs, 48/48 references,
abstract **191** words; `verify_tables` 758 cells / 0 mismatches; `verify_prose` 336 values
/ 0 mismatches; `verify_manuscript` 1980 printed numbers walked, 0 unclaimed; Word build
14/14 and `AUDIT_OK` with the single expected placeholder (the data DOI). The deposit
archive was rebuilt because it ships the figure generators (629 entries, SHA-256
`a65db4be…`, recorded in `ZENODO.md`).

**AI-marker pass (2026-09-14, evening; `mdpi-review-output/ai-marker-audit-2026-09-14.md`).** The
current-model register (aphoristic closers, `What X does` clefts, `X, not Y` tails, staged candour,
`buys`/`genuinely`, duplicated caveats) was removed in 124 wording-only edits across the five section
files; the tuning outcome now lives in Results 3.2 only (Methods 2.6 points there), the one-sample-test
caveat in Methods 2.8 and the table notes, §4.3 is titled *Sparsity and the library effect*, and
Acknowledgments stays `Not applicable` by the authors' decision. Nine `verify_prose.py` anchors were
re-pointed. Later the same evening the 15-item Limitations list (§4.6) was recast as seven prose
paragraphs (every sentence, number and `%%` provenance note kept; the `format_mdpi_docx.py`
validation anchor now matches the lower-case `there is no physical-greenhouse validation`), and
person usage was checked: Methods and Results are impersonal throughout, `we`/`our` appears 17 times
(Introduction 2, Discussion 12, Conclusions 1, abstract 1) only for the authors' choices, claims and
interpretations, the paper is `this study`/`the present study`, and there is no `I`/`the author`;
MDPI permits either voice and asks only for consistency, so the scheme was left as it is. Gates after the pass: `verify_paper_en` balanced, 0 dangling refs, 48/48 references, abstract
191 words; `verify_tables` 758/0; `verify_prose` 336/0; `verify_manuscript` 1974 numbers walked, 0
unclaimed; Word build 14/14 and `AUDIT_OK` with the single data-DOI placeholder.

**Still open from the review, author's call** (unchanged, see
`mdpi-review-output/plugin-review-findings.md`): M-5 … M-19 and the hedging of causal
verbs — every one of them changes a claim's strength or adds content, which this pass did
not do.

---

## 0 (2026-08-28). What changed in that pass, and why the register was rewritten

The 2026-08-14 register was written before three things happened: the `notuboil`
wave settled the one experiment it listed as un-run, the manuscript was
retargeted at *Agronomy* (new title, in-silico framing, four added references),
and the submission route became a Word file built against the official template
rather than a LaTeX class conversion.  Proof-reading that Word file page by page
turned up defects the LaTeX checks cannot see, all of which are now fixed:

- the body pointed at a **"Figure 6"** that no caption defined — the graphical
  abstract is unnumbered in the Word build, so the reference had nowhere to land;
- display equations carried **hand-written numbers inside the maths**, centred
  next to the equation instead of set at the right margin, and the third
  equation had no number at all;
- annotations **sat on the data** in Figures 1c, 2, 4a, 4b, 5a, 5b and in two
  panels of the graphical abstract;
- Figure 2 was drawn at single-column width and printed at 0.85 of the text
  width, so its fifteen labels overlapped;
- four of the sixteen tables did **not repeat their header row** across page
  breaks, and Word was not asked to refresh the page-number fields;
- the ORCID placeholders existed in the LaTeX front matter but not in the Word
  one, so the authors would not have been prompted for them;
- `make_docx.py` pointed at a pandoc that is not in the repository, and three
  near-identical styled `.docx` files sat side by side with nothing saying which
  one to submit.

Every item below is genuinely open — nothing listed here is already done.

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
| **Bibliography** | 48 entries verified against publisher records; 26 DOIs added; four keys renamed to match the version of record. The four *Agronomy* entries added at the retarget (`xu2023agronomy`, `wen2022agronomy`, `ecimduric2024`, `padillanates2025`) are cited in the Introduction and the Discussion. |
| **The bilinear-detour reading** | Tested and **falsified** — see §3.1. It is reported as falsified in §1 (iv), §3.5, §4.1 and §5, and the four-library table and Figures 1c/6b carry the probe. |
| **Graphical abstract numbering** | Closed 2026-08-28. `figures/SPEC.md` always said five numbered figures plus an unnumbered graphical abstract; the LaTeX still numbered it and the Conclusions `\ref`-ed it, so the Word build printed "(Figure 6)" against a caption reading "Graphical Abstract." The float now carries `\captionsetup{labelformat=empty}` and no `\label`, and the Conclusions names it. `grep "Figure 6"` over the exported PDF returns nothing. |
| **Equation numbering** | Closed 2026-08-28. The numbers are no longer written into the maths: LaTeX numbers the three display equations itself, and `format_mdpi_docx.py` clones the template's own two-cell equation component so the number sits at the right margin. Equation (3) is numbered for the first time. |
| **Figure annotations over data** | Closed 2026-08-28 in `_plotstyle.annotate_n` (every corner note now carries a background) and in the placement tables of `make_fig1.py`, `make_fig2.py`, `make_fig4.py`, `make_fig5.py` and `make_fig6.py`. Each figure's own self-check still passes: 48/48, 63/63, waterfall closing to 0.00, 8/8 caption claims. |
| **Log-axis tick labels** | `_plotstyle.finish` now silences minor log-tick labels. The same scripts produced `8 16 32 64` on one matplotlib and an overlapping `16 2×10¹ 3×10¹` on another; the figures are now identical across environments rather than across versions. |
| **`fig3_values.json` was not JSON** | A missing library value used to arrive falsy and now arrives as a float `NaN`, which is truthy, so `r.library or "none"` wrote a bare `NaN` into the values file. Fixed at the source in `make_fig3.py`; the file parses again and matches the committed one. |

---

## 2. OPEN — must be resolved before submission

### 2.1 Author identity and back matter *(only the authors can supply these)*

**`authors.json` now exists and carries the nine authors**, all at Don State
Technical University, across four units: the World-Class Research Centre
"Agroengineering of the Future" (six), Hydraulics/Hydropneumatic Automation and
Thermal Processes (one), Cybersecurity of Information Systems (one) and the
Research Administration Office (one). Names are transliterated and the English
unit names are translations — **both have to be confirmed by the authors**, a
misspelt name being what gets indexed. `I.I.N.`, the head of the centre, is the
corresponding author (moved from `A.T.C.` on 2026-09-02 at the authors' request).

`author_contributions` is a **proposal derived from the stated positions**, not
a statement anyone has made yet: every author must confirm the CRediT roles
attributed to them. Institutional e-mails and six ORCID iDs were supplied on
2026-08-31 and are in place; the title block carries no placeholder at all now.
What is still empty — and still prints as a `[[...]]` marker that
`audit_mdpi.py` lists and `assemble_paper_en.py` names on every build — is the
funding sentence, the acknowledgments and the data DOI.

Nothing has been invented anywhere. **One file drives both builds:** copy
`authors.example.json` to `authors.json` and complete it, then re-run the four
build commands in §5. `authorship.py` feeds both the LaTeX assembler and the
Word styling pass from that single file, so the two front matters cannot
disagree, and it refuses a half-filled file rather than mixing a real author
with a placeholder one. Any number of authors works — MDPI does not require a
particular number, and the Word front matter is built from the list, not from a
fixed two-author layout. With the file complete and a DOI in `data_location`,
`audit_mdpi.py` reports `explicit_placeholders=0`; this was tested end to end
with dummy values, which were then removed.

The markers below are what the manuscript carries until then:

| Location | Marker | `authors.json` key | State |
|---|---|---|---|
| Title block | author names, affiliations | `authors[].name`, `affiliations[]` | **supplied**, spelling to be confirmed |
| Title block | ORCID iD | `authors[].orcid` | **six supplied**, including the corresponding author's — the only one MDPI requires. None for M.S.K., M.S.Kh. and M.N.K.; nothing is printed for them, and MDPI will display an iD for anyone who adds one |
| Title block, affiliations | e-mail, labelled by initials | `authors[].email` | **all nine supplied** |
| Author Contributions | CRediT roles per author | `author_contributions` | **drafted from positions**, to be confirmed by each author |
| Funding | `[[REQUIRED — NOT SUPPLIED.]]` — every funder with grant numbers, or the MDPI "received no external funding" wording | `funding` | open — a World-Class Research Centre normally has an agreement number to cite |
| Acknowledgments | `[[ACKNOWLEDGMENTS REQUIRED …]]` | `acknowledgments` | open (or "Not applicable.") |
| Conflicts of Interest | "The authors declare no conflicts of interest." | `conflicts_of_interest` | **supplied**, to be confirmed by every author |
| Data Availability | `[[REQUIRED BEFORE SUBMISSION …]]` — see §2.2 | `data_location` | open — the one hard blocker |

IRB, Informed Consent and Supplementary Materials are already correctly
"Not applicable." (simulator study, no human or animal subjects, no
supplementary file). Do not change those to placeholders. All eight back-matter
statements are now written by the LaTeX assembler in MDPI order; the Word pass
only styles them.

### 2.2 Data availability DOI — **hard blocker**

The Data Availability Statement is otherwise complete: it names `config_hash
637c6b535a9e`, the per-wave `regen_manifest.json`, the eight-block regeneration
sequence, `--merge` + `make_tables.py` → `NUMBERS.md`, the `verify_regen.py`
gates, the `repro.py --selftest` digests, `gl_gym` 0.3.1 and the Open-Meteo/ERA5
weather. It lacks **a public, citable archive location**. Deposit the results
tree (Zenodo or equivalent) and insert the DOI. This is the one item that
genuinely prevents submission.

### 2.3 Which file to submit, and one file that is still locked

`own-article/paper/en/paper_en_mdpi.docx` is the submission file: the Word build
against the official Agronomy template, and the only styled output the pipeline
now writes.  `paper_en.docx` is the unstyled pandoc intermediate — do not submit
it.

`paper_en_mdpi_simulation_short_captions.docx`, one of the two superseded
variants, is **open in Word** and could not be deleted (`paper_en_mdpi_simulation.docx`
was). Close it and delete it, so that only one styled file remains.

### 2.4 LaTeX route, if it is ever needed

The Word file is the submission. The LaTeX source stays authoritative for the
*content* — the five section files are edited, `paper_en.tex` is generated — and
`MDPI_SUBMISSION.md` still carries the `article` → `Definitions/mdpi` mapping
should a `.tex` submission be wanted. No TeX distribution exists on this machine,
so the LaTeX has never been compiled; the Word build is what has been proof-read.
The abstract sits at **188 of 200 words**, so there is real headroom now, but the
scope qualifiers listed in `MDPI_SUBMISSION.md` §3 still may not be cut.

---

## 3. OPEN — scientific, and honestly disclosed rather than blocking

These are stated as limitations in the manuscript. They are listed here so they
are not mistaken for oversights.

### 3.1 The named experiment was run, and it falsified the reading

Deleting the single bilinear `t_uBoil` feature from the 18-feature `physics` set
gives a 17-feature library; it was run at the same optimiser and threshold,
4 seasons × 20 seeds, closed loop (`regen/results/notuboil/`, 160 rows, zero
solver aborts). The registered prediction of the bilinear-detour reading was a
collapse onto `physics_no_cross` — survival ≈ 0.15, EPI ≈ +0.3. **Measured:**
κ 52.3 against 53.4, rollout median 24.17 against 24.27, EPI +2.11 against +2.75,
survival 0.40 against 0.55 (exact McNemar p = 0.549). The library does not
collapse; the reading is falsified and is reported as falsified.

What replaced it is an open question, not a claim: EPI still tracks boiler-term
survival monotonically across the four libraries (0.15 → +0.28; 0.40 → +2.11;
0.55 → +2.75 / +4.32), but *which* structural feature kills the direct term in
`physics_no_cross` is unresolved. The small but significant penalty for removing
the bilinear term (−0.64 mean, ensemble arm only) says it shares threshold
pressure with the direct term rather than substituting for it.

The `cross` knock-out block still **cannot** stand in for this test: it edits
coefficients on a λ = 10⁻⁶ fit whose baseline boiler survival is 1.00 in all 20
replicates, so sparsification never severs the pathway there. This is stated in §3.5 and §4.1.

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

### 3.3 Cross-environment reproducibility of any single wave was never measured

No manifest records an environment: `repro.py` can emit a fingerprint, but the `env`
block is absent from **all 21** `regen_manifest.json` files, from every
run log, and `final/NUMBERS.md` prints `env_hash: n/a`. Manifests are separated
only by `git_sha` (12 distinct values at one `config_hash`). The **row-level `image`
column** does record the environment class, and it shows two (see §0, D-11): the
canonical `final/` blocks ran in the cluster container, everything else on the
workstation. The in-tree cross-platform evidence is the deterministic heuristic
drifting between those two at identical `config_hash`: `-1.2061` (`final/main.csv`,
container) against `-1.2264` (`n2_tune/tune_rb_n2.csv`, workstation), per-season
|Δ| 0.0031 / 0.0134 / 0.0266 / 0.0381; and §3.8's 80 default-objective design cells,
75 of them within 0.2 EUR m⁻² across the two.

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
PYTHONIOENCODING=utf-8 python figures/make_fig1.py   # 48/48 checks
PYTHONIOENCODING=utf-8 python figures/make_fig2.py
PYTHONIOENCODING=utf-8 python figures/make_fig3.py   # 63/63 checks
PYTHONIOENCODING=utf-8 python figures/make_fig4.py   # VERIFY OK
PYTHONIOENCODING=utf-8 python figures/make_fig5.py   # waterfall closes to 0.00
PYTHONIOENCODING=utf-8 python figures/make_fig6.py   # 8/8 caption self-check
PYTHONIOENCODING=utf-8 python assemble_paper_en.py
PYTHONIOENCODING=utf-8 python verify_paper_en.py
```

Then the Word build, which is what is submitted:

```bash
PYTHONIOENCODING=utf-8 python make_docx.py           # pandoc -> paper_en.docx
PYTHONIOENCODING=utf-8 python format_mdpi_docx.py    # -> paper_en_mdpi.docx, 13/13
cd ../../.. && PYTHONIOENCODING=utf-8 python .codex-tmp/mdpi-format/audit_mdpi.py
```

`audit_mdpi.py` is the package-level gate: styles, relationships, caption
sequence, equation components, table rules and repeating headers, back-matter
order, A4 geometry, line numbering, field refresh, and a canonical-XML
comparison of the template's headers, footers, theme and fonts. It ends in
`AUDIT_OK` and prints every remaining `[[...]]` placeholder.

Requirements beyond the article environment: `python-docx`, `lxml`, `pandas`,
`scipy`, `matplotlib`, and pandoc 3.10 on `PATH` (or the pinned build under
`.tools/`). Page proofs were taken by exporting the `.docx` from Word 16 and
rasterising with PyMuPDF.

Edit the **section files** and the assembler. `paper_en.tex` is generated and is
overwritten on every assembly.
