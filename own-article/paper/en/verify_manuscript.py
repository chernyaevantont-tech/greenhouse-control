"""Run both verifiers and gate on COVERAGE as well as on agreement.

`verify_tables.py` and `verify_prose.py` fail when a recomputed value disagrees with the
manuscript. Neither notices a number that no checker ever asks about -- and a silent skip
looks exactly like a pass. Three columns went unverified that way for two full passes: the
active-term column of the sparsity table, the training-score row of the setpoint search,
and the raw-minus-physics gap quoted in three tables.

This runs both suites and then walks every number the manuscript prints, in tables and in
running text alike, and fails if any of them was never claimed by a check. A number may be
left unclaimed only by appearing in EXEMPT below, with a reason -- so an exemption is a
visible decision rather than an oversight.

    python verify_manuscript.py             # agreement and coverage
    python verify_manuscript.py --list      # what is exempt, and why
    python verify_manuscript.py --self-test # that the gate can still fail

Exit code 0 only when every value agrees and every printed number is accounted for.
"""
from __future__ import annotations

import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "figures"))

import verify_tables as vt  # noqa: E402
import verify_prose as vp  # noqa: E402

TEX = vt.TEX

# ---------------------------------------------------------------------------
# What may go unclaimed, and why
# ---------------------------------------------------------------------------
#
# Every entry is a number the manuscript prints that no recomputation can reach, because it
# is not derived from the results tree. Anything else that turns up unclaimed is a gap in
# the checking, not a fact about the manuscript, and fails the run.

EXEMPT: tuple[tuple[str, str], ...] = (
    (r"^20(1[4-9]|2[0-3])$",
     "a season, used as a column header or a range endpoint, not a measurement"),
    (r"^0000-\d|^0009-\d|^0000$|^0009$",
     "an ORCID, supplied by the author and verifiable only against the ORCID registry"),
    (r"^344003$", "the postal code of the affiliation address"),
    (r"^075$|^15$|^2025$|^592$",
     "the funding agreement number 075-15-2025-592, a document identifier"),
    (r"^1$",
     "the street number of the affiliation, and the numerator of stated ratios such as"
     " 1:2.97:0.46, whose two informative terms are checked"),
    (r"^24$", "the day of the funding agreement's date"),
)


def exemption(token: str) -> str | None:
    for pattern, reason in EXEMPT:
        if re.match(pattern, token):
            return reason
    return None


# ---------------------------------------------------------------------------
# What the manuscript prints
# ---------------------------------------------------------------------------

_SCI = re.compile(r"([-+]?\d+(?:\.\d+)?)\s*\\times\s*10\^\{([-+]?\d+)\}")
_TOKEN = re.compile(r"(?<![\w.\-])([-+]?\d+(?:\.\d+)?)(?![\w.])")


def _collapse(text: str) -> str:
    """Fold `6.9\\times10^{-11}` into a single token, so a mantissa is not read alone."""
    return _SCI.sub(lambda m: f"{float(m.group(1)) * 10 ** int(m.group(2)):.12g}", text)


def _strip_layout(text: str) -> str:
    """Remove the parts of LaTeX that carry numbers which are not claims."""
    text = re.sub(r"(?m)^%%.*$", "", text)
    text = re.sub(r"\\cite\{[^}]*\}|\\ref\{[^}]*\}|\\label\{[^}]*\}", " ", text)
    text = re.sub(r"\\includegraphics[^\n]*|\\bibitem\{[^}]*\}", " ", text)
    text = re.sub(r"p\{[\d.]+\\textwidth\}|\{@\{\}[^}]*@\{\}\}", " ", text)
    text = re.sub(r"\\(?:toprule|midrule|bottomrule|addlinespace|cmidrule)[^\s]*", " ", text)
    text = re.sub(r"\\multicolumn\{\d+\}|\\begin\{[^}]*\}|\\end\{[^}]*\}", " ", text)
    text = re.sub(r"\\(?:sub)*section\*?\{|\\vspace\{[^}]*\}|\\setlength[^\n]*", " ", text)
    return text


def regions() -> list[tuple[str, str]]:
    """The manuscript, split into the sixteen tables and the running text around them."""
    tex = TEX.read_text(encoding="utf-8").split(r"\begin{thebibliography}")[0]
    out, prose = [], tex
    for block in re.findall(r"\\begin\{table\}.*?\\end\{table\}", tex, re.S):
        m = re.search(r"\\label\{(tab:[^}]*)\}", block)
        if m:
            out.append((m.group(1), block))
        prose = prose.replace(block, " ")
    out.append(("prose", prose))
    return out


def tokens_of(text: str) -> list[str]:
    return _TOKEN.findall(_collapse(_strip_layout(text)))


# ---------------------------------------------------------------------------
# What the checks claimed
# ---------------------------------------------------------------------------

def claimed() -> set[str]:
    """Every value a check compared against, rendered at each plausible precision."""
    out: set[str] = set()
    for _, _, _, want, _ in vt.RESULTS:
        if want != want:                                    # a checker that errored
            continue
        for nd in range(0, 7):
            out.add(f"{want:.{nd}f}")
            out.add(f"{-want:.{nd}f}")
        out.add(f"{want:.12g}")
        out.add(f"{-want:.12g}")
    return out


