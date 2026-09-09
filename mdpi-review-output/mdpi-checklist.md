# MDPI *Agronomy* submission checklist

Checked 2026-09-07 against the revised manuscript
(`mdpi-review-output/manuscript-revised/`). Requirement sources and dates:
`mdpi-requirements.md`.

Legend: **PASS** — verified · **BLOCK** — stops submission · **CHECK** — needs an author
decision · **n/a** — does not apply to this study.

---

## Front matter

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Title concise, specific, no running title, no periods | **PASS** | Names design ("an in silico study") and mechanism; no abbreviations beyond none |
| 2 | Author full first and last names, "Firstname Lastname" | **PASS** | Nine authors, e.g. "Ivan I. Naumov" |
| 3 | Affiliations: department, institution, street, post code, city, country | **PASS** | Four numbered DGTU affiliations, "1 Gagarin Square, 344003 Rostov-on-Don, Russia" |
| 4 | E-mail for every author | **PASS** | All nine institutional `@donstu.ru` addresses present |
| 5 | Corresponding author designated | **PASS** | `$^{*}$Correspondence: inaumov@donstu.ru` |
| 6 | ORCID for corresponding author (mandatory) | **PASS** | Naumov `0000-0002-8582-3203` |
| 7 | ORCID for co-authors (encouraged) | **CHECK** | 6 of 9 present; missing for Kilina, Kharina, Kulinich → M-2 |
| 8 | Abstract ≈200 words maximum | **PASS** | **190 words** |
| 9 | Abstract a single paragraph, structured style without headings | **PASS** | Background → Methods → Results → Conclusion, one paragraph |
| 10 | Abstract contains no result absent from the main text; does not exaggerate | **PASS** | Every abstract figure recomputed by the numeric gate; closes "establish comparative simulation evidence rather than field performance" |
| 11 | Keywords 3–10 | **PASS** | 8 |
| 12 | GenAI not listed as an author | **PASS** | Nine human authors |

## Structure

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 13 | Introduction / Materials and Methods / Results / Discussion / Conclusions | **PASS** | Five numbered sections, validated by the package audit |
| 14 | Agronomy: Methods subsection on experimental design and statistics | **PASS** | "Simulation study design, site, weather and cropping season" + "Statistical treatment" |
| 15 | Methods detailed enough to replicate | **PASS** | Identification ladder, MPC formulation, stage cost, tuning protocol, statistical treatment, reproducibility and its limits |
| 16 | Software name **and version** stated | **CHECK** | IPOPT named without version; `gl_gym 0.3.1` only in the Data Availability Statement; CasADi and Python versions absent → m-4 |
| 17 | Code publicly released or supplied as supplementary | **CHECK** | Regeneration driver described in detail but no public repository URL → folded into C-1 |
| 18 | Preregistration link supplied where preregistration is claimed | **BLOCK** | "pre-registered" used at 5 sites with no link → **C-2** |
| 19 | Abbreviations defined separately in abstract, main text, first caption | **PASS** | MPC defined in the abstract and again in the body |
| 20 | SI units | **PASS** | °C, EUR m⁻², kW·h; no imperial units |

## Back matter (MDPI order)

| # | Statement | Status | Content |
|---|---|---|---|
| 21 | Supplementary Materials | **PASS** | "Not applicable." |
| 22 | Author Contributions (CRediT, MDPI wording) | **CHECK** | Complete and correctly worded; roles assigned by job title and still need each author's confirmation → M-3 |
| 23 | Funding | **PASS** | Ministry of Science and Higher Education of the Russian Federation, agreement **075-15-2025-592** of 24 June 2025 |
| 24 | Institutional Review Board Statement | **PASS** | "Not applicable" — correct for a simulation study with no human or animal subjects; correctly retained rather than deleted |
| 25 | Informed Consent Statement | **PASS** | "Not applicable" |
| 26 | **Data Availability Statement with a link to a public archive** | **BLOCK** | Detailed and honest, but points at a repository-internal path; carries the author's own red `[[REQUIRED BEFORE SUBMISSION]]` marker → **C-1** |
| 27 | Acknowledgments | **PASS** | "Not applicable." |
| 28 | Conflicts of Interest | **PASS** | "The authors declare no conflicts of interest." |
| 29 | Funder-role declaration in Conflicts of Interest | **CHECK** | MDPI asks for an explicit statement of the sponsor's role, or "The sponsors had no role in the design, execution, interpretation, or writing of the study". Not present |
| 30 | Back-matter order matches MDPI | **PASS** | Verified by the package audit |

