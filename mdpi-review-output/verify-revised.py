"""Run the project's own numeric gate against the REVISED manuscript.

    python mdpi-review-output/verify-revised.py

The checkers resolve the repository as ``paper/en/figures``.parents[2], so they only
run from a directory at that depth. This script stages the revised manuscript in a
temporary sibling of ``own-article/paper/en``, runs the gate there, prints the result
and removes the staging directory. Nothing under ``own-article/paper/en`` is touched.

Exit code is the gate's own: 0 when every printed number agrees with the
regeneration tree and every printed number is accounted for by a check.
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "own-article" / "paper" / "en"
REVISED = REPO / "mdpi-review-output" / "manuscript-revised" / "paper_en_revised.tex"
STAGE = REPO / "own-article" / "paper" / "_verify_revised"


def main() -> int:
    if not REVISED.exists():
        print(f"revised manuscript not found: {REVISED}", file=sys.stderr)
        return 2
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    try:
        # A checker that anchors on a sentence must move with that sentence.
        # Where mdpi-review-output/manuscript-revised/ ships a patched checker,
        # it wins over the one in own-article/paper/en/.
        patched = REVISED.parent
        for name in ("verify_manuscript.py", "verify_tables.py",
                     "verify_prose.py", "verify_paper_en.py"):
            src = patched / name if (patched / name).exists() else SRC / name
            shutil.copy2(src, STAGE / name)
        shutil.copytree(SRC / "figures", STAGE / "figures")
        shutil.copy2(REVISED, STAGE / "paper_en.tex")

        args = [sys.executable, "verify_manuscript.py", *sys.argv[1:]]
        print(f"running: {' '.join(args)}\n  in {STAGE}\n")
        return subprocess.run(args, cwd=STAGE).returncode
    finally:
        shutil.rmtree(STAGE, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
