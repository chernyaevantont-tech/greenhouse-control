# Change log

Every edit made to the revised copy. Original files were **not** modified.

- Source of truth edited: `mdpi-review-output/manuscript-revised/0*.tex` (five section files)
- Assembled result: `mdpi-review-output/manuscript-revised/paper_en_revised.tex`
- Line numbers refer to `paper_en_revised.tex`.

**Totals: 42 lines changed in the assembled manuscript. 36 language/MDPI edits, 6
anti-slop edits. No scientific or structural edits were made** — no claim, number, hedge,
limitation or conclusion was altered.

(The same content amounts to 36 changed lines across the five section files; the assembled
file carries six more because the abstract appears in the generated front matter as well
as in `05-conclusions-abstract.tex`. Both copies were edited identically.)

---

## A. Anti-slop — paired em-dash-function inserts (6)

Category: **anti-slop**. Reason for all six: a sentence interrupted twice by a spaced en
dash is the strongest AI-writing tell present in this manuscript. Recast with commas
(short non-restrictive appositive) or parentheses (insert already contains commas, or
precedes a contrastive clause). No word of content changed.

**A-1** — `paper_en_revised.tex:372` (Introduction)
- **was:** `$+1.92$ -- significant, typically small and heavily right-skewed -- while the`
- **now:** `$+1.92$ (significant, typically small and heavily right-skewed), while the`
- **why:** the insert already contains commas, so commas would be ambiguous; parentheses keep the reading unambiguous.

**A-2** — `paper_en_revised.tex:985` (Methods, accounting rules)
- **was:** `(method, seed, test\_year) -- or on the block-specific factor key -- before`
- **now:** `(method, seed, test\_year), or on the block-specific factor key, before`
- **why:** an alternative in a list reads correctly with commas.

**A-3** — `paper_en_revised.tex:1687` (Results, mechanism)
- **was:** `term, while the full library -- worse conditioned still -- keeps the bilinear term as a`
- **now:** `term, while the full library, worse conditioned still, keeps the bilinear term as a`
- **why:** non-restrictive appositive takes commas.

**A-4** — `paper_en_revised.tex:2718` (Discussion, coverage limitation)
- **was:** `has no 2022 season -- all 20 runs exhausted the solver-failure budget -- but that`
- **now:** `has no 2022 season (all 20 runs exhausted the solver-failure budget), but that`
- **why:** parenthetical explanation before a contrastive `but` clause.

**A-5** — `paper_en_revised.tex:2738` (Discussion, mechanism status)
- **was:** `added -- the term-deletion probe below -- and did not disturb the pattern, but the`
- **now:** `added (the term-deletion probe below) and did not disturb the pattern, but the`
- **why:** a forward cross-reference is an aside, not a clause break.

**A-6** — `paper_en_revised.tex:3048` (Conclusions)
- **was:** `threshold -- rather than conditioning alone -- best tracks the non-monotone economic`
- **now:** `threshold, rather than conditioning alone, best tracks the non-monotone economic`
- **why:** contrastive aside takes commas. The retained contrast with "conditioning alone"
  is load-bearing — it marks the retracted earlier reading — and is preserved exactly.

---

## B. Language — British/US consistency (15 sites)

Category: **language**. Rule: MDPI Layout Style Guide §4.3 — either variant is allowed but
"authors must be consistent throughout the paper". The manuscript is uniformly British
(60 `-ise/-isation` forms, 0 US `-ize`; `labelled`, `metre`, `behaviour`, `favour`,
`centre`, `analyse`) except this one stem, which appeared both ways in running prose.

**`optimizer` → `optimiser`, `optimizers` → `optimisers`** at:

| Line | Revised context |
|---|---|
| 308 | `two of the optimiser labels turn out to be bit-identical` |
| 1146 | `two polynomial degrees $\times$ four optimisers $\times$ three denoisers` |
| 1163 | `library and the denoiser, not on degree or optimiser` |
| 1164 | `relation is equally clean at fixed optimiser` |
| 1165 | `comparison below holds the optimiser fixed` |
| 1184 | `Pooled over all four optimiser labels` |
| 1216 | `3 libraries $\times$ 2 sparse optimisers` |
| 1230 | `pools the four optimiser labels ($n=80$ fits per library)` |
| 1240 | `\multicolumn{7}{@{}l}{\emph{All four optimiser labels}}` (table section header) |
| 1366 | `SINDy-MPC leads with an ensemble optimiser` |
| 1377 | `degree, same denoiser, same optimiser, same threshold` |
| 1415 | `not the optimiser, carries the effect` |
| 1667 | `by construction: degree, denoiser, optimiser and threshold` |
| 1805 | `ladder fits at the matching optimiser ($n=20$)` |
| 2027 | `The bootstrap draw of the ensemble optimiser is a real but secondary` |

**Explicitly not changed:** `\texttt{}` code identifiers, CSV column names in provenance
comments, and the reference title *"…and continuous optimization"* in the bibliography —
quoted material must keep its own spelling. The bibliography was excluded from this pass
by construction.

---

## C. MDPI style — numerals ≥10 (24 sites, 21 lines)