def unclaimed(text: str, seen: set[str]) -> list[str]:
    missing = []
    for tok in tokens_of(text):
        bare = tok.lstrip("+")
        if bare in seen or tok in seen or exemption(bare):
            continue
        missing.append(tok)
    return missing


# ---------------------------------------------------------------------------

def self_test() -> int:
    """Prove the gate can fail, and that no checker is inert.

    A gate that has never fired is indistinguishable from no gate. This disables each table
    checker in turn and re-runs the coverage walk, reporting how many numbers only that
    checker accounts for.

    Two summary tables contribute no unique coverage and that is correct: every number in
    them restates one verified elsewhere. They still contribute agreement -- each compares
    its own printed cell against the tree, which is how a summary drifting out of step with
    the section it summarises gets caught.

    The failure worth having is a checker that compares NOTHING, which is the shape a
    silently skipped column takes: it looks like a pass from the outside.
    """
    print("self-test: disabling one checker at a time\n")
    inert, unique = [], {}
    for dropped in sorted(vt.CHECKS):
        vt.RESULTS.clear()
        with redirect_stdout(io.StringIO()):
            for label, fn in vt.CHECKS.items():
                if label == dropped:
                    continue
                try:
                    fn()
                except Exception:
                    pass
            for fn in vp.CHECKS.values():
                try:
                    fn()
                except Exception:
                    pass
        seen = claimed()
        unique[dropped] = sum(len(unclaimed(text, seen)) for _, text in regions())

    vt.RESULTS.clear()
    with redirect_stdout(io.StringIO()):
        for label, fn in list(vt.CHECKS.items()) + [(k, v) for k, v in vp.CHECKS.items()]:
            before = len(vt.RESULTS)
            try:
                fn()
            except Exception:
                pass
            if len(vt.RESULTS) == before:
                inert.append(label)

    for name in sorted(unique):
        n = unique[name]
        note = "" if n else "   (a summary: every number restates a verified one)"
        print(f"  [{'ok  ' if n else 'none'}] without {name:22s} {n:4d} numbers "
              f"go unclaimed{note}")

    print("\n" + "=" * 96)
    if inert:
        print("these checkers compared nothing at all: " + ", ".join(inert))
        print("a checker that claims nothing is a silent skip wearing a pass.")
        return 1
    covering = sum(1 for n in unique.values() if n)
    print(f"{covering} of {len(unique)} table checkers account for numbers no other check "
          f"reaches;")
    print("the rest are summaries, and every checker compares at least one value.")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if "--list" in sys.argv:
        print("Numbers the manuscript prints that no recomputation can reach:\n")
        for pattern, reason in EXEMPT:
            print(f"  {pattern:28s} {reason}")
        return 0

    print("running the table checks ...")
    with redirect_stdout(io.StringIO()):
        for fn in vt.CHECKS.values():
            try:
                fn()
            except Exception as exc:                        # noqa: BLE001
                vt.RESULTS.append(("tables", f"checker error: {exc}",
                                   float("nan"), float("nan"), False))
    n_tables = len(vt.RESULTS)

    print("running the prose checks ...")
    with redirect_stdout(io.StringIO()):
        for fn in vp.CHECKS.values():
            try:
                fn()
            except Exception as exc:                        # noqa: BLE001
                vt.RESULTS.append(("prose", f"checker error: {exc}",
                                   float("nan"), float("nan"), False))
    n_prose = len(vt.RESULTS) - n_tables

    bad = [r for r in vt.RESULTS if not r[4]]
    seen = claimed()

    print("\nchecking that every printed number was claimed by a check ...\n")
    gaps: list[tuple[str, list[str]]] = []
    total = 0
    for label, text in regions():
        toks = tokens_of(text)
        total += len(toks)
        miss = unclaimed(text, seen)
        if miss:
            gaps.append((label, miss))
        mark = "ok  " if not miss else "GAP "
        print(f"  [{mark}] {label:22s} {len(toks):4d} numbers, {len(miss):3d} unclaimed")

    print("\n" + "=" * 96)
    print(f"recomputed {n_tables} table cells and {n_prose} prose values against the tree")
    print(f"walked {total} printed numbers; {sum(len(m) for _, m in gaps)} unclaimed")

    for label, what, got, want, ok in vt.RESULTS:
        if not ok:
            print(f"   ! MISMATCH {label} {what}: tree {got:.6g} vs paper {want:.6g}")
    for label, miss in gaps:
        shown = " ".join(sorted(set(miss))[:16])
        print(f"   ! UNCLAIMED {label}: {shown}")

    if not bad and not gaps:
        print("\nevery value agrees, and every printed number is accounted for.")
        return 0
    if gaps:
        print("\nAn unclaimed number is a hole in the checking, not a fact about the")
        print("manuscript: write a check for it, or add it to EXEMPT with a reason.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
