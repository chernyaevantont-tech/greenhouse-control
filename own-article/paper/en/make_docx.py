"""Regenerate own-article/paper/en/paper_en.docx from paper_en.tex via pandoc.

Conversion-only adaptations (the .tex source of truth is NOT modified):
  1. includegraphics .pdf -> .png (docx cannot embed PDF)
  2. \\multicolumn{N}{@{}l} -> \\multicolumn{N}{l} (pandoc drops tables whose
     multicolumn spec carries @{})
  3. \\cite{keys} -> literal [n] / [n,m] / [n-m] (pandoc drops Cite inlines
     without citeproc); numbering follows the \\bibitem order of the file
  4. thebibliography -> \\section*{References} + plain numbered paragraphs
     (pandoc leaks the {99} width argument and adds no heading)
"""
import io
import re
import subprocess
import sys
import zipfile

ROOT = r"C:\Users\zergu\repos\greenhouse-control"
TEX = ROOT + r"\own-article\paper\en\paper_en.tex"
OUT = ROOT + r"\own-article\paper\en\paper_en.docx"
REF = ROOT + r"\mdpi-template\agronomy-template.docx"
PANDOC = ROOT + r"\.tools\pandoc-3.10.2\pandoc.exe"

tex = open(TEX, encoding="utf-8").read()

n_pdf = len(re.findall(r"\\includegraphics\[[^\]]*\]\{[^}]*\.pdf\}", tex))
tex = re.sub(r"(\\includegraphics\[[^\]]*\]\{[^}]*)\.pdf\}", r"\1.png}", tex)

n_mc = tex.count("{@{}l}")
tex = tex.replace("{@{}l}", "{l}")

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
    f"{n_cites} cite calls, {len(entries)} references"
)

p = subprocess.run(
    [
        PANDOC, "-f", "latex", "-t", "docx",
        f"--reference-doc={REF}",
        "--resource-path=.;figures",
        "-o", OUT,
    ],
    input=tex.encode("utf-8"),
    cwd=ROOT + r"\own-article\paper\en",
    capture_output=True,
)
sys.stderr.write(p.stderr.decode("utf-8", "replace"))
if p.returncode:
    sys.exit(p.returncode)

# -- 5: fix OMML property order (pandoc emits <m:nor/><m:sty/>, the OOXML
#       schema wants <m:sty/> first inside <m:rPr>) -----------------------------
import shutil
import tempfile

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
}
print(f"[{n_bracket} bracketed citation groups in body]")
for name, ok in checks.items():
    print(("OK  " if ok else "FAIL"), name)
if not all(checks.values()):
    sys.exit(1)
print("ALL CHECKS PASSED ->", OUT)
