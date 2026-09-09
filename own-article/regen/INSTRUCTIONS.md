# Recomputing the draw-axis waves (`adapt`, `guard`)

Most waves in `results/` are deterministic given a seed: `faults`, `design`, the λ sweep and
the cross block all fit with `stlsq`, which has no bootstrap draw. The two that are not are
**`adapt` (E4)** and **`guard` (E5)**: both use the `confirmatory` recipe, which is an
ensemble fit, so every number they produce depends on which bootstrap realisation was drawn.

That axis is not a nicety. The `draws` experiment measured it: on `sindy_mpc_conf_dagger` a
single realisation gave −0.12 EUR m⁻² where the mean over draws is +0.69 — an error of
+0.81 that moved the method from fourth place to first. Reporting one draw per seed as a
point estimate is exactly the defect the `draws` wave exists to expose, so these two waves
are run with `--draws 10`.

This file is the runbook for reproducing them. The shipped `results/final/adapt.csv` and
`guard.csv` (1800 rows each) were produced this way, on a 16-core desktop, in about five
hours.

---

## 0. Environment

The pinned stack is `numpy 1.26.4`, `pysindy 2.1.0`, `casadi`, `do-mpc`, `gl_gym 0.3.1`,
`torch`. Install order matters: `gl_gym` requires `numpy<2.0` while the `pysindy 2.1.0`
wheel declares `numpy>=2.0` (it works on 1.26.4), so a single `pip install -r` cannot be
resolved.

```bash
uv venv --python 3.11 .venv-regen
```

```bash
uv pip install --python .venv-regen -r requirements-cluster.txt --no-deps pysindy==2.1.0
```

`requirements-cluster.txt` lives in `own-article/cluster/` in the project repository; it is
not part of this package.

---

## 1. Determinism check (required, ~2 minutes)

```bash
python repro.py --selftest
```

It must end with `fully reproducible` and seven `[PASS]` lines. A single `[FAIL]` means the
environment is non-deterministic and the numbers it produces are not usable — stop there.
Record the `env_hash` it prints: it belongs in the provenance of anything computed
afterwards.

---

## 2. Smoke (~10 minutes)

```bash
python run_regen.py --experiment adapt --seeds 0 --draws 2 --fast --tag smoke --out ./results/smoke && python run_regen.py --experiment guard --seeds 0 --draws 2 --fast --tag smoke --out ./results/smoke
```

The log must contain both `seed 0 draw 0 …` and `seed 0 draw 1 …`. If there is no `draw`
column, or only one draw appears, the loop is not running and the full wave would silently
reproduce the single-realisation defect.

---

## 3. Full run (~5–7 hours)

Sharded over the seeds, one process per physical core. Each process is single-threaded
(`OMP_NUM_THREADS=1` is set internally), so parallelism is the process count.

`adapt` first — it is the more expensive of the two, because of the EKF:

```bash
for i in $(seq 0 15); do python run_regen.py --experiment adapt --draws 10 --shard-index $i --num-shards 16 --tag "a$i" --out ./results/raw > ./results/log_a$i.txt 2>&1 & done; wait
```

then `guard`:

```bash
for i in $(seq 0 15); do python run_regen.py --experiment guard --draws 10 --shard-index $i --num-shards 16 --tag "g$i" --out ./results/raw > ./results/log_g$i.txt 2>&1 & done; wait
```

Chain them with `&&` to leave both running unattended.

| wave | grid | CPU-hours | wall clock on 16 cores |
|---|---|---|---|
| `adapt` | 20 seeds × 10 draws × 3 seasons × 3 modes | ~50 | ~3.5 h |
| `guard` | 20 seeds × 10 draws × 3 seasons × 2 modes | ~25 | ~1.7 h |
| **total** | | **~75** | **~5 h**, 6–7 with the tail |

Memory: 16 processes × 1.5–2 GB ≈ 32 GB. SMT at 28–32 processes cuts it to about 4 hours,
but the EKF is memory-hungry in places, so the gain is small and the swap risk is not worth
it. Sixteen is the right number.

---

## 4. Merge and verify (~2 minutes)

```bash
python run_regen.py --merge --out ./results/raw && python make_tables.py --out ./results/raw && python verify_regen.py --out ./results/raw
```

`verify_regen.py` exits non-zero on blocking failures. On the shipped tree that is expected
and explained: the two blocking failures are `oracle_mpc` solver aborts, discussed under
"Acceptance gates" in `README.md`. What matters is that the *other* gates pass and that
`NUMBERS.md` regenerates.

The deliverables are `results/raw/tables/*.csv` and `results/raw/NUMBERS.md`, the
claim → value → source-file map.

---

## Troubleshooting

**`ModuleNotFoundError: gl_gym`** — wrong interpreter. Check that
`python -c "import gl_gym; print(gl_gym.__version__)"` prints `0.3.1`.

**`load_recipe … refusing to run (D1)`** — the safety catch fired: a recipe reached
`fit_sindy` without an explicit threshold. `regen_config.py` has been modified or is
damaged; restore it from the repository.

**`config_hash` mismatch** — `verify_regen.py` fails the run at `G0`. That is the guard
against mixing results computed under different configurations: `regen_config.py` changed
between the two runs being merged.

**Out of memory** — reduce the shard count to 8–12. Wall clock grows proportionally and the
results do not change; sharding only splits the seeds.

**Interrupted run** — partitions are written incrementally after every row, so only the
failed shards need repeating: re-run them with the same `--shard-index` and the files are
rewritten.