Category: **MDPI**. Rule: Layout Style Guide §6.1 — "numbers 0–9 should be written as
words unless they are a measurement"; a sentence-initial number is always written out.

Word → digit, mid-sentence only:

| Line | was → now |
|---|---|
| 128 | `screened, and fifteen controllers were` → `screened, and 15 controllers were` (**abstract**) |
| 290 | `seasons, and fifteen controllers were evaluated` → `seasons, and 15 controllers were evaluated` |
| 319 | `mean margin of the fifteen controllers` → `mean margin of the 15 controllers` |
| 974 | `closed-loop comparison twenty seeds were run` → `closed-loop comparison 20 seeds were run` |
| 1033 | `twelve decimal places: all seven digests` → `12 decimal places: all seven digests` |
| 1050 | `absent from all twenty run manifests` → `absent from all 20 run manifests` |
| 1052 | `eleven distinct values across those twenty manifests` → `11 distinct values across those 20 manifests` |
| 1175 | `middle one by a factor of ten` → `middle one by a factor of 10` |
| 1360 | `canonical wave. Two of the fifteen` → `canonical wave. Two of the 15` |
| 1382 | `recomputed over all fifteen controllers` → `recomputed over all 15 controllers` |
| 1542 | `raised all thirteen pre-existing levels` → `raised all 13 pre-existing levels` |
| 1660 | `economic ranking, ten times above` → `economic ranking, 10 times above` |
| 1690 | `full library -- sixteen of eighteen features` → `full library -- 16 of 18 features` |
| 1838 | `the middle one by a factor of ten in` → `the middle one by a factor of 10 in` |
| 2137 | `re-scored only for the ten controllers` → `re-scored only for the 10 controllers` |
| 2400 | `that keeps sixteen of eighteen features` → `that keeps 16 of 18 features` |
| 2532 | `not monotone across the thirteen levels` → `not monotone across the 13 levels` |
| 2571 | `fifteen. The apparent advantage` → `15. The apparent advantage` |
| 3101 | `fifteen controllers on four test seasons` → `15 controllers on four test seasons` |
| 3204 | `front holds five of the fifteen controllers` → `front holds five of the 15 controllers` |
| 3255 | `2020--2023}, fifteen controllers ($n=80$…)` → `2020--2023}, 15 controllers ($n=80$…)` (table note) |

**Not changed — correct as they stand:** four sentence-initial numerals (`Fifteen
controllers were compared…`, `Sixteen configurations were drawn…`, `Seventy-two
sparse-identification configurations…`), which MDPI requires to be written out. Numbers
0–9 (`four seasons`, `nine SINDy-MPC variants`, `five of the 15`) are also correct as words.

---

## D. Not changed, deliberately

| Item | Why |
|---|---|
| 118 remaining spaced en dashes | MDPI §5.3 *prefers* em dashes to colons and asks only for sparing use; rewriting 118 sentences in a numerically-verified manuscript is a worse trade than leaving them. See `anti-slop-audit.md`. Author's call. |
| `writing---original draft preparation`, `writing---review and editing` | True em dashes, but this is MDPI's own required CRediT wording. Correct. |
| Every number, `\ref`, `\label`, `\cite` key, equation, table and figure | Out of scope for a language pass. Verified unchanged — see below. |
| The `[[REQUIRED BEFORE SUBMISSION…]]` marker at line 3430 | Deliberately left in place. It is the Data Availability blocker (C-1) and must stay visible until a real DOI replaces it. Filling it in would be fabrication. |
| "pre-registered" wording | Needs an author decision (C-2), not an editor's guess. |
| British `-ise` forms, `labelled`, `metre`, `centre`, `behaviour` | Consistent British English, which MDPI permits. Not errors. |
| Reference entries | Quoted material. All flags are reported in `reference-audit.md` for the author to adjudicate; nothing was auto-corrected. |

---

## E. Integrity verification of the revision

Run after all edits, comparing original `paper_en.tex` with `paper_en_revised.tex`:

| Invariant | Original | Revised | Result |
|---|---|---|---|
| Printed numbers lost or altered | — | — | **NONE** |
| Printed numbers added | 2508 | 2532 | +24, all the word→digit conversions in §C (`10`×4, `11`, `12`, `13`×2, `15`×9, `16`×2, `18`×2, `20`×3) |
| Citation keys | 111 | 111 | identical set |
| `\label` targets | 50 | 50 | identical |
| `\ref` targets | 93 | 93 | identical |
| `table` / `figure` / `equation` environments | 16 / 6 / 3 | 16 / 6 / 3 | identical |
| `tabular` environments | 16 | 16 | identical |
| `\bibitem` entries | 48 | 48 | identical |

Independently, the project's own gate was re-run on the untouched original and reports
**758 table cells and 336 prose values recomputed, 1,953 printed numbers walked, 0
unclaimed, 0 mismatches**, and the rebuilt `.docx` passes all 14 package checks plus 9
pandoc-stage checks.

---

## G. Second pass — plugin skills applied (81 further lines)

Run after the three plugins became loadable. Rules taken from
`academic-prose` §1–§2 and `humanizer` §8/§19.

