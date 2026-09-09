# REMAINING — open items in the English manuscript

Rewritten **2026-08-28**, after the Word build was made the submission route and
the figure and equation defects it exposed were fixed.  The previous rewrite was
2026-08-14, before the `notuboil` wave and before the retarget at *Agronomy*.

**Structural state at this assembly** (`verify_paper_en.py`):
51/51 environments balanced · 1479/1479 braces · 2452 inline-math delimiters
(even) · 0 dangling `\ref` · **5 numbered figures + the graphical abstract, and
16 tables, all cited** · 48 `\cite` keys against 48 `\bibitem` entries, none
unused, none missing, in first-citation order · abstract **188** words (MDPI
limit 200) · 16 288 words of narrative prose.

**Word state** (`format_mdpi_docx.py`, then `.codex-tmp/mdpi-format/audit_mdpi.py`):
13/13 formatting checks and the full package audit pass — 16 three-line tables
with repeating header rows, 3 equation components with right-aligned numbers,
6 figure captions, 48 references in MDPI style, back matter in MDPI order, A4
geometry, continuous line numbering and the template's own headers, footers and
logos byte-preserved.  The only text the audit still finds in brackets is the
eleven author-supplied fields listed in §2.1.

All six `\includegraphics` targets exist on disk and were regenerated from the
CSVs in this pass.

---

## 0. What changed in this pass, and why the register was rewritten

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
misspelt name being what gets indexed. `A.T.C.` is set as the corresponding
author; if it should be the head of the centre instead, move
`"corresponding": true` one entry and rebuild.

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

### 3.3 Cross-environment reproducibility was never measured

No wave records an environment: `repro.py` can emit a fingerprint, but the `env`
block is absent from **all 21** `regen_manifest.json` files, from every
run log, and `final/NUMBERS.md` prints `env_hash: n/a`. Waves are separated
only by `git_sha` (12 distinct values at one `config_hash`). The in-tree evidence
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
