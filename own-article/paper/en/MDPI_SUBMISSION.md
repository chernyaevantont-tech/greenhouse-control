# What changes at submission to MDPI *Agronomy*

Written 2026-08-14. This file exists because `paper_en.tex` deliberately does **not**
use `mdpi.cls`: that class is not present on this machine, and a manuscript that cannot
be compiled is worse than one that compiles in the standard `article` class. Everything
below is the delta between what is in the tree today and what MDPI needs.

Nothing here is a formatting nicety. Items marked **BLOCKER** stop the submission.

---

## 0. Regenerate first, always

`paper_en.tex` is assembled by concatenation and is overwritten on every run. Edit the
five section files and `assemble_paper_en.py`, never `paper_en.tex`.

```
python own-article/paper/en/assemble_paper_en.py   # rebuild paper_en.tex
python own-article/paper/en/verify_paper_en.py     # structural + terminology check
```

`verify_paper_en.py` reports environment balance, dangling `\ref`s, float and citation
coverage, the abstract word count, and the terminology guard. It is **not** a LaTeX
compiler — no TeX distribution is installed here. Compile once before submission.

---

## 1. Author block — **BLOCKER**

`assemble_paper_en.py` carries a placeholder author block whose contents are
`[[...REQUIRED]]` strings in red. **No name, initial, affiliation, e-mail or ORCID has
been invented anywhere in this manuscript.** That is deliberate and must stay that way
until a human supplies the real values. The block itself lists the eight items needed;
the short version:

| # | Item | Where it goes |
|---|------|---------------|
| 1 | Full author names, in final author order | `\author{}` |
| 2 | ORCID iD per author (mandatory for the corresponding author) | `\author{}` |
| 3 | Full postal affiliation per institution, numbered | `\author{}` footnotes |
| 4 | Corresponding author + institutional e-mail | `\thanks{}` → MDPI `\corres` |
| 5 | E-mail of every co-author | MDPI prints these in the affiliation block |
| 6 | CRediT roles by initials | Author Contributions, back matter |
| 7 | Funding statement with grant numbers, or "no external funding" | Funding, back matter |
| 8 | Conflict-of-interest declaration from every author | Conflicts of Interest, back matter |

Under `mdpi.cls` these become `\Author{}`, `\AuthorNames{}`, `\address{}`, `\corres{}`,
`\firstnote{}`. The mapping is one-to-one; only the macro names change.

---

## 2. Back matter

The assembler emits an MDPI back-matter block between the Conclusions and the
bibliography, in MDPI's required order. Under `mdpi.cls` each becomes its own macro:

| Statement in `paper_en.tex` | `mdpi.cls` macro | State today |
|---|---|---|
| Author Contributions | `\authorcontributions{}` | **placeholder — BLOCKER** |
| Funding | `\funding{}` | **placeholder — BLOCKER** |
| Institutional Review Board Statement | `\institutionalreview{}` | real: *Not applicable* |
| Informed Consent Statement | `\informedconsent{}` | real: *Not applicable* |
| Data Availability Statement | `\dataavailability{}` | real, except the public URL/DOI — **BLOCKER** |
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

MDPI's limit is **200 words**. The abstract measured **198** at the last structural check
(it was 248 before the mechanism rewrite trimmed it). Two words of headroom is not a
margin: re-run `verify_paper_en.py` after every edit to the abstract, because the section
is under active revision and one added clause puts it over.

Do **not** cut, in any trim: *"in the first-order, undenoised block under sparse
estimators"*, *"against three comparators"*, *"deterministic reference"*, or the Pareto
sentence. Each is a scope limit that was added to fix an overstatement, and removing one
re-creates a defect the verification passes were run to remove. `REMAINING.md` §4.15
lists the cheapest 48 words to lose instead.

---

## 4. Bibliography

The manuscript uses a manual `thebibliography` block, emitted by the assembler in
first-citation order. All 44 entries were verified on 2026-08-14 against Crossref,
arXiv, PMLR, dblp or the publisher's landing page; the rules applied — including which
entries deliberately carry **no** DOI, and the four keys that were renamed so key year
matches cited year — are recorded in the `FOOTER` comment of `assemble_paper_en.py`.

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

Six floats: five numbered body figures and the graphical abstract. `figures/SPEC.md` is
the specification; `figures/_plotstyle.py` owns the dedup key and the solver-abort rule,
and no figure script reads a CSV directly.

| # | Label | File | On disk? |
|---|-------|------|----------|
| 1 | `fig:kappa` | `fig1_selection_and_conditioning.pdf` | yes |
| 2 | `fig:pareto` | `fig2_pareto_margin_violations.pdf` | yes |
| 3 | `fig:lambda` | `fig3_lambda_survival_knockin.pdf` | yes |
| 4 | `fig:perturb` | `fig4_sensitivity_perturbation_prices.pdf` | yes |
| 5 | `fig:disc-corrections` | `fig5_corrections_waterfall.pdf` | **no — generator writes `fig5.pdf`; rename** |
| — | `fig:graphical-abstract` | `fig-graphical-abstract.pdf` | yes |

Actions at submission:

1. **Rename `fig5.pdf` → `fig5_corrections_waterfall.pdf`.** The `\includegraphics` path
   in `04-discussion.tex` already carries the SPEC name; the generator has not caught up.
2. **The graphical abstract must stop being Figure 6.** It is currently a numbered
   `figure` environment sitting in Section 5, so it prints as "Figure 6". Under
   `mdpi.cls` it moves to the front matter, where MDPI wants it and where its
   duplication with Figures 1a and 2 is expected. If the standard class is kept for any
   reason, make it unnumbered in place (`\captionsetup{labelformat=empty}` inside the
   float, or `\includegraphics` with a plain `\centering` paragraph).
3. Supply **both** the vector PDF and the 600 dpi PNG; MDPI accepts either but asks for
   ≥1000 dpi bitmap or vector, and the PNGs are already emitted next to each PDF.
4. Widths are set for MDPI's single (8.5 cm) and double (17.5 cm) column measures. The
   `\includegraphics[width=...]` values in the sections are relative
   (`\linewidth` / `\textwidth`) and need no change.

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

- [ ] Author names, ORCIDs, affiliations, corresponding author and e-mails supplied
- [ ] Author Contributions written in CRediT roles, initials matching the author block
- [ ] Funding statement supplied (or the explicit "no external funding" sentence)
- [ ] Conflicts of Interest declared by every author
- [ ] Replication tree archived, DOI minted, Data Availability statement completed
- [ ] Abstract still ≤200 words (198 at last check) and no scope qualifier lost
- [ ] `fig5.pdf` renamed to `fig5_corrections_waterfall.pdf`
- [ ] Graphical abstract moved to the front matter or made unnumbered
- [ ] `assemble_paper_en.py` re-run, `verify_paper_en.py` clean apart from intended items
- [ ] `pdflatex` run at least once on a machine that has a TeX distribution
- [ ] No `[[...REQUIRED]]` string survives anywhere in the compiled PDF
