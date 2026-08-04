"""E3 oracle CEM-budget sweep (reviewer item #6, pragmatic closure).

Reviewer #6 asks whether the oracle's weak EPI is the MODEL's fault or the OPTIMIZER's.
The action-replay mode of run_oracle_parity.py isolates model error; this runner attacks
the other half by INCREASING the CEM optimization budget (n_samples x n_iters). If the
oracle's EPI does NOT improve as the budget grows, its weakness is not under-optimization
(it is the structural short-horizon resource overspend documented in the article), and the
true-model IPOPT "same-solver" experiment is unnecessary (it is also computationally
impractical -- embedding the 28-state env.F into do-mpc/IPOPT does not converge, see
run_oracle_parity.build_true_model_mpc).

Design: on a fixed 14-day probe window (same window as the oracle horizon sweep, so numbers
are comparable to it -- NOT the 60-day seasonal EPI), roll the CEM oracle out at several
budgets and record EPI. Sharded over (seed x budget) CELLS so the expensive high-budget
cells isolate on their own pods (wall = slowest single cell, not the per-pod sum).

Examples
  python run_oracle_budget.py --seeds 0,1 --tag s01
  python run_oracle_budget.py --shard-index 0 --num-shards 24 --tag shard0 --out /results
  python run_oracle_budget.py --merge --out /results
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402
import protocol_config as P  # noqa: E402

# CEM budgets to sweep: (n_samples, n_iters). Base == the article's oracle setting.
BUDGETS = [(48, 2), (96, 3), (192, 4)]
PROBE_DAYS = 14                      # 14-day probe window (matches the horizon sweep)
SEEDS_DEFAULT = list(range(8))       # 8 seeds x 3 budgets = 24 cells


def _cells(seeds):
    """Flatten (seed x budget) into an ordered list of cells for sharding."""
    return [(s, ns, ni) for s in seeds for (ns, ni) in BUDGETS]


def run_cell(seed: int, n_samples: int, n_iters: int, pc, test_scen, CORR, PRICES,
             days: int = PROBE_DAYS) -> dict:
    start = test_scen["start_date"]
    cfg = pc.cfg_for(test_scen, seed=seed)
    t0 = time.time()
    df = U.rollout_oracle_mpc(cfg, n_days=days, start_date=start,
                              horizon=12, n_samples=n_samples, n_iters=n_iters)
    m = U.epi_metrics(df, corridors=CORR, prices=PRICES)
    secs = round(time.time() - t0, 1)
    rec = {"seed": seed, "n_samples": n_samples, "n_iters": n_iters,
           "cem_budget": n_samples * n_iters, "probe_days": days,
           "epi": float(m.get("epi", float("nan"))),
           "viol": int(m.get("violation_steps_total", 0)),
           "secs": secs}
    print(f"[oraclebudget] seed {seed} budget {n_samples}x{n_iters} "
          f"EPI={rec['epi']:.3f} viol={rec['viol']} ({secs}s)", flush=True)
    return rec


def worker(args) -> int:
    pc = P.DEFAULT.resolved(bool(args.fast))
    econ = P.read_env_economics(pc.location)
    CORR, PRICES = econ["corridors"], econ["prices"]
    test_scen = pc.test_scenario()             # in-distribution 2020
    out = _out_dir(args.out) / f"e3_oracle_budget_{args.tag}.csv"

    days = 2 if args.fast else PROBE_DAYS
    cells = _resolve_cells(args)
    if args.fast:                       # smoke: one cheap cell per seed
        cells = [(s, 16, 1) for (s, _, _) in cells]
        seen = set(); cells = [c for c in cells if not (c in seen or seen.add(c))]
    print(f"[oraclebudget {args.tag}] cells={cells} days={days} out={out}", flush=True)
    records: list[dict] = []
    for (s, ns, ni) in cells:
        try:
            records.append(run_cell(s, ns, ni, pc, test_scen, CORR, PRICES, days=days))
            pd.DataFrame(records).to_csv(out, index=False)
        except Exception as exc:  # noqa: BLE001
            print(f"[oraclebudget {args.tag}] seed {s} {ns}x{ni} FAILED "
                  f"{type(exc).__name__}: {str(exc)[:150]}", flush=True)
    pd.DataFrame(records).to_csv(out, index=False)
    print(f"[oraclebudget {args.tag}] DONE wrote {out} ({len(records)} rows)", flush=True)
    return 0


def merge(args) -> int:
    outd = _out_dir(args.out)
    parts = sorted(glob.glob(str(outd / "e3_oracle_budget_*.csv")))
    parts = [p for p in parts if os.path.basename(p) != "e3_oracle_budget.csv"]
    frames = [pd.read_csv(p) for p in parts if os.path.getsize(p) > 0]
    if not frames:
        print("no oracle-budget partials found in", outd)
        return 1
    d = pd.concat(frames, ignore_index=True).drop_duplicates(
        ["seed", "n_samples", "n_iters"], keep="last")
    d.to_csv(outd / "e3_oracle_budget.csv", index=False)
    agg = (d.groupby(["n_samples", "n_iters"])
           .agg(epi_mean=("epi", "mean"), epi_std=("epi", "std"),
                viol=("viol", "mean"), secs=("secs", "mean"), n=("seed", "nunique"))
           .reset_index())
    print(agg.round(3).to_string(index=False))
    d.to_csv(outd / "e3_oracle_budget.csv", index=False)
    print(f"merged {len(parts)} partials -> {len(d)} rows -> {outd / 'e3_oracle_budget.csv'}")
    return 0


def _out_dir(out):
    from pathlib import Path
    if out:
        p = Path(out); p.mkdir(parents=True, exist_ok=True); return p
    return U.results_dir() / "tables"


def _resolve_cells(args):
    if args.seeds:
        seeds = [int(s) for s in args.seeds.split(",") if s.strip() != ""]
        return _cells(seeds)
    if args.shard_index is not None and args.num_shards:
        allc = _cells(SEEDS_DEFAULT)
        return allc[args.shard_index::args.num_shards]
    raise SystemExit("need --seeds, or --shard-index/--num-shards, or --merge")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", help="comma-separated seeds (runs all budgets for each)")
    ap.add_argument("--shard-index", type=int, default=None)
    ap.add_argument("--num-shards", type=int, default=None)
    ap.add_argument("--tag", default="local")
    ap.add_argument("--out", default=None)
    ap.add_argument("--fast", type=int, default=0)
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    if args.merge:
        return merge(args)
    return worker(args)


if __name__ == "__main__":
    raise SystemExit(main())
