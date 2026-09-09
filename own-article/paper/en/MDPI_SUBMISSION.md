# What changes at submission to MDPI *Agronomy*

Written 2026-08-14, **revised 2026-08-28** when the submission route changed.

**The manuscript is submitted as Word.** `own-article/paper/en/paper_en_mdpi.docx`
is built from the LaTeX source through pandoc against the official Agronomy
template and then styled paragraph by paragraph into the template's own MDPI
styles. It has been exported from Word 16 and proof-read page by page. The LaTeX
remains the content source of truth — the five section files are edited and
`paper_en.tex` is generated from them — but it is not what is uploaded, and it
has never been compiled: no TeX distribution exists on this machine. Sections 6
and the class mapping below are kept only in case a `.tex` submission is ever
wanted.

Nothing here is a formatting nicety. Items marked **BLOCKER** stop the submission.

---

## 0. Regenerate first, always

`paper_en.tex` is assembled by concatenation and is overwritten on every run. Edit the
five section files and `assemble_paper_en.py`, never `paper_en.tex`.

```
python own-article/paper/en/assemble_paper_en.py   # rebuild paper_en.tex
python own-article/paper/en/verify_paper_en.py     # structural + terminology check
python own-article/paper/en/make_docx.py           # pandoc -> paper_en.docx
python own-article/paper/en/format_mdpi_docx.py    # -> paper_en_mdpi.docx (13 checks)
python .codex-tmp/mdpi-format/audit_mdpi.py        # package-level gate, ends AUDIT_OK
```

`verify_paper_en.py` reports environment balance, dangling `\ref`s, float and citation
coverage, the abstract word count, and the terminology guard. It is **not** a LaTeX
compiler. `audit_mdpi.py` is the one that speaks for the file actually being
submitted: caption sequence, equation components, three-line tables with
repeating headers, back-matter order, A4 geometry, line numbering, field refresh,
and a canonical-XML comparison against the template's headers, footers, theme and
fonts. It also prints every `[[...]]` placeholder still in the file — eleven
today, all of them §1 and §2 items.

---

## 1. Author block — **BLOCKER**

`assemble_paper_en.py` carries a placeholder author block whose contents are
`[[...REQUIRED]]` strings in red. **No name, initial, affiliation, e-mail or ORCID has
been invented anywhere in this manuscript.** That is deliberate and must stay that way
until a human supplies the real values.

**How to supply them:** copy `authors.example.json` to `authors.json`, fill it in, and
re-run the five commands in §0. `authorship.py` reads that one file and drives both the
LaTeX author block and the Word front matter, so they cannot drift apart; a half-filled
file is refused with a list of what is missing. MDPI does not require any particular
number of authors — one is a valid paper — and the front matter is generated from the
list, so adding a third author means adding a third entry, not editing two builders.
Under `mdpi.cls` the class option is `oneauthor` for a single author and `moreauthors`
otherwise.

The eight items the file asks for:

| # | Item | `authors.json` | Where it goes |
|---|------|----------------|---------------|
| 1 | Full author names, in final author order | `authors[].name` | `\author{}` |
| 2 | ORCID iD per author (mandatory for the corresponding author) | `authors[].orcid` | `\author{}` |
| 3 | Full postal affiliation per institution, numbered | `affiliations[]` | `\author{}` footnotes |
| 4 | Corresponding author + institutional e-mail | `authors[].corresponding`, `.email` | `\thanks{}` → MDPI `\corres` |
| 5 | E-mail of every co-author | `authors[].email` | MDPI prints these in the affiliation block |
| 6 | CRediT roles by initials | `author_contributions` (`authors[].initials`) | Author Contributions, back matter |
| 7 | Funding statement with grant numbers, or "no external funding" | `funding` | Funding, back matter |
| 8 | Conflict-of-interest declaration from every author | `conflicts_of_interest` | Conflicts of Interest, back matter |

Two more the same file carries: `acknowledgments` (or "Not applicable.") and
`data_location`, the §2 blocker.

Under `mdpi.cls` these become `\Author{}`, `\AuthorNames{}`, `\address{}`, `\corres{}`,
`\firstnote{}`. The mapping is one-to-one; only the macro names change.

---

## 2. Back matter

The assembler emits an MDPI back-matter block between the Conclusions and the
bibliography, in MDPI's required order. Under `mdpi.cls` each becomes its own macro:

All eight statements are emitted by the assembler, in MDPI's order, and the Word pass
only styles them.