Changed lines in this pass: `01` 11, `02` 6, `03` 24, `04` 32, `05` 8 — 81 in the
section files, 82 in the assembled file. **Cumulative across both passes: 120 lines.**

### G-1. Paired em-dash-function inserts — all 20 removed (anti-slop)

Pass 1 scanned line by line and found 6. Re-scanning on paragraph-joined text found
**20**: most paired inserts straddle a line break in the wrapped source. Rule applied:
` -- X -- ` becomes `, X, ` when X contains no comma, and ` (X) ` when it does, so the
comma set stays unambiguous. Examples:

| Was | Now |
|---|---|
| `-- the degree-2 candidates are all non-embeddable in the MPC solver --` | `, the degree-2 candidates are all non-embeddable in the MPC solver,` |
| `-- 63rd of 72 on median rollout error, 64th on divergence --` | `(63rd of 72 on median rollout error, 64th on divergence)` |
| `-- 16 of 18 features, and essentially all of the collinearity, unchanged --` | `(16 of 18 features, and essentially all of the collinearity, unchanged)` |
| `-- both computed on the identification data in seconds, before any closed-loop season is simulated --` | `(both computed on the identification data in seconds, before any closed-loop season is simulated)` |
| `-- unlike the full library --` | `, unlike the full library,` |

### G-2. Dash before a coordinating conjunction — 14 removed (anti-slop)

` -- and`, ` -- but`, ` -- so`, ` -- while`, ` -- whereas`, ` -- though`, ` -- although`
become `, and`, `, but`, and so on. A dash carries no work a comma does not do here.

### G-3. Overlong sentence split (language)

`01-introduction.tex`. The manuscript's longest sentence, 105 words, carried a
three-line paired insert. Split at the natural join, preserving order, wording and
every number:

- **was:** `The obvious structural account of why the middle library is the worst -- that it carries enough collinearity … once the direct one is cut -- has been tested and rejected: deleting exactly that one feature …`
- **now:** `The obvious structural account of why the middle library is the worst is that it carries enough collinearity … once the direct one is cut. That account has been tested and rejected: deleting exactly that one feature …`

A second dash in the same sentence, `with survival at $40\,\%$ -- nowhere near the
collapse`, became a comma.

### G-4. Bold used for emphasis in running prose (language)

`04-discussion.tex`: `\textbf{non-monotone in $\kappa$}: the worst-conditioned library…`
→ `non-monotone in $\kappa$: the worst-conditioned library…`. Wording unchanged.
Bold on table header cells and on the run-in labels of the Limitations list was **kept** —
those are structure, not emphasis.

### G-5. Checked by the plugins and found clean — no action

`load-bearing` / `linchpin` / `cornerstone` / `heavy lifting` / `backbone of` (0);
intensifier adverbs `crucially`/`importantly`/`notably`/`strikingly`/`surprisingly` (0);
defensive pre-emption `To be clear` / `This is not to say` / `None of this means` (0);
bare hedges on tested results `exploratory`/`indicative`/`appears to` (0);
`we do not claim` (0 — the skill allows one).

### G-6. Flagged by a plugin, deliberately not changed

| Flag | Why kept |
|---|---|
| `Wins/$n$`, `Wins` | Table **column headers**: a defined statistical quantity (count of paired wins), not a sports metaphor. |
| `worst-conditioned` ×10 | Technical compound paired with `best-conditioned`. Renaming it would break terminology consistency, which is the worse fault. |
| `degrades` ×4, `merely unsearched` ×2 | academic-prose §2b asks that failure language be reserved for actual failures. These describe genuine monotone degradation and a precise scope limit, so they are accurate, not self-sabotage. |
| One research question in the Introduction | §2 bans *stacked* rhetorical questions. A single stated research question is what MDPI asks for. |
| 43 single appositive dashes | Each does real syntactic work; MDPI §5.3 permits them. Reduced from 132 to 51 overall, which is "sparingly". |

### G-7. Skill rule NOT followed, and why

`academic-prose` §3 requires an abstract of **≤160 words**. The abstract is **190 words**.
MDPI *Agronomy* allows "about 200 words maximum". A journal's own limit governs over a
generic style preference, and cutting 30 words would mean dropping a result the abstract
currently reports. **Kept at 190.** Flagged here rather than silently overridden, as the
skill itself requires.

---

## F. Note on `own-article/paper/en/paper_en.tex`

While building the revised copy, `assemble_paper_en.py` was run and it **regenerated
`own-article/paper/en/paper_en.tex` in place** — the script carries a hard-coded output
path that ignores its working directory. Stated plainly rather than glossed over.

Assessed impact: **none.** That file is a generated artefact; the project's own
documentation states *"`paper_en.tex` is assembled by concatenation and is overwritten on
every run. Edit the five section files… never `paper_en.tex`."* It was regenerated **from
the five untouched original section files** — it still contains `fifteen controllers` and
`optimizer`, proving no revision leaked into it — and it passes the full numeric gate
(1,953 numbers, 0 unclaimed, 0 mismatches). The five original section files are byte-for-byte
unmodified.

All subsequent revision work was done by editing a **copy**, not by re-running the assembler.
