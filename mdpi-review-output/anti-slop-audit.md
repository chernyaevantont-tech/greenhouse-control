# Anti-slop audit

Scope: the five section files and the assembled `paper_en.tex`, LaTeX comments stripped
(the comment blocks carry provenance notes, not manuscript prose). 30,889 words, 513
prose sentences.

## Headline: this manuscript is already unusually clean

Every pattern below was searched for across the whole manuscript. **Fourteen of the
brief's categories returned zero hits.**

| Pattern from the brief | Hits | Note |
|---|---|---|
| True em dash `---` as a syntactic connective | **0** | The 2 occurrences of `---` are `writing---original draft` and `writing---review and editing` in Author Contributions, which is MDPI's own required CRediT wording. Correct; left alone. |
| Metadiscourse ("It is important to note", "Notably", "Importantly", "Crucially") | **0** | |
| Vague attribution ("studies show", "research suggests", "it has been shown") | **0** | |
| Promotional words (`novel`, `groundbreaking`, `remarkable`, `pivotal`, `comprehensive`, `state-of-the-art`, `seminal`, `compelling`, `unprecedented`) | **0** | |
| `crucial` / `vital` / `essential` / `paramount` | **0** | |
| "To the best of our knowledge" | **0** | |
| Colloquial contractions (`don't`, `can't`, `it's`…) | **0** | |
| Hedge stacking ("may potentially", "could possibly") | **0** | |
| `delve`, `tapestry`, `landscape of`, `testament to`, `intricate`, `interplay`, `underscore`, `foster` | **0** | |
| Significance-instead-of-result ("highlights the importance", "paves the way", "sheds light on") | **0** | |
| "not only X but also Y" | **0** | |
| Emoji / bold-label bullets | **0** | |
| Rhetorical `from X to Y` | **0** | 8 matches, all genuine numeric transitions ("from 71 to 26 steps"). No action. |
| `key` as an empty adjective ("key role", "key finding") | **0** | |

Two near-misses, both legitimate and left alone:

- **`robust` ×2** — one is "robustness analyses of that formulation", a technical term of
  art; the other is a table section header "Benchmarking safeguards, mechanism and
  robustness". Neither is the vacuous booster the brief targets.
- **"not X but Y" ×2** — `"not a ranking but a check"` and one clause where "but" is an
  ordinary conjunction. Neither is the rhetorical antithesis pattern.

## What was actually found and fixed

### 1. Spaced en dash as the universal clause connector — the one real AI-tell

The manuscript uses no em dashes, but it uses **` -- ` (spaced en dash) 132 times** as its
parenthetical/appositive connector. Functionally this is the em dash the brief targets,
just rendered in the British spaced-en-dash convention.

Density before: Discussion 45, Results 36, Introduction 12, Methods 12, Conclusions 8.

**The strongest form of the tell is the paired insert** — ` -- X -- ` interrupting a
sentence twice. There were **6**, and all 6 were revised (see `change-log.md` A-1…A-6).
Commas were used for short non-restrictive appositives, parentheses where the insert
already contained commas or preceded a contrastive clause.

| Metric | Original | After pass 1 | After pass 2 (plugins) |
|---|---|---|---|
| Paired ` -- X -- ` inserts | 20 | 14 | **0** |
| Total ` -- ` clause connectors | 132 | 118 | **51** |
| Dash immediately before a conjunction | 14 | 14 | **0** |

Pass 1 found only 6 paired inserts because it scanned line by line, and most paired
inserts straddle a line break in the wrapped LaTeX source. Re-scanning on
paragraph-joined text found **20**. All 20 are now gone.

### 2. Sentence rhythm — no mechanical uniformity

Checked because the brief asks for it, and no artificial variation was introduced.

- 513 sentences, mean **29.8 words**, range **4 to 105**. The spread is wide and driven by
  content, not by a rhythm template.
- Sentence openers: `The` 32.6%, then `A` 2.7%, `What` 2.5%, `It` 2.3%, `This` 2.3%. A
  ~33% "The" rate is normal for quantitative English prose and does not read mechanically.
- No triple-sentence drama, no repeated paragraph-closing formula, no rule-of-three lists
  padded to three items.

