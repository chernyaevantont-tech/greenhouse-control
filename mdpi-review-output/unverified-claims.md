# Unverified claims and author decisions

Everything this review could **not** establish, and everything that needs a human answer.
Nothing below was guessed, filled in or silently corrected.

---

## 1. Facts that do not exist yet and cannot be invented

| # | Item | Why it cannot be supplied here |
|---|---|---|
| U-1 | **Public DOI / URL for the data** | The Zenodo deposit is prepared (`ZENODO.md`: `greenhouse-control-regen-data-v1.0.zip`, 5.97 MB, 625 entries, SHA-256 `b767d361…dc94b`) but **has not been made**. A DOI cannot be written before it is minted. Inventing one would be fabrication. → C-1 |
| U-2 | **Preregistration link** | "Pre-registered" is claimed at 5 sites. Whether a public, timestamped registration exists is a fact about what the authors did in the past, not something recoverable from the manuscript. → C-2 |
| U-3 | **Three missing ORCID iDs** | Kilina, Kharina, Kulinich. An ORCID cannot be derived from a name. → M-2 |
| U-4 | **Whether GenAI was used beyond superficial editing** | Only the authors know the production history of the text, figures and analysis. This review's own edits are within MDPI's declared exemption (grammar, spelling, punctuation, formatting) and need no declaration; anything earlier is unknown here. → M-1 |

## 2. Author confirmations MDPI requires

| # | Item | Note |
|---|---|---|
| U-5 | **Final author order** | Nine authors listed. MDPI: after acceptance, changes to author names or order may not be permitted. |
| U-6 | **CRediT role assignment** | The paragraph is complete and correctly worded, but project records state the split was **proposed by job title** and awaits each author's confirmation. MDPI requires each author to have made a substantial contribution, approved the version, and agreed to be accountable. |
| U-7 | **Corresponding author designation** | Currently Naumov (`inaumov@donstu.ru`). Project records show this was previously assigned to Chernyaev; the designation has changed at least once. Confirm it is final. |
| U-8 | **English transliteration of all nine names and four department names** | These are translations from Russian. A wrong transliteration is a permanent attribution error. |
| U-9 | **Consent to publish e-mail addresses** | MDPI displays all author e-mails; the corresponding author must obtain consent from each co-author. |
| U-10 | **Funder name spelling** | "Ministry of Science and Higher Education of the Russian Federation", agreement 075-15-2025-592. MDPI: use the standard spelling from the Crossref Funder Registry, "any errors may affect your future funding". Not checked against that registry here. |
| U-11 | **Funder role in Conflicts of Interest** | MDPI asks for an explicit statement of the sponsor's role, or "The sponsors had no role in the design, execution, interpretation, or writing of the study". Currently absent. |
| U-12 | **Cover letter** | `cover_letter.docx` exists but was not reviewed. It must carry both MDPI-mandated sentences (not under consideration elsewhere; all authors approve submission). |

## 3. Bibliographic items needing adjudication

| # | Item | Status |
|---|---|---|
| U-13 | `openmeteo2023` year | Entry and key say 2023; DataCite reports publicationYear **2024** for `10.5281/zenodo.7970649`. The weather source is central to the study. → M-4 |
| U-14 | 13 references without DOI or URL | `ljung1999`, `lambert2020`, `jackson2022`, `farahmand2017`, `wei2024`, `haarnoja2018`, `raffin2021`, `holm1979`, `demsar2006`, `ross2011`, `mahalanobis1936`, `lee2018`, `lakshminarayanan2017`. Verified only for internal formatting, against no registry. |
| U-15 | Retraction status of all 48 sources | Crossref returned no retraction record for the 32 registered DOIs, but that is not proof of good standing, and the 16 DOI-less entries were not checked at all. |
| U-16 | **Whether each reference supports the claim it is attached to** | **Not established.** Verifying the 61 citation sites requires reading all 48 sources. This review checked that references *exist* and that their metadata matches, not that they say what the sentence claims. |

## 4. Scientific content this review did not and could not verify

Stated explicitly, because the distinction matters for how much weight to give this report.

| # | Item | Note |
|---|---|---|
| U-17 | **Whether the simulation results are correct** | The project's gate proves the manuscript's numbers **agree with the result files** — 758 table cells, 336 prose values, 1,953 printed numbers, 0 mismatches. It does **not** prove the underlying simulations were correctly specified or executed. Internal consistency is not external validity. |
| U-18 | **Whether the GreenLight model and ERA5 forcing are used correctly** | Domain question, outside a language and compliance review. |
| U-19 | **Whether the statistical treatment is appropriate** | The Holm procedure reproduces exactly under one family definition (15 controllers, step-down, monotone enforcement) and under no other variant tried, which shows the reported values are self-consistent. Whether that family definition is the right one is a reviewer's judgement. |
| U-20 | **Bit-level reproducibility across environments** | The manuscript already limits this claim honestly to one computing environment and states the cross-environment case was never measured. No action needed — recorded so the limitation is not mistaken for an omission. |
| U-21 | **The 105-word Discussion sentence** | Left intact. Splitting it risks the argument; that is the author's judgement to make. |
| U-22 | **Graphical abstract distinctness** | `fig6.png` and `fig-graphical-abstract.png` share identical pixel dimensions. The package audit confirms only 5 numbered figures with the GA unnumbered, so this is probably one file used once — but MDPI requires the GA not duplicate a body figure, so confirm. |
| U-23 | **Five-digit numbers in tables and figures** | MDPI requires a comma separator at ≥5 digits. No five-digit value was found in the current tables (violation counts top out in the thousands). If any appears after a rerun, the rule applies. |

---

## 5. What the review DID establish

For balance, so the list above is not read as a list of doubts about everything:

- Every printed number agrees with the source data, and every printed number is claimed by
  a check — verified before and after revision, with the revision proven to have altered none.
- The reference apparatus is complete and correctly ordered.
- The structure, back matter and figure specifications meet MDPI Agronomy's requirements.
- The abstract does not overstate the results, and the Conclusions do not exceed them.
- Negative results, null findings and a retracted earlier interpretation are all retained
  in the text rather than quietly removed.
