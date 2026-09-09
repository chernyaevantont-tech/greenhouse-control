Greenhouse climate control -- regeneration data and analysis scripts
====================================================================

Companion archive for the manuscript submitted to MDPI *Agronomy*:

  "Multi-step stability selects sparse surrogate models for economic greenhouse
   climate control: an in silico study of feature-library design and
   actuator-pathway survival"

Every quantity the manuscript states is computed from the per-run tables in this
archive. The map from claim to file and column is regen/results/final/NUMBERS.md.

This is a simulation study. No greenhouse sensor records, plant measurements,
harvested-yield observations or actuator trials were collected; the controlled
object is the GreenLight tomato greenhouse model as packaged in gl_gym 0.3.1,
driven by ERA5-derived weather from the Open-Meteo historical archive.


One configuration, one lineage
------------------------------
Every wave here was produced under a single frozen configuration whose hash,
637c6b535a9e, is written into every result row and into the regen_manifest.json
of each of the 21 wave directories, alongside the git commit that produced it.
The manifest also records the seeds, test years, horizon, solver-failure budget,
season length and the four identification recipes, so a wave can be identified
without reference to any text.

  python -c "import regen_config; print(regen_config.config_hash())"   -> 637c6b535a9e


Contents
--------
  article_experiment_utils.py  the compute API: identification, MPC construction,
                             rollouts, economic scoring
  protocol_config.py         the protocol dataclasses regen_config builds on
  rostov_soil.py             the continental soil boundary condition for this site
  make_weather.py            reconstructs the ERA5-derived weather CSVs
  figures/                   the figure layer: _plotstyle.py, which owns the dedup
                             key and the solver-abort rule -- how a CSV becomes a
                             number in the paper -- plus the six make_figN.py that
                             draw Figures 1-5 and the graphical abstract, and SPEC.md
  regen/*.py                 the driver, the experiment blocks, and the analysis
  regen/README.md            what this package is, which manuscript it belongs to,
                             how to run it, and which result tree the paper reads
  regen/INSTRUCTIONS.md      runbook for recomputing the two draw-axis waves
  regen/recipe_frozen_v2.json  the frozen identification recipe
  regen/results/             one row per (controller, seed, test season), by wave
  regen/results/final/       the tree the paper reads: merged blocks, derived
                             tables, NUMBERS.md, VERIFY.txt
  regen/results_pull/raw/    the cluster's own output; see "The two result trees"
                             in regen/README.md before using it

Two files in results/final/ are superseded by later waves and are kept as part of
the record: adapt.csv/guard.csv exist there in the correct draw-axis form, but the
single-draw versions survive in results_pull/raw/, and ladder.csv predates a
rollout-horizon correction -- the manuscript's ladder numbers come from
results/ladder_rerun/. Both cases are explained in regen/README.md.

Run logs (log_*.txt), the Kubernetes manifests and the cluster submission script
are not included: they are infrastructure for one cluster and duplicate what the
CSVs already record. regen/make_archive.py declares exactly what this archive
contains and rebuilds it.


Entry points
------------
  python repro.py --selftest        determinism gate: runs the pipeline twice and
                                    compares SHA-256 digests of the training data,
                                    the coefficient matrices, the network weights
                                    and the closed-loop trajectory and margin
  python run_regen.py --experiment <block> --seeds 0-19 --out <dir>
                                    one of: main, mechanism, parity, ladder,
                                    adapt, guard, faults, design
  python run_regen.py --merge --out <dir>
  python make_tables.py --out <dir> derived tables + NUMBERS.md
  python verify_regen.py --out <dir>  acceptance gates
  python analyze_notuboil.py        the 17-feature library probe: paired Wilcoxon
                                    with Holm correction, exact McNemar on survival
  python ../figures/make_fig2.py    redraws a manuscript figure from the CSVs; each
                                    script ends in a self-check that fails the build
                                    if a caption claim stops holding

Everything above runs from the extracted archive, with no reference back to the
project repository. The three analysis entry points need only numpy, pandas and
scipy; the figure scripts add matplotlib; run_regen.py needs the full simulation
stack below.


What the acceptance gates say about this tree
---------------------------------------------
verify_regen.py --out results/final exits 1. That is the recorded state, not a
surprise: results/final/VERIFY.txt is the same output. The two blocking failures
are oracle_mpc solver aborts (20 in the main grid, all of season 2022; 10 in the
horizon sweep), and the manuscript reports that missing season as a budget
artefact rather than as infeasibility -- raising the cap completes it. The three
warnings are disclosed the same way: the rule-based reference is deterministic,
so tests against it are one-sample; the per-year ranking is not stable; and the
monotonicity claim was replaced by the knock-in result. The gates stay blocking
on purpose -- these numbers may be published with those statements, not without.


Environment, and the limit of the reproducibility claim
-------------------------------------------------------
Pinned stack: Python 3.14.2, numpy 1.26.4, pysindy 2.1.0, casadi 3.7.2,
do-mpc 5.1.1, gl_gym 0.3.1, torch. Install order matters: gl_gym requires
numpy<2.0 while the pysindy 2.1.0 wheel declares numpy>=2.0 (it works on 1.26.4).

Bit-level reproduction is established WITHIN ONE COMPUTING ENVIRONMENT. No wave
records an environment fingerprint -- the env block is absent from all 21
manifests and NUMBERS.md prints env_hash: n/a -- so cross-environment agreement
is unmeasured, not established. Closed-loop margins should not be expected to
match to the last decimal on a different stack.

PPO/SAC determinism was measured on 2026-09-02 on that stack: repro.py --selftest
--rl returns nine identical digests across two runs, the policy weights included.
It trains at the self-test's fast-mode budget, not at the 200 000 steps the
reported RL controllers received, so the seeding is shown to be effective rather
than a full training run shown to be bit-identical.

The manuscript's own weather methodology is described in its Section 2.1; the
generator here reconstructs it and is checked by regenerating a year that ships
with gl_gym (`python make_weather.py --check 2020`).