| Statement in `paper_en.tex` | `mdpi.cls` macro | State today |
|---|---|---|
| Supplementary Materials | `\supplementary{}` | real: *Not applicable* |
| Author Contributions | `\authorcontributions{}` | **placeholder — BLOCKER** |
| Funding | `\funding{}` | **placeholder — BLOCKER** |
| Institutional Review Board Statement | `\institutionalreview{}` | real: *Not applicable* |
| Informed Consent Statement | `\informedconsent{}` | real: *Not applicable* |
| Data Availability Statement | `\dataavailability{}` | real, except the public URL/DOI — **BLOCKER** |
| Acknowledgments | `\acknowledgments{}` | **placeholder** |
| Conflicts of Interest | `\conflictsofinterest{}` | **placeholder — BLOCKER** |

"Not applicable" is the correct answer for the two ethics statements: this is a
computational study of a greenhouse climate simulator with no human or animal subjects.
Do not delete them — MDPI requires the statement to be present even when it is negative.

### Data Availability — what is already true, and the one thing that is not

The statement in the back matter is real and specific. It names:

- the replication tree `own-article/regen/results/`, one row per
  (controller, seed, test season);
- the single frozen configuration hash **`637c6b535a9e`**, written into every result row
  and into each wave's `regen_manifest.json` together with the git commit;
- the regeneration commands — `run_regen.py --experiment <block>` for each of the eight
  blocks, then `run_regen.py --merge` and `make_tables.py`, which rebuild the derived
  tables and `NUMBERS.md` (the claim → value → source-file map);
- the acceptance gates in `verify_regen.py`, which exit non-zero on a bad wave;
- the determinism self-test `repro.py --selftest` (seven SHA-256 digests, nine with the
  reinforcement-learning policies);
- the external dependencies: the GreenLight model as packaged in `gl_gym` 0.3.1, and the
  ERA5-derived weather from the Open-Meteo historical archive API;
- the honest limit: bit-level reproduction is established **within one computing
  environment only**; the cross-environment case was never measured.

**What is missing and blocks submission:** a public, citable location. MDPI requires a
link or an explicit statement of restriction, and a path inside a private repository is
neither. Archive the tree (Zenodo, figshare or equivalent), get a DOI, and replace the
red `[[REQUIRED BEFORE SUBMISSION: ...]]` marker with it. If the tree cannot be made
public, the statement must say so and say why — silence is not an option.

---

## 3. Abstract length — within limit, keep it there

MDPI's limit is **200 words**. The abstract measures **188** at the last structural
check (198 before the *Agronomy* retarget, 248 before the mechanism rewrite). Twelve
words of headroom is a real margin, but re-run `verify_paper_en.py` after every edit
to the abstract.

Do **not** cut, in any trim: *"in the first-order, undenoised block under sparse
estimators"*, *"against three comparators"*, *"deterministic reference"*, or the Pareto
sentence. Each is a scope limit that was added to fix an overstatement, and removing one
re-creates a defect the verification passes were run to remove. `REMAINING.md` §4.15
lists the cheapest 48 words to lose instead.

---

## 4. Bibliography

The manuscript uses a manual `thebibliography` block, emitted by the assembler in
first-citation order. 44 entries were verified on 2026-08-14 against Crossref,
arXiv, PMLR, dblp or the publisher's landing page; the rules applied — including which
entries deliberately carry **no** DOI, and the four keys that were renamed so key year
matches cited year — are recorded in the `FOOTER` comment of `assemble_paper_en.py`.
Four *Agronomy* entries (`xu2023agronomy`, `wen2022agronomy`, `ecimduric2024`,
`padillanates2025`) were added at the retarget, so the count is **48**.

If the submission moves to BibTeX (which `mdpi.cls` expects, with `\bibliography{}` and
the `mdpi` bibliography style):

- convert the `ENTRIES` dict in `assemble_paper_en.py` into a `.bib` file; the fields are
  already in MDPI order, so this is mechanical;
- `ross2011` already exists in `paper/build_ru/references.bib` as `ross2011dagger` —
  **re-key, do not add a duplicate**;
- `veremey2016` from `statya_ru.tex` is not cited in the English manuscript and must not
  be carried over.

`ross2011` is cited in exactly one place, solely to **disclaim** the DAgger label for the
on-policy re-identification loop. It is not an attribution and must never become one.

---

## 5. Figures

Six floats: five numbered body figures and an unnumbered graphical abstract.
`figures/SPEC.md` is the specification; `figures/_plotstyle.py` owns the dedup key and
the solver-abort rule, and no figure script reads a CSV directly.

| # | Label | File | On disk? |
|---|-------|------|----------|
| 1 | `fig:kappa` | `fig1_selection_and_conditioning.pdf` | yes |
| 2 | `fig:pareto` | `fig2_pareto_margin_violations.pdf` | yes |
| 3 | `fig:lambda` | `fig3_lambda_survival_knockin.pdf` | yes |
| 4 | `fig:perturb` | `fig4_sensitivity_perturbation_prices.pdf` | yes |
| 5 | `fig:disc-corrections` | `fig5_corrections_waterfall.pdf` | yes |
| — | (unnumbered) | `fig-graphical-abstract.pdf` | yes |

