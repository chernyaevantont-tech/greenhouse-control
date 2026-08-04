# regen-v2 — full regeneration of the article's experiments

One config, one driver, one output tree, one lineage. Nothing in `own-article/results_scenarios/`,
`results_e0_e3_final/` or `cluster/results_pull/` is read or reused: this regenerates from
data collection upward so that every number in the paper traces to one `config_hash`.

Built and smoke-tested 2026-08-03 against the validated stack in
`../../../greenlight/sindylom/.venv` (Python 3.14.2; numpy 1.26.4, pysindy 2.1.0,
casadi 3.7.2, do-mpc 5.1.1, gl_gym 0.3.1 — exactly the pins in
[requirements-cluster.txt](../cluster/requirements-cluster.txt)), driven through
`uv run --no-project --python <venv>`.

**Smoke status (1 seed, `--fast`):** `main` ✅ · `mechanism` ✅ (λ, knock, cross) ·
`parity` ✅ (horizon block + replay over 288 oracle steps) · `--merge` ✅ ·
`verify_regen.py --smoke` ✅ exit 0. All three experiments run end to end. The smoke found and fixed one real defect (**D7**,
below) and produced the oracle timings that reshaped the run plan. It has **not** been run
on the cluster image — `bash submit.sh smoke` is still the gate before the main waves.

---

## Which paper this register is about

**Read this first.** The register below was written against
[`paper/main.tex`](../paper/main.tex) (English, 16.07). The current manuscript is
[`paper/statya_ru.tex`](../paper/statya_ru.tex) (Russian, 20.07) — written from scratch for
*Автоматика и телемеханика*, already through one review round, and **substantially ahead of
the English file**: it uses the canonical multi-season table verbatim, makes the four-season
result the headline, reports the controlled single-coefficient ablation with paired
statistics, and states the DAgger data-budget caveat.

Already correct in `statya_ru.tex`, so **not** defects there — the register keeps them only
because they are still live in `main.tex`:

| Item | How the Russian version already handles it |
|---|---|
| G-2 λ non-monotonicity | Stated outright: at λ=0.1 the coefficient is exactly zero yet the margin is *not* minimal (2.49 vs 0.99), violations are maximal, and the sweep is explicitly called "not a controlled intervention in one coefficient" — the coefficient/margin link is labelled **association, not proven causation**. |
| G-3 causal claim | Rests on the controlled ablation, not the sweep: paired median **+3.19** EUR/m², IQR [+2.0, +3.6], 95% CI [+1.85, +3.40], Wilcoxon p=6.3e-5, positive in 17/20. |
| G-7 single season | The four-season table *is* the headline and matches `e3_multiseason_table.csv` cell for cell; the heuristic's 2020→2021 collapse (4.63 → −6.97) is the argument. |
| D6 stale numbers | Canonical multi-season values throughout. The one stale artifact — the Pareto figure — is flagged by the file's own `%% TODO` comment. |
| Oracle ceiling | Incorporates the 20.07 budget run: enlarging the optimiser budget does not help, so the binding constraint is the horizon, not the optimiser. |

**A correction to an earlier claim of mine in this file's history:** I asserted the cross
term `t_uBoil` "carries part of the heating pathway", from a mean of +1.03 EUR/m² over the
9 seeds with an active coefficient. That was an over-read of a noisy mean (positive in only
4 of 9). `statya_ru.tex` tests it properly and reports p=0.92 — no reliable effect. The
paper is right; the `cross` block in this regen should therefore be read as a confirmatory
check, not as evidence of a known interaction.

## Defect register — why a full regen and not a patch

Each row is a defect found by reading the current code and result files. The "Effect on the
paper" column is what changes in the text, not just in the data. Rows marked **[RU]** are
live in `statya_ru.tex` as well; the rest are `main.tex`-only or code-level.

### Blocking: the numbers themselves

