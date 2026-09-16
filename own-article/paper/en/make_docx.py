"""Regenerate own-article/paper/en/paper_en.docx from paper_en.tex via pandoc.

Conversion-only adaptations (the .tex source of truth is NOT modified):
  1. includegraphics .pdf -> .png (docx cannot embed PDF)
  2. \\multicolumn{N}{@{}l} and \\multicolumn{N}{@{}p{..}@{}} -> \\multicolumn{N}{l}
     (pandoc drops tables whose multicolumn spec carries @{} or a p-column;
     the panel rows of tab:headline wrap through a p-column in LaTeX and
     through a spanning cell in Word); \\addlinespace immediately before a
     \\multicolumn row is dropped, because pandoc silently discards that row and
     two tables lost their lower-panel label to it. The vertical gap is cosmetic
     and the label is content, so the gap is what gives way.
  3. \\cite{keys} -> literal [n] / [n,m] / [n-m] (pandoc drops Cite inlines
     without citeproc); numbering follows the \\bibitem order of the file
  4. thebibliography -> \\section*{References} + plain numbered paragraphs
     (pandoc leaks the {99} width argument and adds no heading)
  5. a tabular preamble with a p-column is rewritten so that every column has
     a p{x\\linewidth} width, the only form pandoc turns into column widths:
     p{x\\textwidth} and p{xcm} keep their size, an l/c/r column beside them
     takes the natural width it has in LaTeX (its longest entry), and the
     fractions are normalised to the full width because every Word table of
     the template spans the page. Without this pandoc emits equal columns and
     Word autofits them by content, which squeezed the label columns of the
     four text tables. Tables without a p-column are left to autofit.
  6. the notes under a tabular (\\begin{minipage}\\footnotesize .. or a bare
     \\footnotesize paragraph inside the table float) are wrapped in a
     tablenotes environment; pandoc turns an unknown environment into a Div,
     and a Lua filter maps that Div onto the template's MDPI_4.3_table_footer
     style, so the notes are set as table notes and not as body text.
  7. \\allowbreak inside \\texttt (a break opportunity inside a path) becomes
     a zero-width space, which is what Word breaks at; pandoc drops it.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = r"C:\Users\zergu\repos\greenhouse-control"
TEX = ROOT + r"\own-article\paper\en\paper_en.tex"
OUT = ROOT + r"\own-article\paper\en\paper_en.docx"
REF = ROOT + r"\mdpi-template\agronomy-template.docx"
_PINNED = ROOT + r"\.tools\pandoc-3.10.2\pandoc.exe"
# The pinned tree is gitignored and absent on a clean checkout; fall back to
# the pandoc on PATH (3.10 line) so the pipeline is reproducible from the repo.
PANDOC = _PINNED if os.path.exists(_PINNED) else (shutil.which("pandoc") or _PINNED)

tex = open(TEX, encoding="utf-8").read()

n_pdf = len(re.findall(r"\\includegraphics\[[^\]]*\]\{[^}]*\.pdf\}", tex))
tex = re.sub(r"(\\includegraphics\[[^\]]*\]\{[^}]*)\.pdf\}", r"\1.png}", tex)

_mc = re.compile(r"\\multicolumn\{(\d+)\}\{(?:@\{\})?([lcr]|p\{[^{}]*\})(?:@\{\})?\}")


def mc_repl(m):
    n, spec = m.groups()
    return "\\multicolumn{%s}{%s}" % (n, spec if spec in "lcr" else "l")


n_mc = sum(1 for m in _mc.finditer(tex) if m.group(0) != mc_repl(m))
tex = _mc.sub(mc_repl, tex)

_als = re.compile(r"[ \t]*\\addlinespace[ \t]*\r?\n(?=[ \t]*\\multicolumn)")
n_als = len(_als.findall(tex))
tex = _als.sub("", tex)

# -- 2b: booktabs partial rules --------------------------------------------------
# pandoc does not know \cmidrule(lr){2-5}; it leaks the arguments as literal text
# ("2-5(lr)6-7") into the first cell of the following header row. The rules are
# cosmetic in Word (the template draws its own three-line tables), so they go.
_cmid = re.compile(r"[ \t]*(?:\\cmidrule(?:\([^)]*\))?\{[^}]*\}[ \t]*)+\r?\n")
n_cmid = len(_cmid.findall(tex))
tex = _cmid.sub("", tex)

# -- 5: column widths ---------------------------------------------------------
_tab = re.compile(r"(\\begin\{tabular\}\{)((?:[^{}\n]|\{[^{}\n]*\})*)(\})(.*?)(?=\\end\{tabular\})", re.S)
_coltype = re.compile(r"@\{\}|[lcr]|p\{[^{}]*\}")
TEXTWIDTH_CM = 16.0        # a4paper with margin=2.5cm, as the preamble sets it
CHAR_FRACTION = 0.011      # one character of \small text as a fraction of \textwidth


def natural_widths(body):
    """The width an l/c/r column takes in LaTeX: its longest entry, unwrapped."""
    longest = []
    for row in body.split("\\\\"):
        if "\\multicolumn" in row:
            continue
        cells = [re.sub(r"\\[a-zA-Z]+|[{}$^_]", "", c).strip() for c in row.split("&")]
        cells = [" ".join(c.split()) for c in cells]
        longest.extend([0] * (len(cells) - len(longest)))
        for i, c in enumerate(cells):
            longest[i] = max(longest[i], len(c))
    return [n * CHAR_FRACTION for n in longest]


def width_repl(m):
    """Give pandoc a width for every column when the author fixed at least one.

    The l/c/r columns beside a p-column take their natural width; the fractions
    are then normalised to the full width because every table of the Word
    template spans the page.  Tables without a p-column are left to autofit.
    """
    spec, body = m.group(2), m.group(4)
    cols = [c for c in _coltype.findall(spec) if c != "@{}"]
    if not any(c.startswith("p{") for c in cols):
        return m.group(0)
    natural = natural_widths(body)
    widths = []
    for i, c in enumerate(cols):
        if c.startswith("p{"):
            size = c[2:-1]
            widths.append(float(size[:-len("\\textwidth")]) if size.endswith("\\textwidth")
                          else float(size[:-len("cm")]) / TEXTWIDTH_CM)
        else:
            widths.append(natural[i])
    total = sum(widths)
    new = "".join("p{%.4f\\linewidth}" % (w / total) for w in widths)
    return m.group(1) + new + m.group(3) + m.group(4)


n_width = sum(1 for m in _tab.finditer(tex) if width_repl(m) != m.group(0))
tex = _tab.sub(width_repl, tex)

# -- 6: table notes -----------------------------------------------------------
_notes = re.compile(
    r"\\vspace\{2pt\}\s*"
    r"(?:\\begin\{minipage\}\{\\linewidth\}\\(?:footnotesize|scriptsize)\s*(.*?)\\end\{minipage\}"
    r"|\\footnotesize[ \t]+(.*?)(?=\\end\{table\}))",
    re.S,
)
n_notes = len(_notes.findall(tex))
tex = _notes.sub(lambda m: "\\begin{tablenotes}\n%s\n\\end{tablenotes}\n" % (m.group(1) or m.group(2)).strip(), tex)
assert n_notes == 5, n_notes

TABLENOTES_LUA = """\
function Div(d)
  if d.classes:includes("tablenotes") then
    d.attributes["custom-style"] = "MDPI_4.3_table_footer"
  end
  return d
