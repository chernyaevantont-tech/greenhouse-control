# Zenodo deposit — AI-writing audit

Scanned `greenhouse-control-regen-data-v1.0.zip` (625 entries) on 2026-09-07, plus
`ZENODO.md`, which is not in the archive but supplies the text of the landing page.

Pattern set: the union of the `academic-prose` ban list, the `humanizer` catalogue
(Wikipedia "Signs of AI writing") and the brief's own list — 26 patterns over two corpora,
public prose (8 `.md`/`.txt` files) and code prose (docstrings and `#` comments in 22
`.py` files, identifiers excluded so they cannot trip the patterns).

## Verdict: clean

**Every high-severity pattern returned zero hits, in both corpora.**

| Pattern | Public | Code |
|---|---|---|
| not X but Y · it's not X it's Y | 0 | 0 |
| staged run-up ("let's dive in", "here's what you need to know") | 0 | 0 |
| arguing with no one ("to be clear", "this is not to say") | 0 | 0 |
| one-line closers ("that's the real win") | 0 | 0 |
| sayings that sound deep ("at its core", "what really matters") | 0 | 0 |
| stock AI words (delve, tapestry, intricate, interplay, seamless, leverage…) | 0 | 1 |
| inflated significance ("paves the way", "underscores the importance") | 0 | 0 |
| vague attribution ("studies show", "experts say") | 0 | 0 |
| chatbot residue ("I hope this helps", "great question") | 0 | 0 |
| knowledge-cutoff disclaimers | 0 | 0 |
| emoji · arrow decoration · bold-label lists as decoration | 0 | 0 |
| stacked qualifiers ("may potentially") | 0 | 0 |
| LLM-tell metaphors (load-bearing, linchpin, cornerstone) | 0 | 0 |

The three code hits are false positives on inspection: `robustly` in "extract a Python
scalar **robustly** (int(array) errors on some builds)" is ordinary engineering usage, and
the two instances of `novelty` are the technical term in "Mahalanobis (input **novelty**)",
the standard name for that OOD signal.

**`README.txt`, the file a visitor opens first, is clean on every pattern including em
dashes (zero, against 878 words).** It is also the opposite of generated prose in
substance: it states that the acceptance gate exits 1 and why, names the two superseded
files, and writes "the seeding is shown to be effective rather than a full training run
shown to be bit-identical" instead of claiming reproducibility flatly.

## The one real signal: em-dash density in `SPEC.md`

66 em dashes across the markdown. Classified:

| Use | Count | Judgement |
|---|---|---|
| Prose clause connector | 34 | the actual tell |
| Blockquote note | 7 | same |
| Table cell | 10 | typographic, fine |
| Heading separator (`# Figure 1 — Selection reversal…`) | 9 | typographic, fine |
| List-item label | 6 | typographic, fine |

So **41 of 66 are prose connectors**, and they concentrate in one file:

| File | Em dashes | Words | Density |
|---|---|---|---|
| `figures/SPEC.md` | 42 | 3377 | 1 per 80 |
| `regen/README.md` | 14 | 1849 | 1 per 132 |
| `regen/INSTRUCTIONS.md` | 8 | 806 | 1 per 101 |
| `README.txt` | **0** | 878 | — |
| everything else | 2 | — | — |

One per 80 words is dense enough to read as a habit. Against that: `SPEC.md` is an internal
figure specification whose content is relentlessly specific ("agreement to
3.6 × 10⁻¹⁵", "falsified 2026-08-18", "60 rows, n = 20"), which is exactly the concrete
detail the humanizer skill says to keep. **This is house punctuation, not slop** — the same
habit the manuscript showed as ` -- `.

> **Reduced on request.** Revised copies of both files are in
> `mdpi-review-output/archive-revised/`, with drop-in instructions in its own `README.md`.
> Prose clause connectors: **33 → 0**. Em dashes: SPEC.md 42 → 17, regen/README.md 14 → 5;
> the 22 that remain are table cells, heading separators and list labels.
> Verified punctuation-only: strip every non-alphanumeric character from each file and the
> before/after streams are **byte-identical**, with code spans, numbers, file paths and
> markdown structure unchanged. The originals in `own-article/` were not touched.

The 24 `- **Field**: value` list items in `SPEC.md` are a specification's field labels, not
decoration, so the humanizer §19 rule does not bite.

## Beyond slop: one substantive item to fix before depositing

`ZENODO.md`'s **Description** block — the text that becomes the landing page — ends its
inventory with:

> "…design sensitivity, the bootstrap-draw axis, and **the later waves run under the priced
> objective** — 21 waves in all."

The driver contradicts this for four of those blocks. `regen/experiments_support.py`,
lines 21–29:

> "WARNING (2026-08-13). The blocks below hard-coded `objective="full"` and therefore
> SILENTLY ignored the driver's `--objective` flag… **Consequence: the
> adapt/guard/faults/design results in this tree were produced on the HARD-CODED weights.**"

`exp_main`, `exp_mechanism` and `exp_parity` live in `run_regen.py` and read `R._OBJECTIVE`
correctly, so `priced_main`, `priced_mech` and `priced_dagger` are genuinely priced and the
manuscript's headline comparison is unaffected. But **adapt, guard, faults and design are
not**, and the description sweeps them into "the later waves run under the priced objective".

This is the same mislabel that was just corrected in the manuscript's Table 16.

**To its credit the archive is honest about it** — the warning ships inside
`experiments_support.py`, `figures/_plotstyle.py` documents `priced_design` as
"MISLABELLED DIRECTORY… Never caption them as priced", and `SPEC.md` names "the mislabelled
`priced_design` directory". And `README.txt`, `regen/README.md` and `regen/INSTRUCTIONS.md`
make **no priced claim at all**. Only the landing-page description does.

> **Applied 2026-09-07.** `ZENODO.md`'s Description block now carries the corrected text
> below. `own-article/paper/en/ZENODO.md` is **not tracked in git**, so the original was
> copied to `mdpi-review-output/originals-backup/ZENODO.md.orig` first; that backup is the
> only copy of the previous wording.
>
> The final wording names the directories rather than the experiments, because
> "re-identification" is ambiguous here: `priced_dagger` holds the two dagger controllers of
> the **main grid**, built through `run_regen.py` and genuinely priced, while the dagger
> rollouts inside `_adapt_rollouts` belong to the **adaptation** block, which is not. Naming
> `priced_main`, `priced_mech` and `priced_dagger` leaves nothing to interpret.
>
> The pasted Description block now contains **zero em dashes**. The one that remains in the
> file is the `**License** — CC-BY-4.0` field separator, which is outside the block and
> matches the other form fields.

**Suggested wording**, which keeps the count and drops the false attribution:

> "…design sensitivity, the bootstrap-draw axis, and the later re-scored waves — 21 waves in
> all. The main, mechanism and re-identification waves were scored under the price-aligned
> objective; the adaptation, guard, fault-injection and design blocks were produced on the
> default weights, as `regen/experiments_support.py` records."

Two directory names, `priced_design` and `design_priced_real`, also assert in public what
the code disproves. Renaming them would break every path recorded in the manifests and in
`NUMBERS.md`, so the better fix is the one already taken inside the archive: leave the names
and keep the disclosure loud.

## Not checked

- The 612 CSV/JSON files were not scanned for prose; they carry data, not writing.
- `EXPERIMENT_PROTOCOL.md` is **not in this archive** and so was not part of this audit. It
  is in Russian and will need its own pass if you add it (which C-2 requires).
- Whether the deposit should be typed Dataset or Software; `ZENODO.md` already reasons about
  that and settles on Dataset, which reads correctly.
