from __future__ import annotations

import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient


NOTEBOOKS = [
    "00_data_collection.ipynb",
    "01_sindy_feature_ablation.ipynb",
    "02_closed_loop_mpc_benchmark.ipynb",
    "03_dagger_dataset_aggregation.ipynb",
    "04_interpretability_and_equations.ipynb",
    "05_cross_season_generalization.ipynb",
]


def main() -> int:
    root = Path(__file__).resolve().parent
    for name in NOTEBOOKS:
        path = root / name
        print(f"\n=== Executing {name} ===", flush=True)
        started = time.time()
        nb = nbformat.read(path, as_version=4)
        client = NotebookClient(
            nb,
            timeout=3600,
            kernel_name="python3",
            resources={"metadata": {"path": str(root)}},
            allow_errors=False,
        )
        try:
            client.execute()
        except Exception:
            nbformat.write(nb, path)
            print(f"FAILED {name}; executed notebook saved with outputs.", flush=True)
            raise
        nbformat.write(nb, path)
        print(f"OK {name} in {time.time() - started:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