## References

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 31 | Numbered in order of first appearance | **PASS** | Order matches the list exactly |
| 32 | Every in-text citation present in the list | **PASS** | 48 cited / 48 defined, no orphans, no duplicates |
| 33 | Square brackets placed before punctuation | **PASS** | 0 citations after punctuation |
| 34 | DOIs (encouraged) | **CHECK** | 32 of 48 carry a DOI; 13 entries have none → m-3 |
| 35 | DOIs correct | **PASS** | 25 verified clean at Crossref; 5 flags resolved as checker artefacts; 1 year discrepancy → M-4 |
| 36 | No retracted sources | **CHECK** | No Crossref retraction record on any of the 32 DOIs, but this is not proof → `reference-audit.md` |

## Figures and tables

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 37 | ≥600 dpi, PNG/JPEG/TIFF | **PASS** | All 11 PNG at 600 dpi |
| 38 | Numbered in order of appearance, near first citation | **PASS** | 5 numbered figures, 16 tables; sequence validated by the package audit |
| 39 | Graphical abstract ≥560 × 1100 px (h × w), unnumbered | **PASS** | 1514 × 4013 px; validated as unnumbered |
| 40 | Graphical abstract not identical to a body figure | **CHECK** | Only 5 figures are numbered and the GA is separate, but `fig6.png` and `fig-graphical-abstract.png` share identical dimensions. **[AUTHOR CHECK: confirm the GA is not also submitted as a numbered body figure]** |
| 41 | Every table column has an explanatory heading | **PASS** | Verified by the package audit |
| 42 | Three-line tables with repeating header rows | **PASS** | "every data table repeats its header row" |
| 43 | Figures use hyphen not em dash, decimal points not commas | **PASS** | Figure generators enforce a decimal point; no em dash in axis labels |
| 44 | Comma separator at five or more digits in tables and figures | **CHECK** | The manuscript prints violation counts in the thousands (e.g. `6006`, `5424`, `4339`) — all four-digit, so the rule does not yet bite. **[AUTHOR CHECK: if any five-digit count appears in a table or figure, add the comma]** |
| 45 | Equations editable, not images; numbered | **PASS** | 3 numbered equations; "no hand-written number left in the maths" |

## Language (Layout Style Guide §4–§6)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 46 | US or British English used consistently | **PASS after revision** | Was mixed on one stem (`optimizer`/`optimiser`); normalised to British, which the rest of the manuscript uses throughout |
| 47 | Numbers 0–9 as words, ≥10 as digits, sentence-initial written out | **PASS after revision** | 24 mid-sentence numerals converted; 4 sentence-initial correctly left as words |
| 48 | No colloquial contractions | **PASS** | 0 occurrences |
| 49 | Space between number and unit; none before `%` or angle `°` | **PASS** | `20~\%`, `24~h`, `\textdegree C` |
| 50 | Tense discipline (Methods simple past; no present perfect) | **PASS** | Methods in simple past; results reported as what happened in this study |
| 51 | En dash for ranges and two-name concepts | **PASS** | 30 numeric ranges (`2020--2023`), `margin--violation` |
| 52 | Em dashes used sparingly | **PASS, with a noted disagreement** | 0 true em dashes in body prose; 118 spaced en dashes serve that function (~1 per 260 words). MDPI *prefers* this construction to colons — see `anti-slop-audit.md` |

## Ethics

| # | Requirement | Status |
|---|---|---|
| 53 | GenAI use disclosed in Materials and Methods where it exceeds superficial editing | **CHECK** — no statement present; only the authors know the full history → M-1 |
| 54 | Research involving humans / animals / plants (field) | **n/a** — computational study of a greenhouse climate simulator |
| 55 | Clinical trial registration | **n/a** |
| 56 | Applicable reporting standard (PRISMA/CONSORT/STROBE/ARRIVE/CARE/TRIPOD) | **n/a** — none applies to an in silico control study; each was considered and excluded in `mdpi-requirements.md` |
| 57 | Cover letter with the two required statements | **CHECK** — `cover_letter.docx` exists but was not part of this review. **[AUTHOR CHECK: confirm it carries both MDPI-mandated sentences]** |

---

## Score

- **PASS: 37**
- **BLOCK: 2** — C-1 (Data Availability link), C-2 (preregistration link)
- **CHECK: 12** — author decisions, listed in `unverified-claims.md`
- **n/a: 4**

**Two blocking items. Both are missing external facts — a DOI and a registration link —
that only the authors can supply. Neither is a writing problem.**
