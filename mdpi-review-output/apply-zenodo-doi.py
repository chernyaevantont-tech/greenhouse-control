"""Fill the two DOI placeholders in the revised manuscript once the Zenodo deposit exists.

    python mdpi-review-output/apply-zenodo-doi.py 10.5281/zenodo.XXXXXXX

Both placeholders take the same DOI: the Data Availability Statement needs a public,
citable location for the result tree, and the Methods pre-registration pointer needs a
link to the archived analysis plan. They are the same archive.

Before running this, make sure the plan is actually in the archive. It is not, yet:
own-article/regen/make_archive.py lists PARENT_MODULES = ("article_experiment_utils.py",
"protocol_config.py", "rostov_soil.py", "make_weather.py") and EXPERIMENT_PROTOCOL.md is
not among them, so the deposited zip contains no copy of the pre-registration. Add it,
rebuild the archive, then deposit, then run this.

The script edits the five section files and the assembled manuscript, prints what it
changed, and leaves the .docx to be rebuilt afterwards.
"""
import re
import sys
from pathlib import Path

REVISED = Path(__file__).resolve().parent / "manuscript-revised"
FILES = ["01-introduction.tex", "02-methods.tex", "03-results.tex",
         "04-discussion.tex", "05-conclusions-abstract.tex", "paper_en_revised.tex"]

# MDPI's recommended wording for data in a public repository.
DAS = ("The original data presented in the study are openly available in Zenodo at "
       "\\url{{https://doi.org/{doi}}}.")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    doi = sys.argv[1].strip().removeprefix("https://doi.org/").strip("/")
    if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
        print(f"that does not look like a DOI: {doi!r}", file=sys.stderr)
        return 2

    prereg = ("\\url{https://doi.org/%s}" % doi)
    total = 0
    for name in FILES:
        p = REVISED / name
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        before = s

        # Methods: the pre-registration pointer
        s = s.replace(
            "(\\textcolor{red}{[[ARCHIVE DOI REQUIRED, see Data Availability]]})",
            "(%s)" % prereg)

        # Data Availability: the whole red block, however it is line-wrapped.
        # The replacement goes through a lambda: it contains \u of \url, which
        # re.sub would otherwise read as an escape sequence.
        s = re.sub(r"\\textcolor\{red\}\{\[\[REQUIRED BEFORE SUBMISSION:.*?\]\]\}",
                   lambda _m: DAS.format(doi=doi), s, flags=re.S)

        if s != before:
            p.write_text(s, encoding="utf-8", newline="\n")
            total += 1
            print(f"  updated {name}")

    left = sum(len(re.findall(r"\[\[", (REVISED / f).read_text(encoding="utf-8")))
               for f in FILES if (REVISED / f).exists())
    print(f"\n{total} file(s) updated; {left} '[[' placeholder(s) remain")
    print("\nnext:")
    print("  cd mdpi-review-output/manuscript-revised && python make_docx.py && python format_mdpi_docx.py")
    print("  python mdpi-review-output/verify-revised.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
