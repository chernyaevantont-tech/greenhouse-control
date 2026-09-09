# Reference audit

Checked 2026-09-07 against `own-article/paper/en/paper_en.tex` (48 entries).
Method: structural checks locally, then each registered DOI resolved against
**Crossref** (`api.crossref.org`), with the one Zenodo DOI resolved against **DataCite**.
Only DOI strings left the machine. **Nothing was corrected automatically.**

## Structural result — clean

| Check | Result |
|---|---|
| `\bibitem` entries defined | 48 |
| Unique keys cited | 48 |
| Citation commands in text | 61 |
| Cited but missing from the list | **none** |
| In the list but never cited | **none** |
| Duplicate keys | **none** |
| Numbered in order of first appearance (MDPI requirement) | **matches exactly** |
| `\cite` placed after punctuation (MDPI wants before) | **0 occurrences** |

## DOI verification

32 of 48 entries carry a DOI. Of those, **25 verified clean**, 6 were flagged by the
automated comparison and **5 of the 6 proved to be artefacts of the checking method**, and
1 needed a different registry.

### Resolved — no action needed (checking artefacts)

| Key | Flag raised | Adjudication |
|---|---|---|
| `ecimduric2024` | first author "Ećim-Đurić" not found | **False positive.** The entry writes `E{\'c}im-{\DJ}uri{\'c}` — correct LaTeX diacritics that the comparator stripped. Entry is right. |
| `wachter2006` | first author "Wächter" not found | **False positive.** The entry writes `W\"achter`. Correct. |
| `brunton2016c` | title mismatch | **False positive.** Crossref stores the title with an acknowledgement footnote concatenated ("…(SINDYc)**SLB acknowled…"). The manuscript's title is the correct one. |
| `cortiella2021` | title mismatch | **False positive.** Crossref stores the title with embedded MathML (`<mml:math…>`). Manuscript title is correct. |
| `xu2023agronomy` | Crossref year 2022, entry says 2023 | **False positive.** *Agronomy* **2023**, *13*, 102 — MDPI's own citation convention uses the issue year; Crossref carries the online-first date. Entry follows MDPI style. |
| `vanhenten1994` | Crossref year 2024, entry says 1994 | **False positive.** Van Henten's PhD thesis is 1994; Wageningen deposited the DOI later. The work year is correct. |

### One genuine discrepancy — author decision required *(decided 2026-09-09, see below)*

| Key | Issue |
|---|---|
| `openmeteo2023` | DOI `10.5281/zenodo.7970649` is a **Zenodo** DOI, so Crossref returns 404 (expected). It **resolves correctly at DataCite**: title "Open-Meteo.com Weather API", publisher Zenodo. But DataCite reports **publicationYear 2024**, while the entry and the citation key say **2023**. Zenodo concept DOIs track their latest version. **[AUTHOR CHECK: confirm whether to cite the 2023 version DOI or update the year to 2024. The weather source is central to the study, so this one should be exact.]** |

## Entries without a DOI, URL or arXiv id (16 of 48)

MDPI: DOIs "are not mandatory but highly encouraged". These are all long-established works
whose bibliographic details are unambiguous, so this is a *Minor* item, not a blocker.

`ljung1999`, `lambert2020`, `jackson2022`, `farahmand2017`, `wei2024`, `haarnoja2018`,
`raffin2021`, `holm1979`, `demsar2006`, `ross2011`, `mahalanobis1936`, `lee2018`,
`lakshminarayanan2017`

**[AUTHOR CHECK: adding DOIs to these 13 would strengthen the submission; `holm1979`,
`demsar2006`, `mahalanobis1936` and `ljung1999` are the ones a reviewer is most likely to
look up.]**

## What this audit did NOT establish

Stated plainly, because the brief asks for it:

1. **Whether each reference actually supports the claim it is attached to.** That requires
   reading all 48 sources. Not done. The 61 citation sites are listed in
   `unverified-claims.md` as a class.
2. **Retraction status.** Crossref's `update-to` field was checked and no retraction notice
   was returned for any of the 32 DOIs, but absence of a Crossref retraction record is not
   proof of good standing. **[AUTHOR CHECK: run the 48 titles through Retraction Watch /
   the Crossref retraction feed before submission.]**
3. **The 16 entries without a DOI** were not verified against any registry at all — only
   their internal formatting was checked.

   > **Closed 2026-09-09 by the second pass below.**