| # | Defect | Evidence | Effect on the paper |
|---|--------|----------|---------------------|
| **D1** | The sparsity threshold — the paper's central hyper-parameter — is not in the frozen recipe. `CANONICAL_RECIPE` and `recipe_frozen.json` have no `threshold` key, so the confirmatory model silently takes `fit_sindy`'s function default. | [protocol_config.py:151](../protocol_config.py:151), [article_experiment_utils.py:590](../article_experiment_utils.py:590) (`threshold: float = 0.05`) | The frozen artifact does not determine the model. Reproducibility claim fails on its own terms. |
| **D2** | `load_frozen_recipe()` silently falls back to a hard-coded dict if the json is absent — in a container, a silent provenance break. The file itself carries an unresolved `PHASE-1 TODO: re-run E3 against THIS file to verify the reported e3_main_table numbers correspond to it (provenance was muddied on 2026-06-30 …)`. | [protocol_config.py:159](../protocol_config.py:159), [recipe_frozen.json](../results_scenarios/recipe_frozen.json) | It is not established that the reported confirmatory number was produced by the frozen recipe. For a paper about pre-registration integrity this is the worst open item. |
| **D3** | `TRAIN = {2018, 2019}` is declared everywhere, but every runner uses `train_scenarios()[0]` — 2018 only. | [run_multiseason.py:136](../run_multiseason.py:136), [run_e3_seeds.py](../run_e3_seeds.py) | Methods text does not describe the run. Fixing it changes every downstream number. |
| **D4** | Solver-failure budget differs 10× by controller: SINDy/grey-box 100, NN-MPC 10, oracle 10. The two controllers with the small budget are exactly the two the paper calls worst, and exactly the two that truncate: oracle 40/80 runs, NN-MPC 34/80 (mean season 93.6% / 93.3%). | [article_experiment_utils.py:993](../article_experiment_utils.py:993) vs [:1795](../article_experiment_utils.py:1795) and [:2334](../article_experiment_utils.py:2334) | "A black-box NN-MPC is worst" and "the oracle over-spends" are partly artifacts of an abort threshold. A truncated season forgoes both revenue and cost, so its EPI is not comparable. |
| **D5** | The oracle runs at horizon 12, every surrogate MPC at horizon 20. | [run_multiseason.py:117](../run_multiseason.py:117) vs [protocol_config.py:43](../protocol_config.py:43) | "Model fidelity does not explain the shortfall" is confounded with horizon. |
| **D7 [RU]** | **The confirmatory model is not reproducible at a fixed seed.** The frozen recipe uses `optimizer="ensemble"` → `ps.EnsembleOptimizer(base, bagging=True, n_models=20)`. In pysindy 2.1.0 that class takes **no** `random_state`/`seed` argument and resamples via `np.random.choice`, i.e. the *global* legacy NumPy RNG — which the codebase never seeds (`np.random.seed` appears nowhere; every other random source correctly uses `default_rng(seed)` or SB3's `seed=`). Refitting the same seed twice yields a different coefficient matrix, so `Ξ(uBoil→t_in)` may be zero on one run and not on the next. | [article_experiment_utils.py:582](../article_experiment_utils.py:582); verified against the installed pysindy 2.1.0 | Directly contradicts the reproducibility statement ("fixed RNG initial values"). Plausibly inflates the confirmatory variant's σ (±4.33/±3.92) and may explain why the baseline boiler coefficient is exactly 0 in 18/20 seeds but non-zero in 2. **Fix:** `np.random.seed(seed)` immediately before `fit_sindy` whenever the optimizer is `ensemble`, and record it in the manifest. |
| **D6** | Four mutually inconsistent headline tables; the paper uses the oldest. conf+DAgger EPI = 5.228 / 4.662 / 4.866 / 4.866; `scaled_pen` 426 in the paper's Table 2 appears in none of them. | [e3_main_table.csv](../results_scenarios/tables/e3_main_table.csv), [e3_main_table_20seed.csv](../results_scenarios/tables/e3_main_table_20seed.csv), [e3_pareto_table.csv](../results_scenarios/tables/e3_pareto_table.csv), [e3_multiseason_table.csv](../cluster/results_pull/multiseason/e3_multiseason_table.csv) | Table 2 is assembled from mixed sources. Δ vs rule-based is +0.59 or +0.03 depending on which file you believe. |
| **D7** | **The confirmatory model is not reproducible.** `_make_optimizer` builds `ps.EnsembleOptimizer(base, bagging=True, n_models=20)` with no `random_state`, so its bootstrap draws from numpy's *global* RNG, which no runner ever pinned. Measured 2026-08-03 on one seed and one identification dataset: ambient state → ξ(uBoil→t_in) = 0.0; `np.random.seed(2)` → 0.0; `np.random.seed(7)` → 0.056325; after 37 extra draws → 0.057179. | [article_experiment_utils.py:582](../article_experiment_utils.py:582); reproduced in the smoke run, where `sindy_mpc_conf` and the knock-block baseline were *different models on the same seed* until the fix | Whether the boiler term survives sparsification — the one quantity the paper is about — was decided by execution order, not by the frozen recipe. "18 of 20 seeds drop the boiler" is therefore not a property of the recipe. It also explains the confirmatory controller's ±4.33 dispersion on a mean of 1.18: that spread is a mixture of boiler-survived and boiler-dropped draws. |

### Blocking: the claims

| # | Defect | Evidence | Effect on the paper |
|---|--------|----------|---------------------|
| **G-1 [RU]** | **`grey_box_mpc` is not a grey-box model.** It is `fit_sindy(physics_no_cross, degree 1, threshold=1e-6)` — the same data-driven estimator as `sindy_mpc_dense` (threshold 1e-3). No first-principles model exists anywhere in the repo. `physics_no_cross` is a *feature library* (raw + psat, vpd, S_eff), not a physical model. | [run_multiseason.py:84](../run_multiseason.py:84), [run_e3_seeds.py:87](../run_e3_seeds.py:87), [article_experiment_utils.py:509](../article_experiment_utils.py:509) | "The repaired dense SINDy-MPC (3.81) coincides with the first-principles grey-box MPC (3.79)… the surrogate collapses onto the physical model it was meant to replace" is an identity, not a convergence. This contribution has to be dropped or a real grey-box authored. |
| **G-2** | The λ sweep contradicts the monotonicity claim at its own endpoint: at λ=0.1 the boiler coefficient is exactly 0 and EPI = 2.49 ± 0.88 — higher than at λ=0.04 (1.14) and λ=0.05 (0.99), where it is still non-zero, and higher than the confirmatory recipe (1.18). Violations there are the sweep's worst (8515). | [e3_lambda_sweep_table.csv](../results_scenarios/tables/e3_lambda_sweep_table.csv) vs [main.tex:455](../paper/main.tex:455), [main.tex:473](../paper/main.tex:473) | "EPI is monotone in the presence of the boiler coefficient" is false as written. The abstract's "collapses from 3.8 to 1.0" drops the endpoint. |
| **G-3** | The heating pathway is not one-dimensional. On the `physics` library, knocking out uBoil alone costs −5.89 EPI (8/9 seeds), but *also* removing the bilinear `t_in*uBoil` **recovers** +1.03 (4/9 seeds). | [e3_knockout_ablation.csv](../cluster/results_pull/knockout/e3_knockout_ablation.csv) | "The boiler coefficient is a one-dimensional causal proxy for economic competence" must be replaced. |
| **G-1b [RU]** | The refutation of G-1 sits three paragraphs above the claim. §4.2 asserts the repaired dense surrogate (3.81) "coincides with the grey-box MPC **built from first principles** (3.79)… the surrogate reduces to the physical model it was meant to replace" — while the λ table on the same page lists λ=10⁻⁶ → **3.79** and λ=10⁻³ → **3.81**. The "grey-box" *is* the λ=10⁻⁶ row of that very sweep. | [statya_ru.tex:545](../paper/statya_ru.tex:545) vs [statya_ru.tex:610](../paper/statya_ru.tex:610) | The paper compares two adjacent rows of its own sparsity sweep and reads the agreement as convergence onto an independent physical model. |
| **G-4 [RU]** | The rule-based baseline is called *tuned* and the honest-benchmark argument rests on it, but there is no tuning artifact: parameters are hard-coded and `temp_setpoint_day` occurs in exactly two files repo-wide, neither a sweep. Learned controllers get an explicit 16-trial budget. | [article_experiment_utils.py:297](../article_experiment_utils.py:297) | Either produce the sweep or call it what it is — an agronomic heuristic on stock setpoints. The result is *stronger* that way. |
| **G-5 [RU]** | The rule-based reference is deterministic: `epi_std == 0.0` in every year. A "paired Wilcoxon by seed against the rule-based baseline" is therefore a one-sample signed-rank test against a constant; pairing buys nothing. | all four E3 tables; [main.tex:296](../paper/main.tex:296), [statya_ru.tex:413](../paper/statya_ru.tex:413) | Methods wording, and the effect-size/CI machinery, must change. |
| **G-5b [RU]** | §3.5 still says SAC converged in only 10 of 20 repeats "and its results are reported on those", but Table 1's SAC row carries the 20-seed multi-season values (2020: −2.43, the n=20 figure; the n=10 figure was −2.408). Text and table disagree. | [statya_ru.tex:412](../paper/statya_ru.tex:412) vs [statya_ru.tex:492](../paper/statya_ru.tex:492) | One of the two is wrong; the regen removes the ambiguity by recording `n` per cell. |
| **G-6 [RU]** | The aggregation loop never queries the rule-based controller. `dagger_final` rolls the *learner's* MPC and refits on simulator ground truth — legitimate on-policy identification, but not DAgger, and the rule-based controller is not "the DAgger expert". | [e3_dagger_compare.py:50](../e3_dagger_compare.py:50) | Rename the method and drop the expert-imitation framing and its citation chain. |
| **G-7** | *(`main.tex` only — resolved in `statya_ru.tex`, see the table above.)* The single 2020 season carried the headline. Over 2020–2023 the ordering **inverts**: conf+DAgger is first in all four years (4-year mean +2.43), the rule-based heuristic is second from bottom (−1.21), oracle −2.19. | [e3_multiseason_table.csv](../cluster/results_pull/multiseason/e3_multiseason_table.csv) | "A tuned heuristic is a strong, hard-to-beat reference" and "the pre-registered hypothesis is not confirmed" are both single-season artifacts. This reframes the paper. |

### Process

| # | Defect |
|---|--------|
| **P-1** | The three most valuable runs (knockout, oracle-parity, multiseason, 17–20 July) are **untracked**: `?? own-article/cluster/`. `origin/main` is six weeks behind. Single copy, one laptop. |
| **P-2** | `main.tex` (16.07) incorporates none of those three runs; `statya_ru.tex` (20.07) incorporates all three. The two manuscripts therefore state materially different results from the same project, and only the untracked directory reconciles them. |
| **P-3** | `P.DEFAULT.seeds = range(10)` while every real run passes 20 via CLI — the "single source of truth" does not encode the seed set. |

Resolved on inspection, recorded so they are not re-raised: DAgger trains only on TRAIN
years, so there is **no test-year leakage** in the multi-season run
([run_multiseason.py:74](../run_multiseason.py:74)); `dagger_final` does pass the full recipe
to `fit_sindy`, so the DAgger variant is not silently a different estimator; and evaluation
rollouts add no excitation noise for anyone, so the rule-based zero variance is determinism,
not a fairness gap.

---

## What regen-v2 changes

| Was | Now | Defect |
|-----|-----|--------|
| threshold implicit (`fit_sindy` default 0.05) | explicit in every recipe, hashed into `config_hash` | D1 |
| silent recipe fallback | `load_recipe()` raises | D2 |
| TRAIN = 2018 only | TRAIN = 2018 + 2019, aggregated | D3 |
| solver budget 100 / 10 / 10 | 100 for everyone; `truncated` recorded and gated | D4 |
| oracle h=12, surrogate h=20 | h=20 for everyone + a 4-point oracle horizon sweep | D5 |
| 4 headline tables from 3 runs | one `main.csv`; all tables derived from it at merge | D6 |
| `grey_box_mpc` (claimed first-principles) | `sindy_mpc_lowthr` (honest name); `build_true_greybox()` raises with instructions | G-1 |
| ensemble bootstrap drew from ambient global RNG | `pin_rng()` before every fit, keyed on (regen_id, label, recipe, seed); the value is recorded in each row as `rng_seed` | D7 |
| λ grid ends where the coefficient hits 0 | 13 points extending past it, with per-point std and violations | G-2 |
| causality asserted from the λ sweep | single-coefficient knock-out/knock-in is the causal experiment; cross-term interaction measured separately | G-3, G-7 |
| single test season | 4 seasons are the primary result | G-7 |
| nothing checks the output | `verify_regen.py` gates, non-zero exit blocks publication | all |

Not changed here, because they are the author's calls, not defects: whether to author a real
grey-box baseline (G-1b), whether to run a rule-based tuning sweep (G-4), and how to rename
the aggregation method (G-6).

---

## Files

```
regen/
  regen_config.py         the ONLY place a number-affecting constant is declared
  recipe_frozen_v2.json   the confirmatory recipe, threshold included, for the record
  repro.py                seed_everything / env_fingerprint / --selftest
  run_regen.py            the driver: 8 experiments + --merge
  experiments_support.py  E2/E4/E5/E6/E7 bodies (imported by the driver)
  make_tables.py          every paper number + NUMBERS.md provenance map
  verify_regen.py         acceptance gates; non-zero exit = do not publish
  submit.sh               image|pvc|smoke|main|mech|support|all|merge|watch|pull
  k8s/                    00-pvc 10-smoke 20-main 30-mechanism-parity 40-support 90-merge-verify
```

Compute is **not** reimplemented: every rollout calls the already-validated
`article_experiment_utils` API, and the coefficient surgery reuses the shim from
`run_knockout_ablation`. This layer owns only what was inconsistent — recipe, horizon,
solver budget, train years, seed set, RNG, provenance.

### The eight experiments

| `--experiment` | Was | Covers |
|---|---|---|
| `main` | E3 + multiseason | 10 controllers × 4 seasons × 20 seeds = 800 seasons — the headline table |
| `mechanism` | λ sweep + knockout | 13-point threshold sweep, single-coefficient knock-out/in, `t_uBoil` cross block |
| `parity` | oracle probe + budget | oracle horizon sweep incl. h=20, optimiser-budget check, action replay along the oracle's own trajectory |
| `ladder` | E2 | the 3×2×4×3 identification-configuration sweep — the pre-registration artifact, open-loop only by design |
| `adapt` | E4 | static vs data aggregation vs EKF/RLS on the OOD seasons |
| `guard` | E5 | Mahalanobis / ensemble-spread signals, ROC, and the OOD guard's closed-loop effect |
| `faults` | E7 | six fault modes × residual supervisor |
| `design` | E6 (design half) | horizon, sparsity threshold, coefficient perturbation |

The **price half** of E6's tornado needs no rollouts. `epi_metrics` reads the simulator's
per-step profit, so prices cannot be swept inside a loop; `make_tables.py` re-derives them
exactly from the recorded physical quantities (revenue scales with the fruit price, the
three cost terms with theirs), holding the trajectories at their nominal-price optimum.
That is what a claim about *ranking* robustness actually means, and the table says so.

Each supporting experiment previously ran on its own season length — E5 on 14 days, E6/E7
on 30, the main table on 60 — and read `protocol_config` defaults rather than the frozen
config. They now share the canonical season, and every row records the window regardless.

## Reproducibility

`python repro.py --selftest` runs the pipeline twice and compares SHA-256 digests of the
training data, the ensemble coefficients, the STLSQ coefficients, the NN weights, and the
closed-loop trajectory and EPI. Verified on the pinned stack (Python 3.14.2, pysindy 2.1.0,
torch 2.11.0, `env_hash=173131a17717`): **all seven digests identical across runs.**

Two global RNGs had to be pinned first, both feeding controllers the paper draws
conclusions from — the ensemble optimiser (**D7**) and torch's MLP init plus DataLoader
shuffle. `pin_rng` derives the key from the run coordinates and delegates to
`repro.seed_everything`, so there is exactly one implementation; BLAS threads are pinned in
the same call, because float reduction order depends on the thread count and a last-bit
difference compounds over a 5760-step closed loop. The smoke job runs `--selftest` first,
so a non-deterministic environment stops the regen before it starts.

## Run order

```bash
bash submit.sh image     # on admin-01 — the old greenhouse-e3:v3 image predates this dir
bash submit.sh pvc
bash submit.sh smoke     # selftest + all 8 experiments on 2 seeds. READ the output.
bash submit.sh all       # main (4 waves) + mechanism/parity + support (5 waves)
bash submit.sh watch
bash submit.sh merge     # merge + make_tables + verify; non-zero exit means stop
bash submit.sh pull      # then COMMIT — see P-1
```

`merge` writes `tables/*.csv` and **`NUMBERS.md`** — a claim → value → source-file map. That
file is the deliverable that makes "confidence in the numbers" checkable: every figure the
manuscript states should appear there with the column it came from, or it does not go in
the paper.

Local smoke, same code, no cluster needed:

```bash
uv run --no-project --python ../../../greenlight/sindylom/.venv/Scripts/python.exe -- \
  python run_regen.py --experiment mechanism --seeds 0 --fast --tag local --out ./results
```

### Budget, from measured smoke timings

Oracle cost is ≈ `(56 + 10.75·h)` seconds on a 3-day/32-sample season (h=12 → 185 s,
h=20 → 271 s measured). Scaling to the real season (×20 steps, ×1.5 samples):

| | per seed | note |
|---|---|---|
| oracle, h=12 | ~1.5 h | matches the July run's measured 5250 s — sanity check on the extrapolation |
| oracle, h=20 (main wave) | ~2.3 h × 4 years ≈ 9 h | the long pole; ~10 h wall at parallelism 20 |
| oracle, h=48 / h=96 | ~4.8 h / ~9.1 h | why the horizon sweep runs on `ORACLE_SWEEP_SEEDS` (5 seeds), not 20 |
| everything else | minutes to ~1.5 h | cheap/dagger/RL/mechanism waves |

Total ≈ 350–400 CPU-h. Running the horizon sweep on all 20 seeds would have cost more than
the entire main table — that is the single most useful thing the smoke bought.

## Acceptance gates

`verify_regen.py` fails the run (exit 1) on: mixed `config_hash`, incomplete
`10 × 4 × 20` grid, duplicate cells, any truncated season, non-uniform horizon or solver
budget, missing `xi_uboil` on surrogate rows, an unresolved λ region, or an incomplete
knock block. It warns (exit 0, but the *text* must change) on: zero rule-based variance
(G-5), a per-year ranking that is not stable (G-7), non-monotone EPI in the boiler
coefficient (G-2), and a non-zero uBoil/cross interaction (G-3).

## Known limitations of this harness

- Smoke-tested locally on 1 seed in `--fast`, **not** on the cluster image and not at full
  scale. `bash submit.sh smoke` remains the gate.
- The `parity` replay block (oracle rollout → `trajectory_from_frame` → `evaluate_sindy`)
  is the one path not yet observed to completion; the horizon block before it ran green.
- Determinism is now pinned for numpy and torch. SB3's own internal RNG streams are seeded
  through `train_rl(seed=…)` as before; PPO/SAC reproducibility has not been re-verified
  under the new pinning.
- E4/E5/E6/E7 (adaptation, OOD guard, sensitivity, faults) are **not** in this regen. They
  are separate claims on separate runners; fold them in only after the main table is green.

## What the smoke already reproduced

- **G-1 confirmed empirically.** `sindy_mpc_dense` and `sindy_mpc_lowthr` (the old
  `grey_box_mpc`) returned EPI −0.3968 vs −0.3966 on 2020 and −0.4885 vs −0.4890 on 2021,
  with identical violation counts. They are the same estimator, so their agreement in the
  paper carries no evidential weight.
- **G-3 reproduced on one seed.** `ko_both − ko_uboil = +0.046`: removing the bilinear
  `t_uBoil` term on top of `uBoil` *improves* EPI relative to removing `uBoil` alone.
- **D7 found here, not on the cluster.** Before the RNG pin, `knock/baseline` and the main
  table's `sindy_mpc_conf` disagreed on the same seed (0.147 vs 0.255). After it they agree
  exactly (0.255 / 0.255), and the confirmatory fit is invariant to deliberately perturbed
  ambient RNG state.
