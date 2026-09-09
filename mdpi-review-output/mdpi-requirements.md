# MDPI requirements applied to this manuscript

All pages were read on **2026-09-07** from the official MDPI site, through the in-app
browser (`www.mdpi.com` returns HTTP 403 to plain fetchers).

## Journal and article type — determined, not guessed

| Item | Value | Evidence |
|---|---|---|
| Journal | **Agronomy** (MDPI) | `own-article/paper/en/MDPI_SUBMISSION.md` is written against Agronomy; `mdpi-template/agronomy-template.docx` is the official template in the repo; the styling pass validates against it |
| Article type | **Article** (original research) | Front matter + Introduction / Materials and Methods / Results / Discussion / Conclusions, 16 tables, 5 numbered figures, original simulation results |
| Study design | **In silico / simulation study** — no human subjects, no animals, no field trial | Title says "an in silico study"; Methods describe the GreenLight model driven by ERA5 weather |
| Submission route | **Microsoft Word** (`.docx`) | Recorded decision of 2026-08-28: no TeX distribution on this machine; LaTeX is the content source of truth, Word is what uploads |

## Sources consulted

| # | Page | URL | Checked |
|---|---|---|---|
| 1 | Agronomy — Instructions for Authors | https://www.mdpi.com/journal/agronomy/instructions | 2026-09-07 |
| 2 | MDPI Author Layout / Style Guide | https://www.mdpi.com/authors/layout | 2026-09-07 |
| 3 | MDPI Research and Publication Ethics | https://www.mdpi.com/ethics | 2026-09-07 |
| 4 | MDPI Research Data Policies (within #1 and #3) | https://www.mdpi.com/ethics | 2026-09-07 |

**Note on "MDPI English Editing Guidelines":** `https://www.mdpi.com/authors/english`
redirects to *MDPI Author Services*, a paid editing-service page with no editorial rules
on it. The operative English rules are §3–§6 of the Layout Style Guide (source #2), and
those are what was applied. No general-MDPI rule below is presented as an Agronomy-specific
rule; the journal-specific column says which is which.

---

## Requirements applied

### Front matter (source #1, #2)

| Requirement | Exact wording / limit | Source |
|---|---|---|
| Abstract | "should be a total of **about 200 words maximum**", single paragraph, structured style **without headings** (Background / Methods / Results / Conclusion) | #1 |
| Abstract fidelity | "must not contain results which are not presented and substantiated in the main text and should not exaggerate the main conclusions" | #1 |
| Keywords | "**Three to ten** pertinent keywords" | #1 |
| Title | concise, specific; periods avoided; no running title; abbreviations avoided | #2 §2.2 |
| Author names | full first and last name, "Firstname Lastname"; no titles or academic suffixes | #2 §2.3 |
| Affiliations | institution, city, post code, country; department before university; PubMed/MEDLINE format | #1, #2 §2.3 |
| GenAI | "GenAI tools and other large language models (LLMs) **cannot be listed as authors**" | #1 |

### Structure (source #1)

Research manuscripts comprise — Front matter: Title, Author list, Affiliations, Abstract,
Keywords. Body: **Introduction, Materials and Methods, Results, Discussion, Conclusions
(optional)**. Back matter: **Supplementary Materials, Author Contributions, Funding, Data
Availability Statement, Acknowledgments, Conflicts of Interest, References**.

Agronomy additionally requires: *"The authors need for a subsection in the materials and
methods on experimental design and statistical description… so that an independent
researcher could reproduce their research"*, listing software with version and packages.

Agronomy has **no maximum length** provided the text is concise and comprehensive.

### Back matter statements (source #1)

- **Data Availability Statement — mandatory.** "authors are required to provide details
  regarding where data supporting their reported results can be found, **including links
  to publicly archived datasets**". A statement is required even when data are unavailable.
- **Funding** — "This research received no external funding" or "This research was funded
  by [name of funder], grant number [xxx]"; funder spelling per Crossref Funder Registry.
- **Author Contributions** — CRediT paragraph in MDPI's fixed wording and role order.
- **Institutional Review Board / Informed Consent** — required as statements even when
  negative; "Not applicable" is correct for a study with no human or animal subjects.
- **Conflicts of Interest** — required; must also declare any funder role, or state
  "The sponsors had no role in the design, execution, interpretation, or writing of the study".

### References (source #1)

- Numbered **in order of appearance in the text**, including table captions and figure legends.
- In text: square brackets **before the punctuation** — `[1]`, `[1–3]`, `[1,3]`.
- DOIs "are not mandatory but highly encouraged".
- Full titles, ACS-style entries; the per-type formats (journal, book, thesis, proceedings,
  website) are given verbatim in source #1.

### Figures, schemes and tables (source #1)

- "high quality (**preferably no less than 600 dpi**) in PNG, JPEG or TIFF formats", RGB 8-bit.
- Numbered in order of appearance; placed close to first citation.
- "figures should contain only English text and the correct mathematical symbols, e.g.,
  **- instead of —** and **decimal points instead of commas**".
- "A **comma** should be added in numbers of **five or more digits** in all figures, schemes
  and tables."
- All table columns need an explanatory heading; font no smaller than 8 pt.
- Every special character in an image (`*`, `**`, `#`) needs a caption explanation.

### Graphical abstract (source #1)

- Minimum **560 × 1100 px (height × width)**; PNG, JPEG or TIFF.
- "should **not** be exactly the same as any figure in the body of the paper".
- Must not carry "Graphical Abstract" as a heading inside the image.

### Language and typography (source #2)

| Rule | Detail | §|
|---|---|---|
| Abbreviations | defined separately in **three places**: the abstract, the main text, and the first figure/table caption | 3.5 |
| Tenses — Methods | simple past; "The present perfect should be avoided" | 4.1.2 |
| Tenses — Results | past tense for what happened in this study is "the best option"; speculation must be separated into its own sentence | 4.1.3 |
| US vs British | either is allowed, "however, **authors must be consistent throughout the paper**"; American recommended unless the authors work in a country using another variant | 4.3 |
| Voice and person | active or passive, first or third person all permitted; "Stylistic consistency, conciseness, and clarity should be prioritized" | 4.5 |
| Hyphens and dashes | hyphen joins words; **en dash** for ranges and two-name concepts (Bose–Einstein); **em dash** introduces a clarifying phrase | 5.3 |
| Em dashes | "**For MDPI papers, em dashes are preferred to colons** when introducing phrases that provide clarification or definitions. Spaces should not be included either side of em dashes… **We recommend using em dashes sparingly**" | 5.3 |
| Numbers | digits normally; **numbers 0–9 written as words unless they carry a unit**; a sentence-initial number is always written out; comma separator at **five or more digits** | 6.1 |
| Units | space between number and unit; **no space** before `%` or the angle `°`; but `90 °C`; SI units required | 6.2 |

### Ethics and GenAI (sources #1, #3)

- **Disclosure rule, verbatim (source #1, Materials and Methods):** *"authors are required
  to disclose in this section details of how GenAI has been used in the paper (e.g., to
  generate text, data or graphics or assist in study design or data collection, analysis
  or interpretation). **The use of GenAI for superficial text editing (e.g., regarding
  grammar, spelling, punctuation and formatting) does not need to be declared.**"*
- Acknowledgments carry the GenAI wording template when GenAI was used substantively.
- **Preregistration (source #1):** *"Where authors have preregistered studies or analysis
  plans, **links to the preregistration must be provided in the manuscript**."*
- Code: "authors should release the code either by depositing in a recognized, public
  repository such as GitHub or uploading as supplementary information"; software name,
  version, corporation and location must be indicated.

---

## Reporting standard: none of the listed ones applies

PRISMA, CONSORT, STROBE, ARRIVE, CARE and TRIPOD were each considered and **none is
applicable**, and none should be force-fitted:

| Standard | For | Applies here? |
|---|---|---|
| PRISMA | systematic reviews / meta-analyses | No — this is primary computational research |
| CONSORT | randomised controlled trials | No — no trial, no participants |
| STROBE | observational epidemiology | No — no human observations |
| ARRIVE | animal research | No — no animals |
| CARE | clinical case reports | No |
| TRIPOD | clinical prediction models for diagnosis/prognosis | No — the models predict greenhouse climate, not patient outcomes |

The governing standards for this design are MDPI's **Research Data Policies** and
**Computer Code and Software** rules (source #1), which the manuscript addresses through
its regeneration tree, frozen configuration hash, acceptance gates and determinism
self-test. The one unmet part is the public archive link — see `review-report.md` C-1.
