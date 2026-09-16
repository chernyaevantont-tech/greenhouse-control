Greenhouse climate control -- regeneration data and analysis scripts
====================================================================

Companion archive for the manuscript submitted to MDPI *Agronomy*:

  "Multi-step stability selects sparse surrogate models for economic greenhouse
   climate control: an in silico study of feature-library design and
   actuator-pathway survival"

Every quantity the manuscript states is computed from the per-run tables in this
archive. regen/results/final/NUMBERS.md lists each of them -- 800 table cells and
410 values in the running text -- with the value recomputed from this tree and
the files it is computed from.

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
  LICENSE.txt                the terms this archive is released under: CC BY 4.0,
                             the same licence the Zenodo record carries
  EXPERIMENT_PROTOCOL.md     the experiment protocol, in English translation: the
                             plan the study was run to, including which gates were
                             declared for the identification ladder and the status
                             notes recording what became of each hypothesis
  requirements-cluster.txt   the pinned package versions of the compute stack; the
                             same pins in both environments described below
  article_experiment_utils.py  the compute API: identification, MPC construction,
                             rollouts, economic scoring
  protocol_config.py         the protocol dataclasses regen_config builds on
  rostov_soil.py             the continental soil boundary condition for this site
  make_weather.py            reconstructs the ERA5-derived weather CSVs
  e3_dagger_compare.py       the dagger/dense counter-experiment, imported by the driver
  run_knockout_ablation.py   the single-coefficient knock-out/knock-in ablation, also
                             imported by the driver
  figures/                   the figure layer: _plotstyle.py, which owns the dedup
                             key and the solver-abort rule -- how a CSV becomes a
                             number in the paper -- plus the six make_figN.py that
                             draw Figures 1-5 and the graphical abstract (sources
                             below)
  regen/*.py                 the driver, the experiment blocks, and the analysis
  regen/README.md            what this package is, which manuscript it belongs to,
                             how to run it, and which result tree the paper reads
  regen/INSTRUCTIONS.md      runbook for recomputing the two draw-axis waves
  regen/recipe_frozen_v2.json  the frozen identification recipe
  regen/results/             one row per (controller, seed, test season), by wave
  regen/results/final/       the tree the paper reads: merged blocks, derived
                             tables (with tables/SUMMARY.md, the summary of this
                             default-objective tree), NUMBERS.md (the manuscript's
                             claim map) and VERIFY.txt (the recorded gate output)
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
  python make_tables.py --out <dir> derived tables + tables/SUMMARY.md
  python verify_regen.py --out <dir>  acceptance gates
  python analyze_notuboil.py        the 17-feature library probe: paired Wilcoxon
                                    with Holm correction, exact McNemar on survival
  python ../figures/make_fig2.py    redraws a manuscript figure from the CSVs; each
                                    script ends in a self-check that fails the build
                                    if a caption claim stops holding

Everything above runs from the extracted archive, with no reference back to the
project repository. The three analysis entry points need only numpy, pandas and
scipy; the figure scripts add matplotlib; run_regen.py needs the full simulation
stack below. NUMBERS.md itself is regenerated from the project repository, where
the manuscript source lives, by the checks that compare every printed value with
this tree; the archive carries their result.


Figures, and the files they are drawn from
------------------------------------------
All paths relative to regen/results/. Every script ends in a self-check that
recomputes each drawn quantity from the CSVs along a second code path.

  Figure 1  make_fig1.py   (a),(b) ladder_rerun/ladder_rerun*.csv, degree 1, no
                           denoising, STLSQ and ensemble; (c),(d) priced_main/*.csv,
                           priced_dagger/*.csv, phys_lib/main_physlib.csv,
                           notuboil/main_notuboil*.csv (per-seed xi_uboil)
  Figure 2  make_fig2.py   priced_main/*.csv, priced_dagger/*.csv,
                           phys_lib/main_physlib.csv (SINDy-MPC, NN-MPC, priced);
                           final/main.csv (PPO, SAC, planner, stock heuristic);
                           n2_tune/tune_rb_n2.csv (tuned heuristic)
  Figure 3  make_fig3.py   priced_mech/mechanism_pricedMech*.csv and
                           final/mechanism.csv (lambda sweep and knock blocks,
                           season 2020); survival strip from the priced pool
  Figure 4  make_fig4.py   (a) priced_design/design_pricedDesign*.csv (default
                           objective, see the caption); (b) final/main.csv
                           re-scored over the price grid, cross-checked against
                           final/tables/sensitivity_prices.csv
  Figure 5  make_fig5.py   n2_tune/tune_rb_n2.csv, final/main.csv, n7/main_n7.csv,
                           priced_main/*.csv
  Graphical abstract  make_fig6.py   (a) as Figure 1a; (b) priced pool, phys_lib
                           and notuboil; (c) as Figure 2


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
Pinned stack (requirements-cluster.txt at the archive root): numpy 1.26.4,
scipy 1.17.1, pandas 2.3.3, scikit-learn 1.8.0, pysindy 2.1.0, casadi 3.7.2 with
its bundled IPOPT, do-mpc 5.1.1, gl_gym 0.3.1, gymnasium 1.2.3, torch 2.11.0,
stable-baselines3 2.9.0. Install order matters: gl_gym requires numpy<2.0 while
the pysindy 2.1.0 wheel declares numpy>=2.0 (it works on 1.26.4).

Two computing environments produced the waves, and the `image` column of every
result row records which: the canonical default-objective blocks (final/main.csv,
mechanism*.csv, faults.csv, design*.csv, parity.csv, ladder*.csv and, as v4,
draws.csv) ran on a compute cluster in a Linux container built from
python:3.11-slim (image "greenhouse-regen:v1"); every other file, including
final/adapt.csv, final/guard.csv and all later waves, ran on a workstation
under Python 3.14 (image "local").

Bit-level reproduction is established WITHIN ONE COMPUTING ENVIRONMENT. No wave
was re-executed in the other environment, and no manifest records an environment
fingerprint -- the env block is absent from all 21 manifests and tables/SUMMARY.md
prints env_hash: n/a -- so cross-environment agreement of any single wave is unmeasured,
not established. The size of the platform effect on a deterministic controller is
visible in the tree: the stock heuristic scores -1.2061 EUR/m2 in final/main.csv
(container) and -1.2264 in n2_tune/tune_rb_n2.csv (workstation) at identical
configuration hash. Closed-loop margins should not be expected to match to the
last decimal on a different stack.

PPO/SAC determinism was measured on 2026-09-02 on that stack: repro.py --selftest
--rl returns nine identical digests across two runs, the policy weights included.
It trains at the self-test's fast-mode budget, not at the 200 000 steps the
reported RL controllers received, so the seeding is shown to be effective rather
than a full training run shown to be bit-identical.

The manuscript's own weather methodology is described in its Section 2.1; the
generator here reconstructs it and is checked by regenerating a year that ships
with gl_gym (`python make_weather.py --check 2020`).
