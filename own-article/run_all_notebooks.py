"""Execute the protocol notebooks E0-E3 in order with nbclient.

Usage:
    python run_all_notebooks.py            # FAST_MODE smoke (tiny data)
    ARTICLE_FAST=0 python run_all_notebooks.py   # article-grade full run

FAST_MODE is read by each notebook from the ARTICLE_FAST env var (default "1").
The executed notebooks are written back in place with their outputs.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient


NOTEBOOKS = [
    "E0_canonical_setup_and_metrics.ipynb",
    "E1_data_and_scenarios.ipynb",
    "E2_identification_ladder.ipynb",
    "E3_closed_loop_benchmark.ipynb",
]


def main() -> int:
    root = Path(__file__).resolve().parent
    fast = os.environ.get("ARTICLE_FAST", "1")
    only = sys.argv[1:] or NOTEBOOKS
    print(f"ARTICLE_FAST={fast} | notebooks={only}", flush=True)
    for name in only:
        path = root / name
        print(f"\n=== Executing {name} ===", flush=True)
        started = time.time()
        nb = nbformat.read(path, as_version=4)
        client = NotebookClient(
            nb,
            timeout=36000,
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
