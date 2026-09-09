"""Build the deposit archive from this tree, so its contents are declared, not remembered.

    python make_archive.py [--out ../../greenhouse-control-regen-data-v1.0.zip]

What goes in: every script, every Markdown note, every result CSV, every
`regen_manifest.json` (the provenance record the manuscript's Data Availability statement
points at), the frozen recipe, and `results/final/VERIFY.txt`, the recorded output of the
acceptance gates.

What stays out, and why: `log_*.txt` (a megabyte of per-shard run logs that duplicate what
the CSVs already record), `k8s/` and `submit.sh` (infrastructure for one Kubernetes cluster,
not a dependency of the results), and caches. Excluding them is a choice, so it is written
down here rather than performed by hand.

The archive is deterministic: entries are sorted, and each carries a fixed timestamp, so
rebuilding it from an unchanged tree gives a byte-identical file.
"""
from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parents[1] / "greenhouse-control-regen-data-v1.0.zip"

#: Everything with these suffixes is included, unless excluded below.
KEEP_SUFFIXES = {".py", ".md", ".csv", ".json"}
#: Individually named files that are kept despite their suffix.
KEEP_NAMES = {"VERIFY.txt"}
#: Directories never included.
SKIP_DIRS = {"__pycache__", ".ruff_cache", "k8s", ".ipynb_checkpoints"}
#: A fixed DOS timestamp (2026-01-01 00:00:00) so the zip does not change on rebuild.
FIXED_DATE = (2026, 1, 1, 0, 0, 0)

#: Modules that live one directory up and that this package cannot run without:
#: regen_config puts that directory on sys.path and imports the first two, and
#: article_experiment_utils loads rostov_soil by path. They go to the archive root, so the
#: extracted layout is the one the code expects. make_weather.py is the reconstructed
#: generator for the ERA5-derived inputs -- without it "regenerate from data collection
#: upward" is not something a reader can do.
PARENT_MODULES = ("article_experiment_utils.py", "protocol_config.py",
                  "rostov_soil.py", "make_weather.py")

#: The figure layer, shipped as `figures/` beside `regen/`. `_plotstyle` owns the dedup key
#: and the solver-abort rule -- how a CSV becomes a number reported in the paper -- and
#: `analyze_notuboil` imports it. The six make_figN.py scripts are included with it, so the
#: figures are reproducible from this archive and not only from the repository.
FIGURE_DIR = Path("paper") / "en" / "figures"
FIGURE_FILES = ("_plotstyle.py", "make_fig1.py", "make_fig2.py", "make_fig3.py",
                "make_fig4.py", "make_fig5.py", "make_fig6.py", "SPEC.md")


def selected(root: Path) -> list[Path]:
    out = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if SKIP_DIRS & set(path.relative_to(root).parts):
            continue
        if path.name.startswith("log_"):
            continue
        if path.suffix.lower() in KEEP_SUFFIXES or path.name in KEEP_NAMES:
            out.append(path)
    return out


def build(out_path: Path) -> int:
    readme = HERE / "ARCHIVE_README.txt"
    files = selected(HERE)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo("README.txt", date_time=FIXED_DATE)
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, readme.read_bytes())
        for name in PARENT_MODULES:
            src = HERE.parent / name
            if not src.exists():
                raise FileNotFoundError(f"{src} is required by the package and is missing")
            info = zipfile.ZipInfo(name, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, src.read_bytes())
        for name in FIGURE_FILES:
            src = HERE.parent / FIGURE_DIR / name
            if not src.exists():
                raise FileNotFoundError(f"{src} is referenced by the package and is missing")
            info = zipfile.ZipInfo(f"figures/{name}", date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, src.read_bytes())
        for path in files:
            arcname = "regen/" + path.relative_to(HERE).as_posix()
            if arcname == "regen/ARCHIVE_README.txt":
                continue
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())

    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    with zipfile.ZipFile(out_path) as z:
        names = z.namelist()
    counts: dict[str, int] = {}
    for n in names:
        counts[Path(n).suffix or "(none)"] = counts.get(Path(n).suffix or "(none)", 0) + 1
    print(f"wrote {out_path} ({out_path.stat().st_size / 1e6:.2f} MB, {len(names)} entries)")
    for suffix, count in sorted(counts.items()):
        print(f"  {suffix:6s} {count}")
    print(f"sha256 {digest}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    return build(Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