end
"""

# -- 7: break opportunities inside paths ---------------------------------------
n_brk = len(re.findall(r"\\allowbreak\s*", tex))
tex = re.sub(r"\\allowbreak\s*", "\u200b", tex)

#: Panel labels inside tables, checked against the output at the end.
panel_labels = re.findall(r"\\multicolumn\{\d+\}\{[^}]*\}\{\\emph\{([^{}]*)\}\}", tex)

# -- 3+4: citations and bibliography -----------------------------------------
bib_keys = re.findall(r"\\bibitem\{([^}]*)\}", tex)
key_no = {k: i + 1 for i, k in enumerate(bib_keys)}
assert len(bib_keys) == len(key_no), "duplicate bibitem keys"


def cite_repl(m):
    nums = sorted(key_no[k.strip()] for k in m.group(1).split(","))
    # compress consecutive runs: [1,2,3,5] -> [1--3,5]
    parts, start, prev = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        parts.append(f"{start}--{prev}" if prev > start else f"{start}")
        start = prev = n
    parts.append(f"{start}--{prev}" if prev > start else f"{start}")
    return " [" + ",".join(parts) + "]"


n_cites = len(re.findall(r"\\cite\{[^}]*\}", tex))
tex = re.sub(r"\\cite\{([^}]*)\}", cite_repl, tex)

bib_m = re.search(
    r"\\begin\{thebibliography\}\{[^}]*\}(.*?)\\end\{thebibliography\}",
    tex,
    re.S,
)
assert bib_m, "thebibliography not found"
entries = re.split(r"\\bibitem\{[^}]*\}", bib_m.group(1))[1:]
entries = [" ".join(e.split()) for e in entries]
ref_block = "\n\\section*{References}\n\n" + "\n\n".join(
    f"{i}. {e}" for i, e in enumerate(entries, 1)
)
tex = tex[: bib_m.start()] + ref_block + tex[bib_m.end() :]

print(
    f"adapted: {n_pdf} includegraphics, {n_mc} multicolumn specs, "
    f"{n_als} addlinespace before a multicolumn row, {n_cmid} cmidrule lines, "
    f"{n_width} tabular preambles with widths, {n_notes} table-notes blocks, {n_brk} path breaks, "
    f"{n_cites} cite calls, {len(entries)} references"
)

with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False, encoding="utf-8") as lua:
    lua.write(TABLENOTES_LUA)
try:
    p = subprocess.run(
        [
            PANDOC, "-f", "latex", "-t", "docx",
            f"--reference-doc={REF}",
            f"--lua-filter={lua.name}",
            "--resource-path=.;figures",
            "-o", OUT,
        ],
        input=tex.encode("utf-8"),
        cwd=ROOT + r"\own-article\paper\en",
        capture_output=True,
    )
finally:
    os.unlink(lua.name)
sys.stderr.write(p.stderr.decode("utf-8", "replace"))
if p.returncode:
    sys.exit(p.returncode)

# -- 8: fix OMML property order (pandoc emits <m:nor/><m:sty/>, the OOXML
#       schema wants <m:sty/> first inside <m:rPr>) -----------------------------
tmp = OUT + ".tmp"
with zipfile.ZipFile(OUT) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/document.xml":
            xml = data.decode("utf-8")

            def fix_rpr(m):
                inner = m.group(1)
                # m:nor duplicates m:sty m:val="p" (both mean upright) and the
                # bundled OOXML schema rejects it in this position -> drop it
                inner = inner.replace("<m:nor />", "").replace("<m:nor/>", "")
                sty = re.search(r"<m:sty[^>]*/>", inner)
                if sty and not inner.startswith(sty.group(0)):
                    inner = sty.group(0) + inner.replace(sty.group(0), "", 1)
                return "<m:rPr>" + inner + "</m:rPr>"

            n_sty = len(re.findall(r"<m:rPr>(?!<m:sty)(?=[^>]*(?:<[^>]+>)*<m:sty)", xml))
            xml = re.sub(r"<m:rPr>(.*?)</m:rPr>", fix_rpr, xml)
            data = xml.encode("utf-8")
        zout.writestr(item, data)
shutil.move(tmp, OUT)
print(f"reordered m:sty in {n_sty} m:rPr blocks")

# ---- post-checks -----------------------------------------------------------
doc = zipfile.ZipFile(OUT).read("word/document.xml").decode("utf-8")
txt = re.sub(r"<[^>]+>", " ", doc)
txt = re.sub(r"\s+", " ", txt)

n_bracket = len(re.findall(r"\[\d+(?:[,\u2013-]+\d+)*\]", txt))
# Every \multicolumn row that labels a panel inside a table has to reach the output:
# losing one leaves a block of rows unlabelled while the text still refers to it.
missing_labels = [lab for lab in panel_labels
                  if lab.replace("--", "\u2013") not in txt]
checks = {
    "16 tables": doc.count("<w:tbl>") == 16,
    "images embedded": len(zipfile.ZipFile(OUT).namelist()) > 0
    and len([n for n in zipfile.ZipFile(OUT).namelist() if n.startswith("word/media/")]) >= 6,
    "math present": doc.count("<m:oMath>") > 1000,
    "no raw tabular leak": not re.search(r"&amp;\s*\d", txt),
    "bib entries present": "Katzin" in txt and "Henten" in txt,
    "References heading": "References" in txt,
    "no stray width arg": " 99 Katzin" not in txt,
    "numeric citations": n_bracket >= n_cites - 5,
    "no dropped cites": "[?]" not in txt,
    "title present": "Multi-step stability selects" in txt,
    "notuboil present": "notuboil" in txt,
    f"{len(panel_labels)} table panel labels": not missing_labels,
    "5 table-notes blocks styled": doc.count('<w:pStyle w:val="MDPI43tablefooter"') == 5,
    "4 tables carry column widths": doc.count('<w:tblLayout w:type="fixed"') == 4,
}
if missing_labels:
    print("     lost panel labels:", missing_labels)
print(f"[{n_bracket} bracketed citation groups in body]")
for name, ok in checks.items():
    print(("OK  " if ok else "FAIL"), name)
if not all(checks.values()):
    sys.exit(1)
print("ALL CHECKS PASSED ->", OUT)
