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

### One genuine discrepancy — author decision required

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