---

# Second pass — 2026-09-09

Every one of the 48 entries was re-checked, this time including the ones that carry no
identifier. Compared for each: title, surname of the first author, and year. For the five
PMLR entries the publisher's own volume index also gave the volume, the page range and the
full author list. Only titles, DOIs and arXiv identifiers left the machine.

## Result: 46 of 48 fully confirmed, 2 confirmed except for their printed page range

| Group | Checked against | Outcome |
|---|---|---|
| 31 DOIs | Crossref | title, first author and year match |
| `openmeteo2023` | DataCite | matches |
| 3 arXiv identifiers | arXiv API | resolve, titles and authors match |
| `lambert2020`, `jackson2022`, `farahmand2017`, `haarnoja2018`, `ross2011` | proceedings.mlr.press volume indexes | volume, page range and every author name match exactly |
| `holm1979`, `demsar2006`, `raffin2021` | OpenAlex, jmlr.org | volume and pages match; the JMLR paper page for `raffin2021` exists |
| `wei2024` | OpenReview | "Accepted by TMLR", 8 February 2024 — the entry's year is right |
| `ljung1999` | OpenLibrary | the book exists, Lennart Ljung, six editions |
| `mahalanobis1936` | Crossref | corroborated by the 2018 Sankhya A reprint, whose own title names the 1936 original |

**No fabricated entry was found.** The six most recent references, where the risk is
highest, all resolve: `mallick2025`, `vanlaatum2025`, `yonezawa2026`, `padillanates2025`,
`controlorientedsurvey2025` (arXiv 2512.06315) and `balanceguided2026` (arXiv 2604.18414).

### The two that are not fully confirmable

`lee2018` and `lakshminarayanan2017`. Title, authors, year and venue are confirmed. Their
printed page ranges (7167–7177 and 6402–6413) come from the printed Curran volumes; the
NeurIPS site does not paginate its proceedings and no open registry carries those numbers,
so they rest on the citation as inherited. Everything else in both entries is verified.

### Two DOIs were considered and rejected

OpenAlex reports `10.2307/4615733` for `holm1979` and `10.5555/1248547.1248548` for
`demsar2006`. Neither resolves: `https://doi.org/...` returns **404** for both, where a
registered DOI returns a 302 to the publisher. They are a JSTOR stable id and an ACM
internal id that OpenAlex stores in its `doi` field. Adding either would have broken the
rule stated in `assemble_paper_en.py` — a DOI appears only where it resolved against the
registry — which already names `holm1979` and the JSTOR id as exactly this case. The
entries stay as they are.

### Year discrepancies — the same four as in the first pass, all explained

Crossref gives 2022 for `xu2023agronomy` and 2005 for `wachter2006` (online-first dates
against the issue year that MDPI style uses), carries no year at all for `vanhenten1994`,
and DataCite gives 2024 for `openmeteo2023` because a Zenodo concept DOI follows its
latest version.

## `openmeteo2023` — decided, 2026-09-09

`10.5281/zenodo.7970649` is the **concept DOI**, confirmed by Zenodo's own `conceptdoi`
and `conceptrecid` fields. It always resolves to the newest version, which today is record
14582479, v1.4.0 of 2024-12-31; that is the whole reason DataCite reports 2024. Six
versions exist, from 0.2.47 of 2023-05-25 to 1.4.0, and the concept DOI was minted with
the first of them in May 2023.

The project asks for exactly this DOI. Its `CITATION.cff` carries
`doi: 10.5281/zenodo.7970649`, described as "Latest release of the Open-Meteo weather API",
and states neither a year nor a version.

**Decision: keep the concept DOI and keep 2023**, and mark it in the entry, which now reads
"Zippenfenig, P. Open-Meteo.com Weather API, 2023; Zenodo (concept DOI, all versions)".

The reasoning, recorded so it is not revisited. 2023 is the year the work first appeared on
Zenodo and the only stable year a concept DOI has; 2024 is the year of a release this study
never used and would be stale again at the next one. A version DOI was rejected because
nothing records which server build answered the requests, and asserting one would be
invented precision in a paper that is careful about exactly that. The values themselves are
ERA5/ERA5-Land, cited separately as `hersbach2020`, so the software version does not bear
on any number reported here; the access date already in the entry is what fixes the data.
The same reasoning is recorded beside the DOI rule in `assemble_paper_en.py`.
