"""Write regen/results/final/NUMBERS.md: every quantity the manuscript states, the value
recomputed from the results tree, and the files it is computed from.

    python make_numbers_md.py            # runs verify_tables + verify_prose, writes the map
    python make_numbers_md.py --dry-run  # print instead of writing

The map is built from the same checks that gate the build (`verify_manuscript.py`): each
row is one comparison "value printed in the manuscript" against "value recomputed from
regen/results/", grouped by the table or the passage the value appears in. Sources are read
from the table captions of the manuscript and from the loaders each passage's checker calls,
so the map cannot name a file that no check reads.

`make_tables.py` writes its own derived summary to `<out>/tables/SUMMARY.md`; that file
describes the canonical default-objective tree only and is not the manuscript's claim map.
"""
from __future__ import annotations

import ast
import datetime as dt
import inspect
import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "figures"))
import _plotstyle as ps  # noqa: E402
import verify_prose as vp  # noqa: E402
import verify_tables as vt  # noqa: E402

OUT = ps.RESULTS / "final" / "NUMBERS.md"
TEX = vt.TEX

# --------------------------------------------------------------------------------------
# Sources: which files each loader reads (parsed from _plotstyle, not retyped)
# --------------------------------------------------------------------------------------

def loader_sources() -> dict[str, list[str]]:
    """``load_xxx`` -> the glob patterns it passes to load_runs / _read_many."""
    src = Path(ps.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    out: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        pats: list[str] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and getattr(sub.func, "id", "") in ("load_runs", "_read_many"):
                for arg in sub.args[:1]:
                    for c in ast.walk(arg):
                        if isinstance(c, ast.Constant) and isinstance(c.value, str) and ".csv" in c.value:
                            pats.append(c.value)
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value.endswith(".csv") \
                    and "/" in sub.value and sub.value not in pats:
                pats.append(sub.value)
        if pats:
            out[node.name] = sorted(set(pats))
    # composites
    out.setdefault("load_library_pool", []).extend(out.get("load_priced_pool", []) + out.get("load_physlib_pool", []))
    for fn in ("library_one_factor", "boiler_coefficients", "boiler_survival"):
        out.setdefault(fn, []).extend(out["load_library_pool"])
    out.setdefault("load_notuboil_pool", [])
    for fn in ("lambda_sweep", "knock_effects"):
        out.setdefault(fn, []).extend(out.get("load_mechanism", []))
    out.setdefault("coef_perturbation", []).extend(out.get("load_design", []))
    out["full_pool"] = sorted(set(out["load_library_pool"] + out.get("load_default_main", [])
                                  + out.get("load_heuristic_tuning", [])))
    out["price_grid"] = sorted(set(out.get("price_grid", []) + out.get("load_default_main", [])))
    return {k: sorted(set(v)) for k, v in out.items()}


LOADERS = loader_sources()
CODE_FILES = {
    "regen_config": "regen/regen_config.py", "experiments_support": "regen/experiments_support.py",
    "article_experiment_utils": "article_experiment_utils.py", "protocol_config": "protocol_config.py",
    "make_weather": "make_weather.py",
}


def passage_sources(fn) -> list[str]:
    """Files a prose checker reads: loaders it calls, explicit CSV paths, code it parses."""
    src = inspect.getsource(fn)
    found: set[str] = set()
    for name in re.findall(r"ps\.(\w+)\(", src):
        found.update(LOADERS.get(name, []))
    if "full_pool(" in src:
        found.update(LOADERS["full_pool"])
    for parts in re.findall(r'RESULTS\s*/\s*((?:"[^"]+"\s*/\s*)*"[^"]+\.csv")', src):
        found.add("/".join(re.findall(r'"([^"]+)"', parts)))
    # RESULTS / "dir" / <variable>: the directory is known, the file name is computed
    for parts in re.findall(r'RESULTS\s*/\s*((?:"[^"]+"\s*/\s*)+)(?=[a-z_]\w*\b)', src):
        found.add("/".join(re.findall(r'"([^"]+)"', parts)) + "/*.csv")
    for pat in re.findall(r'glob\(["\']([^"\']+\.csv)["\']', src):
        found.add(pat)
    if "regen_manifest.json" in src:
        found.add("*/regen_manifest.json")
    for key, path in CODE_FILES.items():
        if key in src:
            found.add(path)
    return sorted(found)


# --------------------------------------------------------------------------------------
# Manuscript side: table order, captions, caption sources, passage sections
# --------------------------------------------------------------------------------------

#: Tables whose caption names no file; the sources of their provenance comments.
EXTRA_SOURCES = {
    "tab:defects": ["n2_tune/tune_rb_n2.csv", "priced_main/*.csv", "priced_dagger/*.csv",
                    "final/main.csv", "n7/main_n7.csv", "ladder_rerun/ladder_rerun*.csv"],
    "tab:wilcoxon": ["priced_main/*.csv", "priced_dagger/*.csv", "phys_lib/main_physlib.csv",
                     "final/main.csv", "n2_tune/tune_rb_n2.csv"],
    "tab:disc-libraries": ["holdout/holdout_holdout.csv"],
    "tab:disc-defects": ["n2_tune/tune_rb_n2.csv", "priced_main/*.csv", "priced_dagger/*.csv",
                         "final/main.csv", "n7/main_n7.csv"],
}


def table_index() -> dict[str, tuple[int, str, list[str]]]:
    """label -> (table number, first sentence of the caption, sources named in the block)."""
    tex = TEX.read_text(encoding="utf-8")
    out = {}
    for n, block in enumerate(re.findall(r"\\begin\{table\}(.*?)\\end\{table\}", tex, re.S), 1):
        m = re.search(r"\\label\{(tab:[^}]*)\}", block)
        if not m:
            continue
        cap = re.search(r"\\caption\{(.*?)\}\s*\\label", block, re.S)
        caption = " ".join((cap.group(1) if cap else "").split())
        caption = re.sub(r"\\texttt\{([^}]*)\}", r"\1", caption)
        caption = (caption.replace("\\pm", "±").replace("\\times", "×").replace("\\,", " ")
                   .replace("--", "–").replace("\\_", "_"))
        caption = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", "", caption)
        caption = re.sub(r"\s+", " ", caption.replace("$", "").replace("^", "")
                         .replace("{", "").replace("}", ""))
        first = re.split(r"(?<=[a-z0-9)])\.\s", caption, maxsplit=1)[0].strip().rstrip(".")
        srcs = set()
        for s in re.findall(r"\\texttt\{([^}]*(?:\.csv|/)[^}]*)\}", block):
            s = s.replace("\\_", "_").replace("\\allowbreak", "").replace(" ", "")
            if "regen/results/" in s:
                s = s.split("regen/results/", 1)[1]
            if s and s not in ("own-article/regen/results/",):
                srcs.add(s.rstrip("."))
        for line in block.splitlines():
            if line.lstrip().startswith("%%"):
                for s in re.findall(r"regen/results/([\w/*.\-]+)", line):
                    srcs.add(s.rstrip("."))
        out[m.group(1)] = (n, first.replace("\\_", "_"),
                           sorted(srcs) or EXTRA_SOURCES.get(m.group(1), []))
    return out


def passage_sections() -> dict[str, str]:
    """passage name -> the '# Section ...' header above its @passage decorator."""
    src = Path(vp.__file__).read_text(encoding="utf-8").splitlines()
    out, last, after_rule = {}, "", False
    for line in src:
        t = line.strip()
        if re.match(r"# -{10,}$", t):
            after_rule = True
            continue
        if after_rule and t.startswith("# "):
            # section numbers in these headers drift with the manuscript; keep the words only
            last = re.sub(r"^Section [\d.]+\s*--\s*", "", t[2:]).strip()
        after_rule = False
        p = re.match(r'@passage\("([^"]+)"\)', t)
        if p:
            out[p.group(1)] = last or p.group(1)
    return out


# --------------------------------------------------------------------------------------

def run_checks() -> int:
    """Run both check sets; return how many results the table checks contributed."""
    vt.RESULTS.clear()
    with redirect_stdout(io.StringIO()):
        for fn in vt.CHECKS.values():
            fn()
        n_tab = len(vt.RESULTS)
        for fn in vp.CHECKS.values():
            fn()
    return n_tab


def fmt(v: float) -> str:
    if v != v:
        return "n/a"
    a = abs(v)
    if a != 0 and (a < 1e-3 or a >= 1e6):
        return f"{v:.3g}"
    if a >= 1000:
        return f"{v:,.4g}".replace(",", " ")
    return f"{v:.4g}"


def build() -> str:
    n_tab = run_checks()
    results = list(vt.RESULTS)
    tables = table_index()
    sections = passage_sections()
    n_prose = len(results) - n_tab
    n_bad = sum(1 for r in results if not r[4])
    man = ps.RESULTS / "final" / "regen_manifest.json"
    cfg = re.search(r'"config_hash":\s*"([0-9a-f]+)"', man.read_text(encoding="utf-8")).group(1) if man.exists() else "n/a"

    lines = [
        "# NUMBERS — every quantity the manuscript states, recomputed, with its source",
        "",
        f"Generated {dt.date.today().isoformat()} by `paper/en/make_numbers_md.py` from the checks that gate "
        f"the manuscript build (`verify_tables.py`, `verify_prose.py`): {n_tab} table cells and {n_prose} "
        f"values in the running text, each compared with the value recomputed from this tree at half a "
        f"unit in the last printed digit. Mismatches at generation time: {n_bad}. Configuration hash of "
        f"every wave read: `{cfg}`.",
        "",
        "Each block names the files the values are computed from, relative to `regen/results/`. The "
        "loaders behind every recomputation (`figures/_plotstyle.py`) apply one deduplication key, "
        "(method or block, seed, test year), and one exclusion rule, solver-aborted seasons, before any "
        "average is taken.",
        "",
        "`tables/SUMMARY.md` is a different file: the derived summary of the canonical default-objective "
        "tree written by `make_tables.py`. It is not the manuscript's claim map.",
        "",
        "## Tables",
        "",
    ]
    by_label: dict[str, list] = {}
    for r in results:
        by_label.setdefault(r[0], []).append(r)
    for label, (num, caption, srcs) in sorted(tables.items(), key=lambda kv: kv[1][0]):
        rows = by_label.get(label, [])
        lines += [f"### Table {num} — {caption} (`{label}`)", ""]
        lines.append("Sources: " + (", ".join(f"`{s}`" for s in srcs) if srcs else "see the row descriptions") + ".")
        lines += ["", f"{len(rows)} cells verified.", "", "| Quantity | Manuscript | Recomputed |", "|---|---|---|"]
        for _, what, got, want, ok in rows:
            flag = "" if ok else " **MISMATCH**"
            lines.append(f"| {what} | {fmt(want)} | {fmt(got)}{flag} |")
        lines.append("")
    lines += ["## Running text", ""]
    for name in vp.CHECKS:
        rows = by_label.get(name, [])
        if not rows:
            continue
        srcs = passage_sources(vp.CHECKS[name])
        lines += [f"### {sections.get(name, name)} (passage `{name}`)", ""]
        lines.append("Sources: " + (", ".join(f"`{s}`" for s in srcs) if srcs else "the manuscript's own configuration constants") + ".")
        lines += ["", "| Quantity | Manuscript | Recomputed |", "|---|---|---|"]
        for _, what, got, want, ok in rows:
            flag = "" if ok else " **MISMATCH**"
            lines.append(f"| {what} | {fmt(want)} | {fmt(got)}{flag} |")
        lines.append("")
    lines += ["## Regenerating", "",
              "The per-run tables are regenerated with `python run_regen.py --experiment <block> --seeds 0-19 "
              "--out <dir>` followed by `python run_regen.py --merge --out <dir>`; `python make_tables.py --out "
              "<dir>` rebuilds the derived tables and `tables/SUMMARY.md`; `python verify_regen.py --out <dir>` "
              "applies the acceptance gates. The comparisons above are re-run from the project repository, "
              "where the manuscript source lives, with `python paper/en/verify_manuscript.py`.", ""]
    return "\n".join(lines)


def main() -> int:
    text = build()
    if "--dry-run" in sys.argv:
        print(text[:6000])
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