State and actions:

1. **The graphical abstract is unnumbered** (fixed 2026-08-28). The float carries
   `\captionsetup{labelformat=empty}` and no `\label`; the one mention of it in the
   Conclusions names it instead of `\ref`-ing it, and the Word build labels the caption
   "Graphical Abstract." Before this, the body pointed at a "Figure 6" that no caption
   defined. Upload `fig-graphical-abstract.pdf` (or its PNG) as the graphical abstract
   file as well — the submission form asks for it separately.
2. Supply **both** the vector PDF and the 600 dpi PNG; MDPI accepts either but asks for
   ≥1000 dpi bitmap or vector, and the PNGs are already emitted next to each PDF. The
   Word file embeds the PNGs, since Word cannot embed PDF.
3. Widths are set for MDPI's single (8.5 cm) and double (17.5 cm) column measures, and
   every figure is now *drawn* at the width it is *printed* at — Figure 2 was widened to
   17.5 cm on 2026-08-28 for exactly that reason. The `\includegraphics[width=...]`
   values in the sections are relative (`\linewidth` / `\textwidth`) and need no change.
4. Annotations no longer sit on the data: corner notes carry a background
   (`_plotstyle.annotate_n`), and the point labels of Figures 1c, 2, 4, 5 and the
   graphical abstract were re-placed against Word page proofs.

Four figures were **dropped** during consolidation (ten floats → six):
`fig01_selection_reversal`, `fig-ladder-scatter`, `fig-methods-design` and
`fig-knockin-distribution`. Each removal is recorded as a comment block at the site where
the float used to be, naming where its content now lives. `fig-methods-design` — the
design schematic — is the one that could be restored at zero cost to the argument if a
reviewer asks for a design overview; the other three would re-create the duplication that
consolidation removed.

---

## 6. Class and preamble

| Now | At submission |
|---|---|
| `\documentclass[11pt,a4paper]{article}` | `\documentclass[agronomy,article,submit,pdftex,moreauthors]{Definitions/mdpi}` |
| `\title{}` / `\author{}` / `\maketitle` | `\Title{}`, `\Author{}`, `\AuthorNames{}`, `\address{}`, `\corres{}` |
| `\begin{abstract}` in the body | MDPI `\abstract{}` in the front matter |
| `\noindent\textbf{Keywords:}` | `\keyword{}` |
| manual back-matter block | the six macros in §2 |
| `thebibliography` | `\bibliography{}` + the `mdpi` style, or `\begin{thebibliography}` kept verbatim |
| `\usepackage{geometry}`, `caption`, `xcolor` | supplied by `mdpi.cls`; remove to avoid option clashes |

`amsmath`, `amssymb`, `graphicx`, `booktabs`, `array`, `url` and `hyperref` are either
loaded by `mdpi.cls` or safe to keep. `xcolor` is used only by the red placeholder
markers and should disappear with them.

---

## 7. Pre-flight checklist

Author-supplied, and nothing else can proceed without them:

- [x] Author names and affiliations supplied (nine authors, four DSTU units) —
      **confirm the transliterated names and the English unit names**
- [ ] Confirm who is the corresponding author (`A.T.C.` at present)
- [x] ORCID iD for the corresponding author (MDPI requires it); six of nine
      supplied — M.S.K., M.S.Kh. and M.N.K. have none, which does not block
- [x] Institutional e-mail for every author
- [ ] Author Contributions: a draft by position is in `authors.json`; **every
      author confirms the roles attributed to them**
- [ ] Funding statement supplied (or the explicit "no external funding" sentence)
- [ ] Conflicts of Interest: "The authors declare no conflicts of interest." is
      in the file — it must be true of every author, or be replaced
- [ ] Acknowledgments written, or set to "Not applicable."
- [ ] Replication tree archived, DOI minted, Data Availability statement completed

Mechanical, and done unless noted:

- [x] Abstract ≤200 words (188 at last check) and no scope qualifier lost
- [x] `fig5.pdf` also written as `fig5_corrections_waterfall.pdf`
- [x] Graphical abstract unnumbered, in the LaTeX and in the Word build
- [x] Display equations numbered (1)–(3) at the right margin
- [x] Every table repeats its header row; page fields refresh on open
- [x] `assemble_paper_en.py`, `verify_paper_en.py`, `make_docx.py`,
      `format_mdpi_docx.py` and `audit_mdpi.py` all re-run clean
- [ ] Close and delete `paper_en_mdpi_simulation_short_captions.docx` (open in Word)
- [ ] Re-export the `.docx` from Word and re-read the pages after the author fields
      are filled in — the front matter reflows
- [ ] No `[[...REQUIRED]]` string survives anywhere in the exported PDF
- [ ] Only if a `.tex` submission is wanted: `pdflatex` on a machine with TeX
