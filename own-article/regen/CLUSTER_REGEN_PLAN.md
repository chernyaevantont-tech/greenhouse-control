# Single-environment regeneration on the cluster — plan (2026-09-16)

> **Shelved the same day.** After the inventory below the owner decided to keep the
> two-environment record as the manuscript now states it (Section 2.9): every claim-bearing
> contrast sits inside one environment, the one crossing contrast (priced-minus-default for
> six controllers) is read against the measured drift, and a full regeneration would move
> every number for the sake of one sentence. This plan and `k8s/60-single-environment.yaml`
> are kept for a revision round in case a reviewer asks for it; nothing was launched.


**Decision (owner, 2026-09-16):** every wave the manuscript reads is to be computed on the
Linux cluster, so that the results tree comes from one platform and Section 2.9 can drop the
two-environment account. Today the `image` column of the result rows splits the tree: the
canonical `final/` blocks carry `greenhouse-regen:v1` (cluster container, `python:3.11-slim`),
everything produced after 10 August carries `local` (workstation, Python 3.14).

Nothing in this plan has been launched. SSH to `admin-01` (192.168.1.148) failed on
2026-09-16 with `kex_exchange_identification: Connection closed by remote host` on port 22
while ports 22, 443, 5000, 6443 and 8080 all accept TCP — sshd is dropping the connection
before authentication (fail2ban / MaxStartups / a host-key or algorithm restriction), which
has to be looked at on the node itself. No kubeconfig exists on the workstation.

---

## 1. What is re-run

Everything with `image == local`; the `final/` blocks already produced in the container stay
(see §7 for the alternative of re-running them too). Per-run wall times are the `secs` column
of the existing files; CPU-hours are on one core per pod, as the jobs request.

| Job (`k8s/60-single-environment.yaml`) | Replaces | Runs | ≈ CPU-h | What the paper takes from it |
|---|---|---|---|---|
| `regen-priced-main` | `priced_main/main_priced*.csv` (SINDy rows) | 5 × 80 | 6 | Table 6/7 priced pool, Figure 2, waterfall b |
| `regen-priced-nn` | `priced_main/main_pricedNN*.csv` | 40 (10 seeds) | 21 | `nn_mpc` priced row (§7: run 20 seeds → 41 h and the "10 seeds" caveat disappears) |
| `regen-priced-dagger` | `priced_dagger/` | 160 | 3 | the two re-identified variants |
| `regen-phys-lib` | `phys_lib/main_physlib.csv` | 160 | 3 | full-physics rows, one-factor triple |
| `regen-notuboil` + `regen-notuboil-ladder` | `notuboil/` | 160 + 40 fits | 3 | term-deletion probe, Table 9 |
| `regen-priced-mech` | `priced_mech/` | 400 | 7 | λ sweep, knock-in/out, cross block (priced) |
| `regen-n7-raw-default` | `n7/main_n7.csv` | 160 | 3 | default end of the library-effect waterfall |
| `regen-n5-unseen` | `n5_years/main_n5.csv` | 128 | 2 | Table 8 (needs 2014–2017 weather in the image) |
| `regen-ec-h8` | `ec_h8/main_ec_h8.csv` | 160 | 2 | horizon-8 comparison |
| `regen-ladder-rerun` | `ladder_rerun/` | 1440 fits | 7 | Table 4, Figure 1a/b, ladder ranks |
| `regen-holdout` | `holdout/` | 240 fits | 1 | Table 14, held-out check |
| `regen-tune-rb` | `n2_tune/tune_rb_n2.csv` | 17 × 6 | 0.2 | Tables 3/5, tuned reference |
| `regen-ea-draws` | `ea_draws/` | 471 | 8 | draw-axis paragraph |
| `regen-design-fine` | `design_priced_real/`, `priced_design/` | 280 | 5 | Table 13, Figure 4a |
| `regen-adapt-draws` | `final/adapt.csv` | 1800 | 44 | adaptation block |
| `regen-guard-draws` | `final/guard.csv` | 1800 | 30 | guard block |
| `regen-v3-parity` | `v3_parity/parity_v3.csv` | 5 planner seasons + replay | 10 | replay error along the planner trajectory |
| `regen-oracle-budget` | `oracle_budget/` | 2 planner seasons | 5 | the 2022 budget diagnostic |
| **total** | | ≈ 7 600 rows | **≈ 160** | |

