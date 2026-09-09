# Revised copies for the Zenodo deposit

Two documents from the deposit, with their em-dash clause connectors reduced. The
originals in `own-article/` are untouched.

| File here | Replaces |
|---|---|
| `figures/SPEC.md` | `own-article/paper/en/figures/SPEC.md` |
| `regen/README.md` | `own-article/regen/README.md` |

## What changed

Punctuation, and nothing else.

| | SPEC.md | regen/README.md |
|---|---|---|
| Em dashes before | 42 | 14 |
| Em dashes after | **17** | **5** |
| Prose clause connectors removed | 25 | 9 |

The 22 that remain are the typographic ones, which were never the problem: 9 in table
cells, 7 heading separators (`## Figure 1 — Selection reversal…`), 6 list-item labels.
Prose clause connectors are now **zero** in both files.

Dashes became a comma, a colon, a semicolon or a pair of parentheses depending on what the
sentence was doing. Two paired inserts that straddled line breaks were converted to
parentheses: the fifteen-controller list in `regen/README.md`, and the `stock_test` /
`tuned_test` pair in `SPEC.md`.

## Proof that only punctuation moved

Strip every non-alphanumeric character from each file and compare:

```
SPEC.md   : alphanumeric stream identical  True
README.md : alphanumeric stream identical  True
```

Not one letter or digit moved. Alongside that:

- code spans 179 → 179 and 107 → 107, no losses, no additions
- numbers 427 → 427 and 67 → 67, identical multisets
- file paths 44 → 44 and 29 → 29, identical
- headings, table rows, blockquote lines, list items and fenced blocks all unchanged
- `**`, backticks and parentheses all balanced

One repair worth naming: the mechanical pass first joined three lines of a blockquote and
swallowed their `> ` prefixes. That was caught on review and rewritten by hand; the
blockquote and its wording are intact.

## How to use them

```bash
cp mdpi-review-output/archive-revised/figures/SPEC.md   own-article/paper/en/figures/SPEC.md
cp mdpi-review-output/archive-revised/regen/README.md   own-article/regen/README.md
python own-article/regen/make_archive.py
```

You are rebuilding the archive anyway to add `EXPERIMENT_PROTOCOL.md` (required by C-2 —
the preregistration pointer would otherwise link to a package that does not contain the
plan). Do both in one rebuild.

**Then update the SHA-256 in `ZENODO.md`.** It currently reads
`b767d3615b1ad703397a6e51e1cba172c4bbf9738ab0970498582d50b28dc94b`, and any change to the
archive changes it. The hash appears only in `ZENODO.md`, not in the manuscript, so nothing
else needs touching.

## Not changed, deliberately

`README.txt` at the archive root already had **zero** em dashes and needed nothing.

The description block in `ZENODO.md` still says "the later waves run under the priced
objective". That is a factual matter rather than a style one, it is wrong for four of the
blocks, and the suggested replacement wording is in `../zenodo-archive-audit.md`.
