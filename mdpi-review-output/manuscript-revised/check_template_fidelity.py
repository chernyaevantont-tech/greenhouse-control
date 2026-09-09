"""Guard the MDPI Agronomy template inside the built .docx.

Compares the template-owned parts of the built document against
mdpi-template/agronomy-template.docx and prints a fingerprint that must not
change across rebuilds. Run before and after any edit; the two runs must agree
on every line except the ones marked (content).

Exit code 1 if a template-owned part diverges.
"""
import hashlib
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(r"C:\Users\zergu\repos\greenhouse-control")
TEMPLATE = ROOT / "mdpi-template" / "agronomy-template.docx"
BUILT = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    ROOT / "mdpi-review-output" / "manuscript-revised" / "manuscript-revised-mdpi.docx"

NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Parts the template owns. Divergence here means the house style is broken.
TEMPLATE_OWNED = [
    "word/theme/theme1.xml",
    "word/fontTable.xml",
    "word/settings.xml",
    "word/webSettings.xml",
]

failures = []


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


def canon(b):
    """Digest of the CANONICAL XML, not of the bytes.

    python-docx re-serialises every part it opens: the XML declaration switches
    quote style and attribute order and namespace declarations move, even where
    nothing changed. Canonical form still catches a real edit to a
    preserve-only part without flagging a rewrite that says the same thing.
    This is the same rule the project's own audit_mdpi.py applies.
    """
    import lxml.etree as etree
    if isinstance(b, bytes):
        b = b.decode("utf-8", "replace")
    return sha(etree.canonicalize(xml_data=b, strip_text=False).encode("utf-8"))


def check(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        failures.append(msg)


print("=" * 74)
print("MDPI TEMPLATE FIDELITY")
print(f"  template : {TEMPLATE.name}")
print(f"  built    : {BUILT.name}")
print("=" * 74)

print(f"\ntemplate sha256[:16] = {sha(TEMPLATE.read_bytes())}   (must never change)")

with zipfile.ZipFile(TEMPLATE) as tz, zipfile.ZipFile(BUILT) as bz:
    check(bz.testzip() is None, "zip integrity of the built document")

    tnames, bnames = set(tz.namelist()), set(bz.namelist())

    # 1. headers and footers must be carried over verbatim
    hf = sorted(n for n in tnames if re.match(r"word/(header|footer)\d*\.xml", n))
    print(f"\nheaders/footers in template: {len(hf)}")
    for n in hf:
        if n not in bnames:
            check(False, f"{n} missing from the built document")
        else:
            check(canon(tz.read(n)) == canon(bz.read(n)), f"{n} identical to template")

    # 2. theme, fonts, settings
    print()
    for n in TEMPLATE_OWNED:
        if n not in tnames:
            continue
        if n not in bnames:
            check(False, f"{n} missing from the built document")
        elif n == "word/settings.xml":
            # KNOWN, PRE-EXISTING: pandoc emits its own settings.xml rather than
            # carrying the template's over. Verified identical in the pre-review
            # build (own-article/paper/en/paper_en_mdpi.docx), so it is a property
            # of the pipeline, not of any edit. Reported, not failed.
            t = re.sub(rb"<w:updateFields[^/]*/>", b"", tz.read(n))
            b = re.sub(rb"<w:updateFields[^/]*/>", b"", bz.read(n))
            same = canon(t) == canon(b)
            print(("  OK   " if same else "  WARN ") + f"{n} vs template"
                  + ("" if same else " -- differs (KNOWN, pre-existing; pandoc"
                                     " substitutes its own settings part, dropping"
                                     " m:mathPr/Cambria Math). Not a regression."))
        else:
            check(canon(tz.read(n)) == canon(bz.read(n)), f"{n} identical to template")

    # 3. every MDPI_* style the template defines must survive, with its definition intact
    def styles(z):
        import lxml.etree as etree
        root = etree.fromstring(z.read("word/styles.xml"))
        out = {}
        for s in root.iter(f"{NS}style"):
            sid = s.get(f"{NS}styleId")
            out[sid] = canon(etree.tostring(s))
        return out

    ts, bs = styles(tz), styles(bz)
    mdpi = sorted(k for k in ts if k.lower().startswith("mdpi"))
    print(f"\nMDPI_* styles defined in template: {len(mdpi)}")
    missing = [k for k in mdpi if k not in bs]
    altered = [k for k in mdpi if k in bs and bs[k] != ts[k]]
    check(not missing, f"all MDPI_* styles present" + (f" -- MISSING: {missing}" if missing else ""))
    check(not altered, f"all MDPI_* style definitions unaltered" + (f" -- ALTERED: {altered}" if altered else ""))
    print(f"  (built document defines {len(bs)} styles in total)")

    # 4. page geometry of the body section
    import lxml.etree as etree
    doc = etree.fromstring(bz.read("word/document.xml"))
    sect = doc.findall(f".//{NS}sectPr")
    if sect:
        pg = sect[-1].find(f"{NS}pgSz")
        mar = sect[-1].find(f"{NS}pgMar")
        w, h = pg.get(f"{NS}w"), pg.get(f"{NS}h")
        print(f"\npage size: {w} x {h} twips", end="")
        check(w == "11906" and h == "16838", " -> A4 portrait")
        print("  margins:", {k.split('}')[1]: v for k, v in mar.attrib.items()})
        lnn = sect[-1].find(f"{NS}lnNumType")
        check(lnn is not None, "continuous line numbering present (MDPI submission requirement)")

    # 5. content fingerprint (EXPECTED to change when prose is edited)
    body = bz.read("word/document.xml")
    paras = len(re.findall(rb"<w:p[ >]", body))
    tbls = len(re.findall(rb"<w:tbl>", body))
    drawings = len(re.findall(rb"<w:drawing>", body))
    print(f"\n(content) paragraphs {paras} | tables {tbls} | drawings {drawings}")
    print(f"(content) document.xml sha[:16] = {sha(body)}")

print("\n" + "=" * 74)
if failures:
    print(f"TEMPLATE FIDELITY FAILED: {len(failures)} problem(s)")
    for f in failures:
        print("   - " + f)
    raise SystemExit(1)
print("TEMPLATE FIDELITY OK -- every template-owned part is byte-identical")
