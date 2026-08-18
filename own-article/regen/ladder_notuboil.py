"""Open-loop ladder arm for the 17-feature ``physics_no_tuboil`` library.

The closed-loop wave measured EPI and boiler-term survival; the manuscript's
Table ``tab:survival3`` also quotes one kappa, rollout RMSE and divergence per
library from the ladder.  This fills those three columns for the new row:
20 seeds x {stlsq, ensemble} at degree 1, no denoise, the canonical rollout
horizons -- the same recipe slice the ladder cells use.

Writes ``results/notuboil/ladder_notuboil.csv`` (incremental, resumable).

Run:  ../.venv-regen/Scripts/python.exe ladder_notuboil.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import regen_config as C          # noqa: E402
import run_regen as R             # noqa: E402
import experiments_support as ES  # noqa: E402

OUT = HERE / "results" / "notuboil" / "ladder_notuboil.csv"


def main() -> None:
    pc = C.protocol(fast=False)
    rows: list[dict] = []
    done = set()
    if OUT.exists():
        prev = pd.read_csv(OUT)
        done = set(zip(prev.seed, prev.optimizer))
        rows = prev.to_dict("records")
        print(f"resuming: {len(done)} fits already in {OUT.name}")
    for s in C.SEEDS:
        train = C.build_train_dataset(pc, seed=s)
        for opt in ("stlsq", "ensemble"):
            if (s, opt) in done:
                continue
            rec = {"feature_variant": "physics_no_tuboil", "library_degree": 1,
                   "optimizer": opt, "denoise": "none",
                   "threshold": C.CONFIRMATORY["threshold"]}
            t0 = time.time()
            b = R.fit_sindy_seeded(train, pc, seed=s, label=f"ntb/d1/{opt}/none",
                                   recipe=rec)
            row = {"variant": "physics_no_tuboil", "seed": s, "optimizer": opt,
                   "degree": 1, "denoise": "none",
                   "kappa": float(b.condition_number),
                   "nonzero": int((b.model.coefficients() != 0).sum()),
                   "secs": round(time.time() - t0, 1)}
            row.update(ES._openloop_stability(b, train, C.LADDER_ROLLOUT_HORIZONS_STEPS))
            rows.append(row)
            pd.DataFrame(rows).to_csv(OUT, index=False)
            print(f"seed {s:>2} {opt:>9} kappa={row['kappa']:.2f} "
                  f"rollout={row.get('rollout_rmse_t_in', float('nan')):.3f} "
                  f"div={row.get('diverged_frac', float('nan')):.4f}")
    print(f"DONE -> {OUT}")


if __name__ == "__main__":
    main()
