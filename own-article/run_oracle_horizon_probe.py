"""Oracle horizon probe (Path A hero-result / Path B go-no-go).

Single-knob test of the central claim: the economic oracle underperforms the
rule-based baseline ONLY because its shooting horizon (12 steps = 3 h) is myopic to
the multi-day fruit-growth payoff -- NOT because of model fidelity (it has the true
model). We sweep the oracle's CEM horizon and check whether EPI rises toward/above
rule_based. Everything else (economic objective, n_samples, n_iters, warm-start) is
held identical to the article oracle in run_e3_seeds.py.

Writes results_scenarios/tables/oracle_horizon_probe_<tag>.csv incrementally so
partial results survive interruption.

Examples
  # smoke: 1 day, one seed, two horizons -- measures per-step cost on THIS machine
  python run_oracle_horizon_probe.py --smoke --tag smoke
  # real probe: 14-day window, 2 seeds, horizons 3/6/12/24/48 h
  python run_oracle_horizon_probe.py --window 14 --seeds 0,1 \
      --horizons 12,24,48,96,192 --tag w14
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import article_experiment_utils as U  # noqa: E402
import protocol_config as P  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=14, help="rollout length [days]")
    ap.add_argument("--seeds", default="0,1", help="comma-separated seeds")
    ap.add_argument("--horizons", default="12,24,48,96,192",
                    help="comma-separated oracle shooting horizons [steps]; 96=24h")
    ap.add_argument("--n_samples", type=int, default=48)
    ap.add_argument("--n_iters", type=int, default=2)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--smoke", action="store_true", help="1-day / 1-seed / horizons 12,48")
    args = ap.parse_args()

    if args.smoke:
        args.window = 1
        args.seeds = "0"
        args.horizons = "12,48"

    seeds = [int(s) for s in args.seeds.split(",") if s.strip() != ""]
    horizons = [int(h) for h in args.horizons.split(",") if h.strip() != ""]

    pc = P.DEFAULT.resolved(False)
    RES = U.results_dir()
    econ = P.read_env_economics(pc.location)
    CORR, PRICES = econ["corridors"], econ["prices"]
    test_scen = pc.test_scenario()
    TEST_START = test_scen["start_date"]
    N = int(args.window)

    keep = ["epi", "revenue", "cost_total", "cost_heat", "cost_elec", "cost_co2",
            "fruit_dm_growth", "violation_steps_total", "t_in_in_corridor_pct", "steps"]
    out = RES / "tables" / f"oracle_horizon_probe_{args.tag}.csv"
    records: list[dict] = []

    def _row(method, seed, horizon, m, secs):
        r = {"window_days": N, "horizon": horizon, "horizon_h": round(horizon * pc.period / 3600.0, 2),
             "method": method, "seed": seed, "secs": round(secs, 1)}
        for k in keep:
            r[k] = m.get(k)
        return r

    def _flush():
        pd.DataFrame(records).to_csv(out, index=False)

    print(f"[{args.tag}] window={N}d seeds={seeds} horizons={horizons} "
          f"n_samples={args.n_samples} n_iters={args.n_iters} start={TEST_START}", flush=True)

    for s in seeds:
        cfg_s = pc.cfg_for(test_scen, seed=s)
        # rule_based reference on the SAME window/seed
        t0 = time.time()
        try:
            df = U.rollout_rule_based(cfg_s, n_days=N, start_date=TEST_START, noise_scale=0.0, seed=s)
            m = U.epi_metrics(df, corridors=CORR, prices=PRICES)
            records.append(_row("rule_based", s, 0, m, time.time() - t0))
            _flush()
            print(f"[{args.tag}] seed {s} rule_based EPI={m.get('epi'):.3f} "
                  f"viol={m.get('violation_steps_total')} ({records[-1]['secs']}s)", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[{args.tag}] seed {s} rule_based FAILED {type(exc).__name__}: {str(exc)[:160]}", flush=True)

        for H in horizons:
            t0 = time.time()
            try:
                df = U.rollout_oracle_mpc(cfg_s, n_days=N, start_date=TEST_START, horizon=H,
                                          n_samples=args.n_samples, n_iters=args.n_iters)
                m = U.epi_metrics(df, corridors=CORR, prices=PRICES)
                secs = time.time() - t0
                records.append(_row("oracle_mpc", s, H, m, secs))
                _flush()
                sps = secs / max(1, int(m.get("steps") or 0))
                print(f"[{args.tag}] seed {s} oracle H={H} ({H*pc.period/3600.0:.0f}h) "
                      f"EPI={m.get('epi'):.3f} viol={m.get('violation_steps_total')} "
                      f"({secs:.0f}s, {sps:.2f}s/step)", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[{args.tag}] seed {s} oracle H={H} FAILED {type(exc).__name__}: {str(exc)[:160]}", flush=True)

    _flush()
    print(f"[{args.tag}] DONE wrote {out} ({len(records)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