At the cluster's ~28 usable cores this is one working day of wall time; the long poles are
one adapt shard (90 runs, ≈ 2.2 h), one `nn_mpc` shard (4 seasons, ≈ 2 h) and the planner
seasons (≈ 2–3 h each). Not re-run: `n3_priced` (superseded partial), the smoke files.

## 2. Prerequisites

1. **Access.** Restore SSH to `admin-01` (check `journalctl -u ssh`, `fail2ban-client status
   sshd`, `MaxStartups`); or copy a kubeconfig to the workstation and drive `kubectl` over
   6443 directly.
2. **Weather 2014–2017.** The unseen-season wave needs four weather years that exist nowhere
   on disk today (`own-article/cluster/weather/Rostov-on-Don/` and the local `gl_gym` data
   directory hold 2018–2023 only). Regenerate on a machine with internet, then place the four
   files beside the six before the image build:
   ```bash
   python own-article/make_weather.py --years 2014,2015,2016,2017 --out own-article/cluster/weather/Rostov-on-Don
   ```
   The generator is checked by regenerating a shipped year and comparing (its docstring).
3. **Image v5.** The v1–v4 images predate the `physics_no_tuboil` library, the `--objective`
   flag and the horizon/budget overrides, so a new image is built from the current tree on
   `admin-01` (the only host with internet and the registry):
   ```bash
   cd ~/greenhouse-control                                   # after syncing the tree
   docker build -f own-article/cluster/Dockerfile -t localhost:5000/agro/greenhouse-regen:v5 .
   docker push localhost:5000/agro/greenhouse-regen:v5
   ```
   `cluster/Dockerfile` is unchanged in base (`python:3.11-slim`) and pins
   (`requirements-cluster.txt`), so the platform is the one the canonical blocks ran on.
4. **Smoke first.** Point `k8s/10-smoke.yaml` at `v5` (image and `REGEN_IMAGE`), apply it, and
   read the gate output before anything else is submitted:
   ```bash
   kubectl -n greenhouse-regen wait --for=condition=complete --timeout=3600s job/regen-smoke
   kubectl -n greenhouse-regen logs -l wave=smoke --tail=-1
   ```
5. **PVC.** `regen-results` exists from the canonical run (`k8s/00-pvc.yaml`); the new jobs
   write to per-wave directories under `/results`, not to `/results/raw`, so nothing from the
   canonical tree is touched.

## 3. Launch

```bash
kubectl apply -f own-article/regen/k8s/60-single-environment.yaml
kubectl -n greenhouse-regen get jobs -l app=greenhouse-regen
kubectl -n greenhouse-regen logs -f -l wave=priced-main --prefix --max-log-requests=20
```

Submit the two long poles (`regen-adapt-draws`, `regen-guard-draws`) first if the cluster
is shared; everything else fits behind them. A failed shard is re-run by deleting its job
and re-applying with `completions`/`parallelism` unchanged — the tag carries the shard index,
and the dedup key (`method`/`block`, `seed`, `test_year`) makes partial re-runs safe.

## 4. Pull

`bash own-article/regen/submit.sh pull` copies `/results` to `regen/results_pull/`. Commit
the pull before touching anything else (the 2026-07 results once lived untracked on one
laptop for two weeks).

## 5. Merge into the tree the paper reads

The loaders in `paper/en/figures/_plotstyle.py` and the verifiers read fixed paths. For each
wave, concatenate the shard files into the file name the loader expects, keep the manifest,
and replace the workstation files (git keeps the old ones):

| Pulled directory | Expected file(s) |
|---|---|
| `priced_main/main_priced*.csv`, `main_pricedNN*.csv` | keep as is — the loader globs `priced_main/*.csv` |
| `priced_dagger/main_pricedDag*.csv` | keep as is (glob) |
| `phys_lib/main_physlib*.csv` | → `phys_lib/main_physlib.csv` (loaded explicitly) |
| `notuboil/main_notuboil*.csv`, `ladder_notuboil.csv` | → `notuboil/main_notuboil.csv`, `ladder_notuboil.csv` |
| `priced_mech/mechanism_pricedMech*.csv` | keep (glob) |
| `n7/main_n7_*.csv` | → `n7/main_n7.csv` |
| `n5_years/main_n5_*.csv` | → `n5_years/main_n5.csv` |
| `ec_h8/main_ec_h8_*.csv` | → `ec_h8/main_ec_h8.csv` |
| `ladder_rerun/ladder_ladder_rerun*.csv` | → `ladder_rerun/ladder_rerun.csv`; the loaders name `ladder_rerun.csv` **and** `ladder_rerun2.csv` explicitly (`_plotstyle.load_ladder`, `verify_*`), so either write the second file too or switch those readers to the glob `ladder_rerun*.csv` (one line each) |
| `holdout/holdout_holdout*.csv` | → `holdout/holdout_holdout.csv` |
| `n2_tune/tune_rb_n2.csv` | as is |
| `ea_draws/draws_ea*.csv` | the readers name `draws_ea.csv` and `draws_ea2.csv` explicitly; merge the six shards into `draws_ea.csv` and switch the readers to the glob, as for the ladder |
| `design_priced_real/design_designPriced*.csv` | → `design_priced_real/design_designPriced.csv`; drop `priced_design/` (misnamed duplicate) |
| `adapt_draws/adapt_a*.csv`, `guard_draws/guard_g*.csv` | → `final/adapt.csv`, `final/guard.csv` (the merge step of `run_regen.py --merge`) |
| `v3_parity/parity_v3_*.csv` | → `v3_parity/parity_v3.csv` |
| `oracle_budget/main_orcbudget*.csv` | → `oracle_budget/main_orcbudget.csv` |

