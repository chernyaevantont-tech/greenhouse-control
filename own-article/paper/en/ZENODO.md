# Zenodo deposit — what to upload and what to type

One file goes up. Everything below is the metadata form, filled in, ready to copy.

## The file

```
greenhouse-control-regen-data-v1.0.zip
```

At the repository root. 5.99 MB, 630 entries, SHA-256
`89504527cae5c44851a897557b05b6821f1edfcd6ad187ad69dcb31ee6bd070c` (rebuilt 2026-09-16
after the text audit of the archive: `results/final/NUMBERS.md` regenerated from the
manuscript's own checks, `figures/SPEC.md` and the cluster plan taken out, working notes
removed from the script headers).

Nothing else is deposited: not the manuscript (MDPI publishes it), not the cover letter,
not the repository. Rebuild the archive with `python own-article/regen/make_archive.py`;
it is deterministic on any platform, because entries are sorted, timestamps are fixed and
the line endings of text entries are normalised, so an unchanged tree gives a
byte-identical file and the same hash.

## Form fields

**Upload type** — Dataset.
(The archive is result tables plus the code that produced and reads them. "Dataset" is the
honest primary type; the code is described in the abstract. Choosing "Software" instead
would put the emphasis on the scripts and is defensible, but the deposit exists so that the
paper's numbers can be checked.)

**Title**

```
Regeneration data and analysis scripts for "Multi-step stability selects sparse surrogate
models for economic greenhouse climate control: an in silico study of feature-library
design and actuator-pathway survival"
```

**Authors** — the manuscript's nine, in the manuscript's order, with ORCID where it exists.
Affiliation for all nine: `Don State Technical University`.

| # | Name | ORCID |
|---|------|-------|
| 1 | Naumov, Ivan I. | 0000-0002-8582-3203 |
| 2 | Lyashov, Maksim V. | 0009-0004-9754-3390 |
| 3 | Chernyaev, Anton T. | 0009-0001-6836-6522 |
| 4 | Kilina, Mariya S. | — |
| 5 | Zhdanova, Marina M. | 0000-0003-1119-5221 |
| 6 | Chernyaeva, Elena O. | 0009-0003-3829-3486 |
| 7 | Kharina, Marina S. | — |
| 8 | Merzlikina, Angelina E. | 0009-0000-5051-346X |
| 9 | Kulinich, Mariya N. | — |

**Description** (paste as is)

```
Replication package for a simulation study of model selection for economic model predictive
control of a greenhouse climate.

The archive contains one row per (controller, seed, test season) for every experiment the
manuscript reports: the 10-controller x 4-season x 20-seed main grid, the 13-point sparsity
sweep with single-coefficient knock-out and knock-in, the 72-configuration identification
ladder, the oracle horizon sweep and action replay, online adaptation, the out-of-distribution
guard, fault injection, design sensitivity, the bootstrap-draw axis, and the later waves
re-scored under the price-aligned objective: 21 waves in all. Alongside them are the driver
that produced them, the acceptance gates, the table generator, the analysis of the 17-feature
falsification probe, and the figure scripts that draw the manuscript's figures from these
files. EXPERIMENT_PROTOCOL.md carries the study's plan in English translation, including
the gates declared for the identification ladder, against which the manuscript reports
what was applied.

Not every wave used the same objective, and the archive records which used which.
priced_main, priced_mech and priced_dagger were scored under the price-aligned weights. The
adaptation, guard, fault-injection and design blocks were produced on the default weights:
regen/experiments_support.py hard-coded the objective and silently ignored the driver's
--objective flag, and its header records the consequence. figures/_plotstyle.py marks the
priced_design directory as misnamed for the same reason.

Every wave was produced under a single frozen configuration whose hash, 637c6b535a9e, is
written into every result row and into each wave's regen_manifest.json together with the git
commit. results/final/NUMBERS.md lists every quantity the manuscript states, with the value
recomputed from this tree and the files it is computed from.

The study is computational: the controlled object is the GreenLight tomato greenhouse model
as packaged in gl_gym 0.3.1, driven by ERA5-derived weather retrieved from the Open-Meteo
historical archive for Rostov-on-Don. No greenhouse sensor records, plant measurements or
harvested-yield observations were collected.

The waves were produced in two computing environments, a Linux container on a compute
cluster (python:3.11-slim) for the canonical default-objective blocks and a workstation
(Python 3.14) for every later wave; the image field of every result row records
which, and requirements-cluster.txt at the archive root carries the package versions common
to both. Bit-level reproduction is established within one computing environment; no wave was
re-executed in the other and no manifest records an environment fingerprint, so
cross-environment agreement of any single wave is unmeasured. README.txt in the archive
states the limits, the acceptance-gate failures the tree ships with and why they are
expected, and which two files are superseded by later waves.

Funding: this research was funded by the Ministry of Science and Higher Education of the
Russian Federation under the agreement on the provision of a grant from the federal budget
in the form of a subsidy for state support of the development programmes of world-class
research centres performing research in priority areas of scientific and technological
development, agreement no. 075-15-2025-592 of 24 June 2025.

The archive is released under CC BY 4.0; LICENSE.txt at its root carries the terms and the
attribution to use.
```

**License** — Creative Commons Attribution 4.0 International (CC-BY-4.0).
This is the usual choice for a replication package that accompanies a paper, and it is what
MDPI's data policy expects. Zenodo allows one licence per record, and the same one now
applies inside the archive: `LICENSE.txt` at its root states CC BY 4.0 over the tables, the
scripts, the protocol and the documentation, gives the attribution to use, and records that
no third-party code or data is redistributed here — gl_gym and the GreenLight model are
imported rather than shipped, and the ERA5 weather is fetched from Open-Meteo by
`make_weather.py` rather than included, so both keep their own terms.
Splitting the deposit — CC BY for the tables and MIT for the scripts — is the alternative if
a software licence is wanted on the code; it needs a second licence statement inside the
archive, because the record itself can carry only one.

**Version** — `1.0`

**Language** — English

**Keywords**

```
greenhouse climate control; protected tomato production; economic model predictive control;
sparse identification of nonlinear dynamics; SINDy; simulation-based evaluation;
control-oriented model selection; multi-step prediction error; reproducibility; GreenLight
```

**Related identifiers** — after the paper is accepted, add its DOI as
`is supplement to`. Before then leave empty; the record can be edited afterwards without
minting a new DOI.

**Grant / funding** — Ministry of Science and Higher Education of the Russian Federation,
agreement no. 075-15-2025-592 of 24 June 2025 (World-Class Research Centre programme).

Checked against Zenodo's registry on 2026-09-09. The agreement number is **not** there: a
search for `075-15-2025-592` returns unrelated awards. The ministry appears only under its
former name, "The Ministry of Education and Science of the Russian Federation"
(ROR `00ghqgy32`), the body that was split in 2018.

The funding statement is therefore carried in the **Description**, where it is exact and
under your control, and it matches the manuscript's Funding statement word for word.
Attaching the ROR entry as well is defensible, since it is the same ministry lineage, but it
would display a name that is not the funder's current one; leaving the funder field empty
loses nothing, because the description already says it.

## Order of operations

1. Upload the file, fill the form, press **Reserve DOI** — Zenodo issues the DOI before
   publication, so the manuscript can carry it at submission.
2. Put the reserved DOI into `own-article/paper/en/authors.json`:

   ```json
   "data_location": "The regeneration tree, the analysis scripts and the derived tables are archived at Zenodo, https://doi.org/10.5281/zenodo.XXXXXXX (accessed on DD Month YYYY)."
   ```

3. Rebuild and check that no placeholder is left:

   ```bash
   cd own-article/paper/en && python assemble_paper_en.py && python make_docx.py && python format_mdpi_docx.py && python ../../../.codex-tmp/mdpi-format/audit_mdpi.py
   ```

   The audit ends in `AUDIT_OK` and should now print `explicit_placeholders=0`.

4. **Publish the Zenodo record before submitting**, or at the latest on the same day. A
   reserved DOI does not resolve until the record is published, and a Data Availability
   Statement whose link 404s is worse than one that names a restriction.

Zenodo mints two DOIs: a version DOI (this deposit) and a concept DOI (all versions). Cite
the **version** DOI in the manuscript — it is the one that points at the exact files the
numbers came from.