One item worth the author's eye: the **105-word sentence** is long enough to cost a reader
a re-read. Not changed, because splitting it risks the argument. **[AUTHOR CHECK: consider
splitting the longest sentence in the Discussion.]**

### 3. Not changed, and why — a direct conflict with MDPI house style

The brief asks for "zero em dashes in ordinary manuscript text". **MDPI's own Layout Style
Guide (§5.3) says the opposite:**

> "For MDPI papers, **em dashes are preferred to colons** when introducing phrases that
> provide clarification or definitions… We recommend using em dashes **sparingly** to avoid
> disrupting the flow of sentences."

So MDPI permits and even prefers the construction, asking only that it be used sparingly.
The 118 remaining connectors were therefore **left in place** rather than driven to zero,
for three reasons:

1. Rewriting 118 sentences in a manuscript whose every printed number is machine-verified
   carries real risk of introducing an error, for a change the journal does not want.
2. The brief itself forbids mechanical replacement by hyphen, and each remaining site
   needs an individual judgement about whether a comma, colon, or full stop reads better.
3. At 118 across 30,889 words the density is roughly one per 260 words — closer to
   "sparingly" than to the once-per-sentence tic that reads as machine-written.

**This is the author's call, and it is a real disagreement, not an oversight.** If you want
the count driven further down, the highest-value target is the Discussion (45 → the
densest section). Every remaining site can be listed with line numbers on request.

## Language and MDPI-style findings (fixed)

### British/American consistency — was genuinely mixed

MDPI §4.3 allows either variant but requires consistency. The manuscript is uniformly
British (`labelled`, `metre`, `behaviour`, `favour`, `centre`, `analyse`, `-ise`
throughout — 60 `-ise/-isation` forms, 0 US `-ize` forms) **except for one stem**:

| Form | Original | Revised |
|---|---|---|
| `optimizer` / `optimizers` (US) | 15 | **0** |
| `optimiser` / `optimisers` (GB) | 6 | 21 |

The same word appeared both ways in running prose, sometimes on adjacent lines. Normalised
to British to match the rest.

Two false alarms discarded: `center` ×22 is the LaTeX `\centering` command, not prose; and
"continuous optimization" is inside a cited reference title, which must not be altered.

### Numerals — MDPI §6.1

"Numbers 0–9 should be written as words unless they are a measurement" — implying 10 and
above take digits, except at the start of a sentence where MDPI requires them written out.

24 mid-sentence numerals ≥10 were spelled out (`fifteen controllers`, `twenty seeds`,
`eleven distinct values`, `sixteen of eighteen features`, `a factor of ten`…) and were
converted to digits.

| Counted in prose only (LaTeX comments excluded) | Original | Revised |
|---|---|---|
| Numerals ≥10 spelled out, total | 27 | **3** |
| …of which mid-sentence (an MDPI §6.1 violation) | 24 | **0** |
| …of which sentence-initial (**correct as words**) | 3 | 3 |

The three survivors are `Fifteen controllers were compared…` (`02-methods.tex:124`),
`Sixteen configurations were drawn…` (`02-methods.tex:320`) and `Fifteen controllers were
compared on the test seasons…` (`03-results.tex:245`), plus `Seventy-two
sparse-identification configurations…` opening a sentence in the abstract. MDPI requires a
sentence-initial number to be written out, so all four are **correct and were left alone**.

A further 15 `optimizer` and 19 numeral occurrences remain inside `%%` provenance comment
blocks. These are CSV column names and source-file notes, not manuscript prose; they are
stripped before the `.docx` is built and were deliberately not touched.

## Verification that the anti-slop pass changed nothing substantive

| Invariant | Original | Revised |
|---|---|---|
| Printed numbers lost or altered | — | **none** |
| Citation keys | 111 | 111 (identical set) |
| `\label` targets | 50 | 50 (identical) |
| `\ref` targets | 93 | 93 (identical) |
| Table / figure / equation environments | 16 / 6 / 3 | 16 / 6 / 3 |
| `\bibitem` entries | 48 | 48 |

The only numeric additions are the 24 word-to-digit conversions, all ≥10, enumerated in
`change-log.md`.