Then, from `own-article/regen`:
```bash
python make_tables.py --out results/final       # derived tables + NUMBERS.md
python verify_regen.py --out results/final      # gates; the two known oracle-abort failures remain
```
Check that every row of every wave now carries `image == greenhouse-regen:v5` (or `v1`/`v4`
for the canonical blocks) and none carries `local`:
```bash
python - <<'PY'
import glob, pandas as pd
bad = {f for f in glob.glob("results/*/*.csv") if "image" in pd.read_csv(f, nrows=5)
       and (pd.read_csv(f)["image"] == "local").any()}
print("files still local:", sorted(bad))
PY
```

## 6. The manuscript afterwards

Every closed-loop number that came from a workstation wave will move — chaotic amplification
means per-run values change even where the pattern does not — so this is the expensive half:

1. `python verify_manuscript.py` in `paper/en` lists every table cell and prose value that
   no longer agrees with the tree (800 cells, 410 prose values, 2102 printed numbers today).
   The tables are hand-written LaTeX: each mismatching cell is retyped from
   `results/final/tables/*.csv` and `NUMBERS.md`; prose values likewise, sentence by
   sentence, with the anchors in `verify_prose.py` as the checklist.
2. Re-derive the claims that are counts or orderings and may flip: Holm-corrected levels and
   the "significant / not separable" wording of Table 7 and §3.3 (run and seed level), the
   Pareto front membership (five members; `make_fig2.py` and `make_fig6.py` fail the build if
   the front changes shape), boiler-term survival fractions (0.55 / 0.15 / 0.55 / 0.40 are
   per-seed fit properties and may move by one or two seeds), the 2021 reversal, the
   `dense`/`lowthr` near-identity, and the McNemar/Wilson figures of the term-deletion probe.
3. `python figures/make_fig1.py … make_fig6.py` — each ends in a self-check against its own
   caption; a caption claim that stops holding fails the build and is re-worded, not
   re-fitted.
4. §2.9, §3 preamble, §4.6 and Finding 5: the two-environment account collapses to one
   sentence ("all waves were produced on one Linux compute cluster under Python 3.11"); the
   seed-matched priced−default caveat goes; the deterministic-heuristic drift paragraph is
   re-measured (the two harnesses are then on one platform, so the drift should vanish or
   shrink to last-bit noise — report what is found).
5. Deposit: `regen/README.md` §Software and `ARCHIVE_README.txt` describe one environment;
   `make_archive.py` → new hash into `ZENODO.md`; `REMAINING.md` §0 records the pass.
6. Word build and audit as in `REMAINING.md` §5; page-by-page read of the rendered file.

Budget: one cluster day for §§2–4, then two to three working days for §§5–6.

## 7. Choices still open

- **Re-run `final/` as well?** The canonical blocks are already cluster-produced (`v1`, `v4`),
  so the platform is one either way; re-running them on `v5` would add the planner
  (≈ 155 CPU-h), `nn_mpc` under the default objective (≈ 41 h), PPO/SAC training and the
  rest (≈ 20 h) for a single image version instead of two. Not required for the
  single-environment claim; it is required only if the manuscript is to say "one image".
- **`nn_mpc` at 20 seeds under the priced objective** (+ 20 CPU-h) removes the one unequal
  replication the paper has to caveat in six places.
- **Seeds.** 20 everywhere is the frozen configuration and stays (`regen_config.SEEDS`).
