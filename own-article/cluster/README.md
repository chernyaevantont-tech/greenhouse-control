# E3 on Kubernetes (RKE2) — cluster execution harness

Runs the article's E3 closed-loop benchmark on the bare-metal RKE2 cluster
(`agroengineer-cluster`) instead of the retired two-host `server0`/`server1` +
`nohup`/`scp` setup. The heavy compute is embarrassingly parallel over
`(controller × seed × condition/year)`, so it runs as **plain indexed Kubernetes Jobs**
on CPU; every pod writes to **one shared Longhorn RWX volume**, and a merge step reads
them all.

## server0/server1 → Kubernetes mapping

| Old (own-article/remote_sync.sh)        | New (this dir)                                            |
|-----------------------------------------|----------------------------------------------------------|
| detached `nohup` job per host           | **indexed `Job`** (`completionMode: Indexed`), auto-restart/backoff |
| local multiprocessing across cores      | **pod parallelism** across all cluster nodes (`parallelism`) |
| `scp` partial CSVs from two hosts        | **one Longhorn RWX PVC** (`e3-results`) mounted at `/results` by every pod |
| `merge_e3.py` over pulled partials       | each runner's `--merge` mode over `/results/*` (in-cluster merge Job) |
| shard by hand (server0=cheap, server1=long) | shard by `JOB_COMPLETION_INDEX` (round-robin over seeds)  |

## What each job is for (reviewer items)

| Job manifest (`k8s/`)          | Reviewer item | Experiment | Runner |
|--------------------------------|:-:|------------|--------|
| `e3-knockout-job.yaml`         | **#1** | boiler knock-out / knock-in ablation (+ interaction check) | `run_knockout_ablation.py` |
| `e3-multiseason-job.yaml`      | **#3** | multi-season main comparison (2020–2023) | `run_multiseason.py` |
| `e3-oracle-parity-job.yaml`    | **#6** | oracle solver-parity / action-replay | `run_oracle_parity.py` |

All three shard **by seed** (20 seeds → `completions: 20`); the runners select their slice
via `--shard-index $JOB_COMPLETION_INDEX --num-shards 20 --seeds-all 0,…,19`.

## Files

```
cluster/
  Dockerfile                  CPU image (python:3.11-slim + the article compute stack)
  requirements-cluster.txt    exact pinned deps the harness was validated against
  submit.sh                   kubeconfig / build / apply / watch / merge / pull helper
  k8s/
    results-pvc.yaml          namespace greenhouse-e3 + Longhorn RWX PVC e3-results
    e3-knockout-job.yaml      indexed Job — reviewer #1
    e3-multiseason-job.yaml   indexed Job — reviewer #3 (+ commented GPU RL / oracle waves)
    e3-oracle-parity-job.yaml indexed Job — reviewer #6
```
The runners live in `own-article/` (siblings of `article_experiment_utils.py`, which they
import via `sys.path`). They reuse the real API verbatim (`fit_sindy`,
`build_mpc_controller`, `rollout_mpc`, `epi_metrics`, `collect_rule_based_dataset`,
`rollout_oracle_mpc`, `train_rl`/`rollout_rl`). Each supports `--merge` and `--fast`
(minutes-long smoke). All three were smoke-tested end-to-end against the live
`pysindy 2.1 / casadi / do_mpc / gl_gym` stack.

## Access wiring (one-time)

```bash
bash submit.sh kubeconfig     # prints the exact commands, summarised:
ssh ubuntu@192.168.1.148 'cat /etc/rancher/rke2/rke2.yaml' > ~/.kube/agro-cluster.yaml
sed -i 's#https://127.0.0.1:6443#https://192.168.1.148:6443#' ~/.kube/agro-cluster.yaml
export KUBECONFIG=~/.kube/agro-cluster.yaml
kubectl get nodes -o wide     # admin-01 + gpu-01..NN Ready
```

### Image (build on admin-01 — it has internet + the local registry)

```bash
# on admin-01, from the repo root:
docker build -f own-article/cluster/Dockerfile -t localhost:5000/agro/greenhouse-e3:v1 .
docker push  localhost:5000/agro/greenhouse-e3:v1
```
Manifests reference it as `docker.io/agro/greenhouse-e3:v1`; containerd's mirror rewrites
that to the local registry (cluster-runbook.md §"local-first"; the §18 devpi image uses the
same `docker.io/agro/…` pattern). **Never** hardcode `10.10.0.2:5000/…` in an image field —
containerd hits it over HTTPS and fails (`server gave HTTP response to HTTPS client`).
`pip` inside the build flows through the local **devpi** PyPI mirror when
`PIP_INDEX_URL` is passed as a build-arg (optional; admin-01's Wi-Fi reaches PyPI directly).

## Run

```bash
bash submit.sh pvc            # namespace + Longhorn RWX PVC
bash submit.sh knockout       # reviewer #1
bash submit.sh multiseason    # reviewer #3 (cheap CPU wave; see file for RL-GPU/oracle waves)
bash submit.sh oracle         # reviewer #6
bash submit.sh watch          # jobs/pods + how to tail logs by shard index
bash submit.sh merge          # in-cluster merge -> e3_*_ablation.csv on the PVC
bash submit.sh pull           # copy merged CSVs to ./results_pull on this PC
```

Merged artifacts on the PVC:
`/results/knockout/e3_knockout_ablation.csv`,
`/results/multiseason/e3_multiseason.csv` (+ `_table.csv`),
`/results/oracle_parity/e3_oracle_parity.csv`.

## Expected wallclock

Per-run costs (measured, 60-day season): rule_based ~6 s, sindy/grey ~100–140 s,
ppo ~500 s, nn_mpc ~2840 s, sac ~4400 s, oracle_mpc ~5250 s. With ~40–64 parallel CPU
workers (20 pods × 2–4 CPU):

| Job | per-pod (1 seed) | wall (20 pods) |
|-----|------------------|----------------|
| knockout (#1) | 6 rollouts ≈ 12–15 min | **~15–20 min** |
| oracle-parity (#6, action_replay) | 1 fit + 1 collect ≈ 2–4 min | **~5–10 min** |
| multiseason cheap (#3) | 4 controllers × 4 yr, nn-dominated ≈ 60–80 min | **~1.5 h** |
| multiseason RL (#3, ppo+sac) | ≈ 85–90 min (GPU faster) | ~1.5 h CPU / ~6 h at GPU-quota 5 |
| multiseason oracle (#3) | 5250 s × 4 yr ≈ 5.8 h | **~6 h** (the long pole) |

Single-season 20-seed E3 ≈ 64 CPU-h; the 4-season sweep ≈ 4× that (~256 CPU-h), collapsed
to ~6 h wall by the oracle long-pole under pod parallelism.

## Scope / TODO

`run_oracle_parity.py` **`action_replay`** (model-error decomposition) is fully implemented.
The **`solver_parity`** mode (true-model IPOPT oracle, same solver as the surrogate MPC) is
scaffolded and raises `NotImplementedError` — a human must wire the true CasADi dynamics
`env.unwrapped.F` into a do-mpc model (see the `build_true_model_mpc` TODO in that file).
The GPU RL wave in `e3-multiseason-job.yaml` is optional and commented (the workload is
CPU-bound; GPU only accelerates PPO/SAC retraining).
