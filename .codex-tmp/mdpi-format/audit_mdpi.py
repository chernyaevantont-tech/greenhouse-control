from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path

from lxml import etree


ROOT = Path(r"C:\Users\zergu\repos\greenhouse-control")
SOURCE = ROOT / "own-article" / "paper" / "en" / "paper_en.docx"
OUTPUT = ROOT / "own-article" / "paper" / "en" / "paper_en_mdpi.docx"
TEMPLATE = ROOT / "mdpi-template" / "agronomy-template.docx"
EXPECTED_TEMPLATE_SHA = "87a0d307c497cf8ed1cb6b108669d8cc1b6ea049bdb7198572f4080a38bb7768"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}
W = f"{{{NS['w']}}}"
R = f"{{{NS['r']}}}"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def text(p: etree._Element) -> str:
    return "".join(p.xpath(".//w:t/text() | .//m:t/text()", namespaces=NS))


def pstyle(p: etree._Element) -> str | None:
    node = p.find("./w:pPr/w:pStyle", NS)
    return node.get(W + "val") if node is not None else None


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


with zipfile.ZipFile(SOURCE) as source_zip, zipfile.ZipFile(OUTPUT) as out_zip, zipfile.ZipFile(TEMPLATE) as template_zip:
    check(out_zip.testzip() is None, "DOCX zip contains a corrupt member")
    check(file_digest(TEMPLATE) == EXPECTED_TEMPLATE_SHA, "Reference template changed")
    check(file_digest(SOURCE) != file_digest(OUTPUT), "Output unexpectedly equals source")

    doc = etree.fromstring(out_zip.read("word/document.xml"))
    styles = etree.fromstring(out_zip.read("word/styles.xml"))
    rels = etree.fromstring(out_zip.read("word/_rels/document.xml.rels"))
    settings = etree.fromstring(out_zip.read("word/settings.xml"))
    body = doc.find("./w:body", NS)
    check(body is not None, "Document body missing")

    defined = {
        node.get(W + "styleId")
        for node in styles.xpath("./w:style", namespaces=NS)
        if node.get(W + "styleId")
    }
    used_pstyles = {pstyle(p) for p in doc.xpath(".//w:p", namespaces=NS) if pstyle(p)}
    used_tblstyles = {
        node.get(W + "val")
        for node in doc.xpath(".//w:tblPr/w:tblStyle", namespaces=NS)
        if node.get(W + "val")
    }
    check(not (used_pstyles - defined), f"Undefined paragraph styles: {sorted(used_pstyles - defined)}")
    check(not (used_tblstyles - defined), f"Undefined table styles: {sorted(used_tblstyles - defined)}")

    relationship_ids = {
        node.get("Id") for node in rels.xpath("./pr:Relationship", namespaces=NS) if node.get("Id")
    }
    used_relationship_ids = set()
    for node in doc.iter():
        for attr in (R + "id", R + "embed", R + "link"):
            if node.get(attr):
                used_relationship_ids.add(node.get(attr))
    check(
        not (used_relationship_ids - relationship_ids),
        f"Missing document relationships: {sorted(used_relationship_ids - relationship_ids)}",
    )

    paragraphs = body.findall(W + "p")
    all_text = "\n".join(text(p) for p in doc.xpath(".//w:p", namespaces=NS))
    table_captions = [p for p in paragraphs if pstyle(p) == "MDPI41tablecaption"]
    figure_captions = [p for p in paragraphs if pstyle(p) == "MDPI51figurecaption"]
    refs = [p for p in paragraphs if pstyle(p) == "MDPI81references"]
    headings_1 = [text(p).strip() for p in paragraphs if pstyle(p) == "MDPI21heading1"]
    headings_2 = [text(p).strip() for p in paragraphs if pstyle(p) == "MDPI22heading2"]
    data_tables = [
        tbl
        for tbl in body.findall(W + "tbl")
        if (node := tbl.find("./w:tblPr/w:tblStyle", NS)) is not None
        and node.get(W + "val") == "MDPI41threelinetable"
    ]
    equation_tables = [
        tbl
        for tbl in body.findall(W + "tbl")
        if "MDPI39equation" in [pstyle(p) for p in tbl.xpath(".//w:p", namespaces=NS)]
    ]

    check(len(table_captions) == 16, f"Table caption count is {len(table_captions)}")
    check(len(figure_captions) == 6, f"Figure caption count is {len(figure_captions)}")
    check(len(refs) == 44, f"Reference count is {len(refs)}")
    check(len(data_tables) == 16, f"Data table count is {len(data_tables)}")
    check(len(equation_tables) == 3, f"Equation table count is {len(equation_tables)}")
    check(
        all(text(p).startswith(f"Table {i}. ") for i, p in enumerate(table_captions, 1)),
        "Table labels are not sequential",
    )
    check(
        all(text(p).startswith(f"Figure {i}. ") for i, p in enumerate(figure_captions, 1)),
        "Figure labels are not sequential",
    )
    check(text(figure_captions[-1]).count("Graphical abstract.") == 1, "Graphical abstract label is duplicated")
    check(
        headings_1 == [
            "1. Introduction",
            "2. Materials and Methods",
            "3. Results",
            "4. Discussion",
            "5. Conclusions",
            "References",
        ],
        f"Top-level heading sequence is wrong: {headings_1}",
    )
    check(len(headings_2) == 23, f"Expected 23 subsections, found {len(headings_2)}")
    check(not re.search(r"\[eq:[^\]]+\]|2-3\(lr\)4-5", all_text), "Internal generator tokens remain")
    check(all(f"({i})" in text(tbl) for i, tbl in enumerate(equation_tables, 1)), "Equation numbering failed")
    check(not doc.xpath(".//w:ins | .//w:del", namespaces=NS), "Tracked-change markup remains")

    for table_no, tbl in enumerate(data_tables, 1):
        first_row = tbl.find(W + "tr")
        check(first_row is not None, f"Table {table_no} has no rows")
        check(first_row.find("./w:trPr/w:tblHeader", NS) is not None, f"Table {table_no} header does not repeat")
        borders = tbl.find("./w:tblPr/w:tblBorders", NS)
        check(borders is not None, f"Table {table_no} has no border specification")
        check(borders.find(W + "insideV").get(W + "val") == "nil", f"Table {table_no} has vertical rules")

    section = body.find(W + "sectPr")
    check(section is not None, "Section properties missing")
    page_size = section.find(W + "pgSz")
    page_margins = section.find(W + "pgMar")
    line_numbers = section.find(W + "lnNumType")
    check((page_size.get(W + "w"), page_size.get(W + "h")) == ("11906", "16838"), "A4 geometry changed")
    check(
        tuple(page_margins.get(W + key) for key in ("top", "right", "bottom", "left", "header", "footer"))
        == ("1417", "720", "907", "720", "720", "612"),
        "MDPI margins changed",
    )
    check(
        (line_numbers.get(W + "countBy"), line_numbers.get(W + "distance"), line_numbers.get(W + "restart"))
        == ("1", "255", "continuous"),
        "Continuous line numbering changed",
    )
    check(settings.find("./w:updateFields", NS).get(W + "val") == "true", "Word fields will not update")

    backmatter_order = [
        "Supplementary Materials:",
        "Author Contributions:",
        "Funding:",
        "Institutional Review Board Statement:",
        "Informed Consent Statement:",
        "Data Availability Statement:",
        "Acknowledgments:",
        "Conflicts of Interest:",
    ]
    positions = [all_text.index(label) for label in backmatter_order]
    check(positions == sorted(positions), "Back-matter declarations are out of MDPI order")

    preserved_parts = [
        name
        for name in source_zip.namelist()
        if name.startswith("word/header")
        or name.startswith("word/footer")
        or name.startswith("word/media/")
        or name in ("word/theme/theme1.xml", "word/fontTable.xml", "word/numbering.xml", "word/styles.xml")
    ]
    changed_preserved = [
        name for name in preserved_parts if digest(source_zip.read(name)) != digest(out_zip.read(name))
    ]
    check(not changed_preserved, f"Preserve-only parts changed: {changed_preserved}")

    template_chrome = [
        name
        for name in template_zip.namelist()
        if name.startswith("word/header")
        or name.startswith("word/footer")
        or name in ("word/theme/theme1.xml", "word/fontTable.xml")
    ]
    chrome_mismatch = [
        name for name in template_chrome if digest(template_zip.read(name)) != digest(out_zip.read(name))
    ]
    check(not chrome_mismatch, f"Output chrome differs from reference template: {chrome_mismatch}")

    placeholders = sorted(set(re.findall(r"\[\[[^\]]+\]\]", all_text)))
    print(f"output_sha256={file_digest(OUTPUT)}")
    print(f"paragraph_styles={len(used_pstyles)} undefined=0")
    print(f"tables=data:{len(data_tables)} equations:{len(equation_tables)} captions:{len(table_captions)}")
    print(f"figures=6 captions:{len(figure_captions)}")
    print(f"references={len(refs)}")
    print(f"headings1={len(headings_1)} headings2={len(headings_2)}")
    print(f"relationships_used={len(used_relationship_ids)} missing=0")
    print(f"preserved_parts={len(preserved_parts)} changed=0")
    print(f"explicit_placeholders={len(placeholders)}")
    for placeholder in placeholders:
        print(f"placeholder={placeholder}")
    print("AUDIT_OK")
