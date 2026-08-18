"""Condition number of the 17-feature ``physics_no_tuboil`` library.

The closed-loop wave (``results/notuboil/``) never recorded kappa.  The
manuscript's Table ``tab:survival3`` quotes one kappa per library, so the new
row needs it.  Kappa is a property of the feature matrix -- in the ladder it is
identical across the 20 seeds and both sparse estimators to three decimals --
so one seed's training data is enough, with the other three libraries fitted
alongside as a check against the canonical 8.21 / 24.52 / 53.43.

Run:  ../.venv-regen/Scripts/python.exe kappa_notuboil.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import regen_config as C  # noqa: E402
import run_regen as R     # noqa: E402

SEED = 0


def main() -> None:
    pc = C.protocol(fast=False)
    train = C.build_train_dataset(pc, seed=SEED)
    print(f"train dataset built: seed {SEED}")
    for variant in ("raw", "physics_no_cross", "physics", "physics_no_tuboil"):
        for opt in ("stlsq", "ensemble"):
            rec = {"feature_variant": variant, "library_degree": 1,
                   "optimizer": opt, "denoise": "none",
                   "threshold": C.CONFIRMATORY["threshold"]}
            b = R.fit_sindy_seeded(train, pc, seed=SEED,
                                   label=f"{variant}/d1/{opt}/none", recipe=rec)
            print(f"{variant:>18} {opt:>9}  kappa={b.condition_number:.2f}  "
                  f"nonzero={int((b.model.coefficients() != 0).sum())}")


if __name__ == "__main__":
    main()
