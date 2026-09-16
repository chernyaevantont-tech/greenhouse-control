# MDPI *Agronomy* review output — 2026-09-07

> **Ported 2026-09-14.** Everything this review changed in `manuscript-revised/` — the
> Critical corrections C-3…C-6, the Major/Applied items, the language and anti-slop passes
> and the figure-generator fixes — was three-way-merged into the canonical
> `own-article/paper/en/` tree and rebuilt (`paper_en_mdpi.docx`, figures, deposit
> archive). `manuscript-revised/` is now a historical record, not a working copy; do not
> edit it or build from it. The two places where the merge deliberately departs from the
> revised copy (the "applied open-loop axes" wording kept, the second DOI placeholder in
> Methods §2.5 not adopted) are recorded in `own-article/paper/en/REMAINING.md` §0.

Review of *Multi-step stability selects sparse surrogate models for economic greenhouse
climate control: an in silico study of feature-library design and actuator-pathway survival*.

**No original file was overwritten by the revision.** All edits were made to copies in
`manuscript-revised/`.

## Read in this order

| File | What it answers |
|---|---|
| **`archive-text-audit-2026-09-16.md`** | Text audit of the deposit archive: `final/NUMBERS.md` contradicts the manuscript, `figures/SPEC.md` is an internal document, "pre-registered" survives in 11 code sites, and the code docstrings carry the assistant register and the revision history. §7 records the application of all six items on 2026-09-16 (NUMBERS.md regenerated from the manuscript checks, SPEC.md and the cluster plan excluded, docstrings scrubbed, archive `89504527…`). Russian. |
| **`review-2026-09-15.md`** | **Latest manuscript review.** Readiness re-check of the current `paper_en_mdpi.docx` (gates re-run, deposit, cover letter, special issue) and a full peer review. Finds a dropped `Đ` in a cited author's name, a 20/11 → 21/12 manifest count, a deposit README that contradicts the manuscript, and shows which significance claims survive a seed-level (n = 20) analysis. Russian. |
| **`review-report.md`** | The 07–08.09 review. Findings by Critical / Major / Minor / Style. |
| `mdpi-checklist.md` | 55-item pass/block/check table against MDPI Agronomy. |
| `unverified-claims.md` | Everything needing an author decision, and what this review could *not* establish. |
| `change-log.md` | Every one of the 42 changed lines: location, before, after, reason, category. |
| `anti-slop-audit.md` | AI-tell scan; what was found, fixed, and deliberately not fixed. |
| `ai-marker-audit-2026-09-14.md` | **14.09, on the current `paper_en_mdpi.docx`.** Literature-derived marker lists (Kobak, Liang, PMC-135, Wikipedia, 2025–26 Claude-isms, MDPI AI policy), a 137-category regex scan (GPT-era vocabulary: zero hits) and a 180-agent semantic audit with three refuters per finding: 165 + 11 document-level confirmed items, all in the current-model register (epigrammatic closers, `What X does` clefts, `X, not Y` tails, staged candour, `buys`/`genuinely`, duplicated caveats). Priorities in its §4; §6 records that they were applied the same evening (124 edits, gates green, docx rebuilt). Russian. |
| `ai-marker-scan-2026-09-14.md` | Raw protocol of the regex scan (Word paragraph numbers). |
| `reference-audit.md` | 48 references; DOI verification against Crossref and DataCite. |
| `mdpi-requirements.md` | The exact requirements applied, with URLs and check dates. |
| `tools-installed.md` | What was installed, from where, why, and what was rejected. |

## The revised manuscript

`manuscript-revised/`

| File | Role |
|---|---|
| **`manuscript-revised-mdpi.docx`** | **The submission candidate.** Styled into the official Agronomy template. |
| `manuscript-revised.docx` | Intermediate pandoc output, before MDPI styling. |
| `paper_en_revised.tex` | Assembled LaTeX, revised. |
| `01-…` … `05-….tex` | The five revised section files — the content source of truth. |
| `figures/`, `make_docx.py`, `format_mdpi_docx.py`, `authorship.py`, `authors.json` | Build inputs, kept so the `.docx` can be rebuilt from the revised sections. |

Rebuild after further edits to the section files:

```bash
python make_docx.py && python format_mdpi_docx.py
```

## Bottom line

**Not yet submittable — two blocking items, neither of them a writing problem:**

1. **C-1** — the Data Availability Statement has no public DOI. The Zenodo deposit is
   prepared but not made.
2. **C-2** — "pre-registered" is claimed five times with no preregistration link. Either
   supply the link or change the word to "pre-specified".

> **C-2 closed 2026-09-09.** Both halves were done: every occurrence now reads
> "pre-specified", and the protocol itself was translated into English and added to the
> deposit as `EXPERIMENT_PROTOCOL.md`, with Section 2.5 pointing at it. C-1 is still open
> and still needs the DOI.

Everything else is either passing or a listed author decision.

## Integrity of the revision

Verified after all edits: **no printed number was lost or altered**; citation keys,
`\label`/`\ref` targets, 16 tables, 6 figures, 3 equations and 48 bibliography entries are
identical to the original. The only numeric additions are 24 word-to-digit conversions,
all ≥10, enumerated in `change-log.md`.

The project's own gate — 758 table cells and 336 prose values recomputed from source data,
1,953 printed numbers walked, **0 unclaimed, 0 mismatches** — passes on the original, and
the rebuilt `.docx` clears all 14 package checks plus 9 pandoc-stage checks.
