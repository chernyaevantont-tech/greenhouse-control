from __future__ import annotations

import hashlib
import re
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path

from lxml import etree


ROOT = Path(r"C:\Users\zergu\repos\greenhouse-control")
SOURCE = ROOT / "own-article" / "paper" / "en" / "paper_en.docx"
TEMPLATE = ROOT / "mdpi-template" / "agronomy-template.docx"
OUTPUT = ROOT / "own-article" / "paper" / "en" / "paper_en_mdpi.docx"
EXPECTED_TEMPLATE_SHA256 = "87a0d307c497cf8ed1cb6b108669d8cc1b6ea049bdb7198572f4080a38bb7768"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
W = f"{{{NS['w']}}}"
M = f"{{{NS['m']}}}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def qn(local: str) -> str:
    return W + local


def parse_xml(blob: bytes) -> etree._Element:
    return etree.fromstring(blob)


def serialize_xml(root: etree._Element) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first(parent: etree._Element, tag: str) -> etree._Element | None:
    return parent.find(qn(tag))


def child(parent: etree._Element, tag: str, *, first_child: bool = False) -> etree._Element:
    found = first(parent, tag)
    if found is not None:
        return found
    found = etree.Element(qn(tag))
    if first_child:
        parent.insert(0, found)
    else:
        parent.append(found)
    return found


def ensure_ppr(p: etree._Element) -> etree._Element:
    return child(p, "pPr", first_child=True)


def ensure_rpr(run: etree._Element) -> etree._Element:
    return child(run, "rPr", first_child=True)


def ensure_tcpr(tc: etree._Element) -> etree._Element:
    return child(tc, "tcPr", first_child=True)


def ensure_trpr(tr: etree._Element) -> etree._Element:
    return child(tr, "trPr", first_child=True)


def ensure_tblpr(tbl: etree._Element) -> etree._Element:
    return child(tbl, "tblPr", first_child=True)


def pstyle(p: etree._Element) -> str | None:
    node = p.find("./w:pPr/w:pStyle", NS)
    return node.get(qn("val")) if node is not None else None


def set_pstyle(p: etree._Element, style_id: str) -> None:
    ppr = ensure_ppr(p)
    node = first(ppr, "pStyle")
    if node is None:
        node = etree.Element(qn("pStyle"))
        ppr.insert(0, node)
    node.set(qn("val"), style_id)


def set_tblstyle(tbl: etree._Element, style_id: str) -> None:
    tblpr = ensure_tblpr(tbl)
    node = first(tblpr, "tblStyle")
    if node is None:
        node = etree.Element(qn("tblStyle"))
        tblpr.insert(0, node)
    node.set(qn("val"), style_id)


def paragraph_text(p: etree._Element) -> str:
    return "".join(p.xpath(".//w:t/text() | .//m:t/text()", namespaces=NS))


def paragraph_text_nodes(p: etree._Element) -> list[etree._Element]:
    return p.xpath(".//w:t | .//m:t", namespaces=NS)


def set_text_node(node: etree._Element, value: str) -> None:
    node.text = value
    if node.tag == qn("t"):
        if value[:1].isspace() or value[-1:].isspace():
            node.set(XML_SPACE, "preserve")
        else:
            node.attrib.pop(XML_SPACE, None)


def consume_text_prefix(p: etree._Element, count: int) -> None:
    remaining = count
    for node in paragraph_text_nodes(p):
        value = node.text or ""
        if not remaining:
            break
        take = min(remaining, len(value))
        set_text_node(node, value[take:])
        remaining -= take
    if remaining:
        raise ValueError(f"Cannot consume {count} characters from paragraph: {paragraph_text(p)!r}")


def strip_matching_prefix(p: etree._Element, pattern: str) -> str | None:
    value = paragraph_text(p)
    match = re.match(pattern, value, flags=re.IGNORECASE)
    if not match:
        return None
    consume_text_prefix(p, match.end())
    return match.group(0)


def make_run(text: str, *, bold: bool = False, italic: bool = False, superscript: bool = False) -> etree._Element:
    run = etree.Element(qn("r"))
    if bold or italic or superscript:
        rpr = ensure_rpr(run)
        if bold:
            rpr.append(etree.Element(qn("b")))
        if italic:
            rpr.append(etree.Element(qn("i")))
        if superscript:
            va = etree.SubElement(rpr, qn("vertAlign"))
            va.set(qn("val"), "superscript")
    t = etree.SubElement(run, qn("t"))
    set_text_node(t, text)
    return run


def prepend_runs(p: etree._Element, runs: list[etree._Element]) -> None:
    ppr = first(p, "pPr")
    pos = 1 if ppr is not None and len(p) and p[0] is ppr else 0
    for run in runs:
        p.insert(pos, run)
        pos += 1


def append_run(p: etree._Element, text: str, **kwargs: bool) -> None:
    p.append(make_run(text, **kwargs))


def make_paragraph(style_id: str, parts: list[tuple[str, dict[str, bool]]]) -> etree._Element:
    p = etree.Element(qn("p"))
    set_pstyle(p, style_id)
    for text, props in parts:
        p.append(make_run(text, **props))
    return p


def clear_paragraph_content(p: etree._Element) -> None:
    for node in list(p):
        if node.tag != qn("pPr"):
            p.remove(node)


def set_keep_next(p: etree._Element) -> None:
    ppr = ensure_ppr(p)
    if first(ppr, "keepNext") is None:
        ppr.append(etree.Element(qn("keepNext")))


def set_keep_lines(p: etree._Element) -> None:
    ppr = ensure_ppr(p)
    if first(ppr, "keepLines") is None:
        ppr.append(etree.Element(qn("keepLines")))


def set_page_break_before(p: etree._Element) -> None:
    ppr = ensure_ppr(p)
    page_break = child(ppr, "pageBreakBefore")
    page_break.set(qn("val"), "true")


def remove_paragraph_borders(p: etree._Element) -> None:
    ppr = first(p, "pPr")
    if ppr is None:
        return
    borders = first(ppr, "pBdr")
    if borders is not None:
        ppr.remove(borders)


def set_jc(p: etree._Element, value: str) -> None:
    ppr = ensure_ppr(p)
    jc = child(ppr, "jc")
    jc.set(qn("val"), value)


def set_cell_vcenter(tc: etree._Element) -> None:
    tcpr = ensure_tcpr(tc)
    va = child(tcpr, "vAlign")
    va.set(qn("val"), "center")


def set_cell_bottom_rule(tc: etree._Element) -> None:
    tcpr = ensure_tcpr(tc)
    borders = child(tcpr, "tcBorders")
    bottom = child(borders, "bottom")
    bottom.set(qn("val"), "single")
    bottom.set(qn("sz"), "8")
    bottom.set(qn("space"), "0")
    bottom.set(qn("color"), "000000")


def set_run_bold(run: etree._Element) -> None:
    rpr = ensure_rpr(run)
    if first(rpr, "b") is None:
        rpr.append(etree.Element(qn("b")))


def set_table_widths_and_rules(tbl: etree._Element) -> None:
    set_tblstyle(tbl, "MDPI41threelinetable")
    tblpr = ensure_tblpr(tbl)

    width = child(tblpr, "tblW")
    width.set(qn("w"), "7920")
    width.set(qn("type"), "dxa")
    layout = child(tblpr, "tblLayout")
    layout.set(qn("type"), "fixed")

    borders = child(tblpr, "tblBorders")
    specifications = {
        "top": ("single", "8", "000000"),
        "left": ("nil", "0", "auto"),
        "bottom": ("single", "8", "000000"),
        "right": ("nil", "0", "auto"),
        "insideH": ("nil", "0", "auto"),
        "insideV": ("nil", "0", "auto"),
    }
    for side, (value, size, color) in specifications.items():
        edge = child(borders, side)
        edge.set(qn("val"), value)
        edge.set(qn("sz"), size)
        edge.set(qn("space"), "0")
        edge.set(qn("color"), color)

    cell_mar = child(tblpr, "tblCellMar")
    for side, amount in (("top", "60"), ("left", "80"), ("bottom", "60"), ("right", "80")):
        margin = child(cell_mar, side)
        margin.set(qn("w"), amount)
        margin.set(qn("type"), "dxa")

    rows = tbl.findall(qn("tr"))
    for row_idx, row in enumerate(rows):
        trpr = ensure_trpr(row)
        for height in trpr.findall(qn("trHeight")):
            trpr.remove(height)
        if row_idx == 0 and first(trpr, "tblHeader") is None:
            trpr.append(etree.Element(qn("tblHeader")))
        if first(trpr, "cantSplit") is None:
            trpr.append(etree.Element(qn("cantSplit")))

        for tc in row.findall(qn("tc")):
            set_cell_vcenter(tc)
            if row_idx == 0:
                set_cell_bottom_rule(tc)
            for p in tc.xpath(".//w:p", namespaces=NS):
                set_pstyle(p, "MDPI42tablebody")
                text = paragraph_text(p).strip()
                if row_idx == 0:
                    set_jc(p, "center")
                    for run in p.xpath(".//w:r", namespaces=NS):
                        set_run_bold(run)
                elif len(text) > 34 or re.search(r"[.;:]\s", text):
                    set_jc(p, "left")
                else:
                    set_jc(p, "center")


def replace_literal_in_text_nodes(root: etree._Element, old: str, new: str) -> int:
    hits = 0
    for node in root.xpath(".//w:t | .//m:t", namespaces=NS):
        value = node.text or ""
        if old in value:
            set_text_node(node, value.replace(old, new))
            hits += value.count(old)
    return hits


def replace_literal_across_paragraph_runs(root: etree._Element, old: str, new: str) -> int:
    """Replace text even when Word has split it across several runs/text nodes."""
    hits = 0
    for p in root.xpath(".//w:p", namespaces=NS):
        while old in paragraph_text(p):
            nodes = paragraph_text_nodes(p)
            values = [node.text or "" for node in nodes]
            combined = "".join(values)
            start = combined.index(old)
            end = start + len(old)
            cursor = 0
            inserted = False
            for node, value in zip(nodes, values):
                node_start = cursor
                node_end = cursor + len(value)
                cursor = node_end
                overlap_start = max(start, node_start)
                overlap_end = min(end, node_end)
                if overlap_start >= overlap_end:
                    continue
                local_start = overlap_start - node_start
                local_end = overlap_end - node_start
                prefix = value[:local_start]
                suffix = value[local_end:]
                if not inserted:
                    set_text_node(node, prefix + new + suffix)
                    inserted = True
                else:
                    set_text_node(node, prefix + suffix)
            hits += 1
    return hits


def defined_style_ids(styles_root: etree._Element) -> set[str]:
    return {
        style.get(qn("styleId"))
        for style in styles_root.xpath("./w:style", namespaces=NS)
        if style.get(qn("styleId"))
    }


def find_equation_table(template_doc: etree._Element) -> etree._Element:
    for tbl in template_doc.xpath(".//w:tbl", namespaces=NS):
        styles = [pstyle(p) for p in tbl.xpath(".//w:p", namespaces=NS)]
        if "MDPI39equation" in styles and "MDPI3aequationnumber" in styles:
            return tbl
    raise RuntimeError("The reference template does not contain an MDPI equation table")


def make_equation_table(template_tbl: etree._Element, source_p: etree._Element, number: int) -> etree._Element:
    tbl = deepcopy(template_tbl)
    cells = tbl.xpath("./w:tr[1]/w:tc", namespaces=NS)
    if len(cells) < 2:
        raise RuntimeError("Unexpected equation-table structure")
    eq_p = cells[0].find(qn("p"))
    num_p = cells[-1].find(qn("p"))
    if eq_p is None or num_p is None:
        raise RuntimeError("Equation table has no paragraph cells")

    clear_paragraph_content(eq_p)
    set_pstyle(eq_p, "MDPI39equation")
    for node in list(source_p):
        if node.tag != qn("pPr"):
            eq_p.append(deepcopy(node))

    clear_paragraph_content(num_p)
    set_pstyle(num_p, "MDPI3aequationnumber")
    append_run(num_p, f"({number})")
    return tbl


def set_section_geometry(doc_root: etree._Element) -> None:
    sections = doc_root.xpath(".//w:sectPr", namespaces=NS)
    if not sections:
        raise RuntimeError("Document has no section properties")
    for sect in sections:
        pg_sz = child(sect, "pgSz")
        pg_sz.set(qn("w"), "11906")
        pg_sz.set(qn("h"), "16838")
        pg_sz.attrib.pop(qn("orient"), None)

        pg_mar = child(sect, "pgMar")
        for key, value in {
            "top": "1417", "right": "720", "bottom": "907", "left": "720",
            "header": "720", "footer": "612", "gutter": "0",
        }.items():
            pg_mar.set(qn(key), value)

        line = child(sect, "lnNumType")
        line.set(qn("countBy"), "1")
        line.set(qn("distance"), "255")
        line.set(qn("restart"), "continuous")
        page_no = child(sect, "pgNumType")
        page_no.set(qn("start"), "1")
        if first(sect, "titlePg") is None:
            sect.append(etree.Element(qn("titlePg")))


def enable_field_updates(settings_root: etree._Element) -> None:
    update = settings_root.find("./w:updateFields", NS)
    if update is None:
        update = etree.SubElement(settings_root, qn("updateFields"))
    update.set(qn("val"), "true")


def build() -> dict[str, int | str]:
    if sha256(TEMPLATE) != EXPECTED_TEMPLATE_SHA256:
        raise RuntimeError("The retained MDPI reference changed; refusing to format against an unverified template")
    if OUTPUT.resolve() == SOURCE.resolve():
        raise RuntimeError("Output must not overwrite the source manuscript")

    with zipfile.ZipFile(SOURCE, "r") as zin:
        entries = {name: zin.read(name) for name in zin.namelist()}
    with zipfile.ZipFile(TEMPLATE, "r") as ztmpl:
        template_doc = parse_xml(ztmpl.read("word/document.xml"))

    doc = parse_xml(entries["word/document.xml"])
    styles = parse_xml(entries["word/styles.xml"])
    settings = parse_xml(entries["word/settings.xml"])
    body = doc.find("./w:body", NS)
    if body is None:
        raise RuntimeError("Document body missing")

    # Front matter: retain the title and scientific text, but rebuild the anonymous metadata slots.
    top_paragraphs = body.findall(qn("p"))
    title_p = next((p for p in top_paragraphs if pstyle(p) == "Title"), top_paragraphs[0])
    title_index = body.index(title_p)
    set_pstyle(title_p, "MDPI12title")
    article_type = make_paragraph("MDPI11articletype", [("Article", {"italic": True})])
    body.insert(title_index, article_type)

    abstract_label_p = next((p for p in body.findall(qn("p")) if pstyle(p) == "AbstractTitle"), None)
    abstract_p = next((p for p in body.findall(qn("p")) if pstyle(p) == "Abstract"), None)
    if abstract_label_p is None or abstract_p is None:
        raise RuntimeError("Could not locate the source abstract")

    # Remove the broken author/affiliation paragraphs between title and abstract.
    for node in list(body):
        if node is title_p or node is abstract_label_p:
            continue
        idx = body.index(node)
        if body.index(title_p) < idx < body.index(abstract_label_p) and node.tag == qn("p"):
            body.remove(node)

    insert_at = body.index(title_p) + 1
    author_p = make_paragraph(
        "MDPI13authornames",
        [
            ("[[AUTHOR 1 – FULL NAME REQUIRED]]", {"bold": True}),
            ("1,*", {"superscript": True}),
            ("; ", {}),
            ("[[AUTHOR 2 – FULL NAME REQUIRED]]", {"bold": True}),
            ("2", {"superscript": True}),
        ],
    )
    affiliation_1 = make_paragraph(
        "MDPI16affiliation",
        [("1", {"superscript": True}), (" [[AFFILIATION 1 REQUIRED]]; [[AUTHOR 1 E-MAIL REQUIRED]]", {})],
    )
    affiliation_2 = make_paragraph(
        "MDPI16affiliation",
        [("2", {"superscript": True}), (" [[AFFILIATION 2 REQUIRED]]; [[AUTHOR 2 E-MAIL REQUIRED]]", {})],
    )
    correspondence = make_paragraph(
        "MDPI16affiliation",
        [("* Correspondence: ", {"bold": True}), ("[[CORRESPONDING AUTHOR E-MAIL REQUIRED]]", {})],
    )
    for p in (author_p, affiliation_1, affiliation_2, correspondence):
        body.insert(insert_at, p)
        insert_at += 1

    # MDPI uses an inline bold Abstract label.
    body.remove(abstract_label_p)
    set_pstyle(abstract_p, "MDPI17abstract")
    strip_matching_prefix(abstract_p, r"\s*Abstract\s*:?\s*")
    prepend_runs(abstract_p, [make_run("Abstract: ", bold=True)])

    keywords_p = next(
        (p for p in body.findall(qn("p")) if re.match(r"\s*Keywords\s*:", paragraph_text(p), flags=re.IGNORECASE)),
        None,
    )
    if keywords_p is None:
        raise RuntimeError("Could not locate the Keywords paragraph")
    set_pstyle(keywords_p, "MDPI18keywords")
    strip_matching_prefix(keywords_p, r"\s*Keywords\s*:\s*")
    prepend_runs(keywords_p, [make_run("Keywords: ", bold=True)])
    separator = make_paragraph("MDPI19line", [])
    body.insert(body.index(keywords_p) + 1, separator)

    # Remove generation tokens and resolve the three display-equation references.
    debris_count = replace_literal_in_text_nodes(doc, "2-3(lr)4-5", "")
    debris_count += replace_literal_across_paragraph_runs(doc, "2-3(lr)4-5", "")
    eq_ref_counts = {
        "epi": replace_literal_in_text_nodes(doc, "[eq:epi]", "(1)"),
        "sindy": replace_literal_in_text_nodes(doc, "[eq:sindy]", "(2)"),
        "mpc": replace_literal_in_text_nodes(doc, "[eq:mpc]", "(3)"),
    }

    # Number sections and subsections while keeping hyperlink/bookmark markup intact.
    h1_map = {
        "Introduction": 1,
        "Materials and Methods": 2,
        "Results": 3,
        "Discussion": 4,
        "Conclusions": 5,
    }
    current_h1: int | None = None
    h2_counter = 0
    reference_heading: etree._Element | None = None
    for p in body.findall(qn("p")):
        old_style = pstyle(p)
        text = paragraph_text(p).strip()
        if old_style == "Heading1":
            set_pstyle(p, "MDPI21heading1")
            set_keep_next(p)
            if text == "References":
                reference_heading = p
                current_h1 = None
                continue
            if text not in h1_map:
                raise RuntimeError(f"Unexpected top-level heading: {text!r}")
            current_h1 = h1_map[text]
            h2_counter = 0
            prepend_runs(p, [make_run(f"{current_h1}. ")])
        elif old_style == "Heading2":
            if current_h1 is None:
                raise RuntimeError(f"Subsection outside a numbered section: {text!r}")
            h2_counter += 1
            set_pstyle(p, "MDPI22heading2")
            set_keep_next(p)
            prepend_runs(p, [make_run(f"{current_h1}.{h2_counter}. ")])

    if reference_heading is None:
        raise RuntimeError("References heading missing")

    # Map source roles to their controlling MDPI styles everywhere in the main document.
    style_map = {
        "Title": "MDPI12title",
        "Author": "MDPI13authornames",
        "AbstractTitle": "MDPI17abstract",
        "Abstract": "MDPI17abstract",
        "FirstParagraph": "MDPI31text",
        "BodyText": "MDPI31text",
        "Heading1": "MDPI21heading1",
        "Heading2": "MDPI22heading2",
        "TableCaption": "MDPI41tablecaption",
        "Compact": "MDPI42tablebody",
        "CaptionedFigure": "MDPI52figure",
        "ImageCaption": "MDPI51figurecaption",
    }
    for p in doc.xpath(".//w:p", namespaces=NS):
        old = pstyle(p)
        if old in style_map:
            set_pstyle(p, style_map[old])

    # Number and style table captions.
    table_captions = [p for p in body.findall(qn("p")) if pstyle(p) == "MDPI41tablecaption"]
    if len(table_captions) != 16:
        raise RuntimeError(f"Expected 16 table captions, found {len(table_captions)}")
    for number, p in enumerate(table_captions, start=1):
        set_keep_next(p)
        if number == 16:
            # This long table otherwise leaves its caption alone at the foot of the preceding page.
            set_page_break_before(p)
        prepend_runs(p, [make_run(f"Table {number}. ", bold=True)])

    # Number and style figure captions; keep the last one explicitly identifiable as the graphical abstract.
    figure_paragraphs = [p for p in body.findall(qn("p")) if pstyle(p) == "MDPI52figure"]
    figure_captions = [p for p in body.findall(qn("p")) if pstyle(p) == "MDPI51figurecaption"]
    if len(figure_paragraphs) != 6 or len(figure_captions) != 6:
        raise RuntimeError(
            f"Expected six figures and six captions, found {len(figure_paragraphs)} and {len(figure_captions)}"
        )
    for p in figure_paragraphs:
        set_jc(p, "center")
        set_keep_next(p)
    for number, p in enumerate(figure_captions, start=1):
        set_keep_lines(p)
        pieces = [make_run(f"Figure {number}. ", bold=True)]
        if number == 6:
            strip_matching_prefix(p, r"\s*Graphical\s+abstract\.\s*")
            remove_paragraph_borders(p)
            pieces.append(make_run("Graphical abstract. ", italic=True))
        prepend_runs(p, pieces)

    # Apply the MDPI back-matter role and insert required-but-missing declarations.
    last_caption_index = body.index(figure_captions[-1])
    reference_index = body.index(reference_heading)
    for node in list(body)[last_caption_index + 1 : reference_index]:
        if node.tag != qn("p"):
            continue
        if not paragraph_text(node).strip() and (
            node.find("./w:pPr/w:pBdr", NS) is not None
            or node.find(".//w:pict", NS) is not None
        ):
            body.remove(node)
            continue
        set_pstyle(node, "MDPI62backmatter")

    backmatter_text = "\n".join(
        paragraph_text(p) for p in body.findall(qn("p"))[last_caption_index + 1 :]
    )
    insertion_target = next(
        (
            p
            for p in body.findall(qn("p"))
            if pstyle(p) == "MDPI62backmatter" and paragraph_text(p).startswith("Conflicts of Interest")
        ),
        reference_heading,
    )
    if "Supplementary Materials:" not in backmatter_text:
        supplementary = make_paragraph(
            "MDPI62backmatter",
            [("Supplementary Materials: ", {"bold": True}), ("Not applicable.", {})],
        )
        body.insert(body.index(next(p for p in body.findall(qn("p")) if paragraph_text(p).startswith("Author Contributions"))), supplementary)
    if "Acknowledgments:" not in backmatter_text:
        acknowledgments = make_paragraph(
            "MDPI62backmatter",
            [("Acknowledgments: ", {"bold": True}), ("[[ACKNOWLEDGMENTS REQUIRED; OTHERWISE STATE ‘Not applicable.’]]", {})],
        )
        # The controlling template places Acknowledgments after Data Availability and before Conflicts.
        insertion_target = next(
            (
                p
                for p in body.findall(qn("p"))
                if pstyle(p) == "MDPI62backmatter" and paragraph_text(p).startswith("Conflicts of Interest")
            ),
            reference_heading,
        )
        body.insert(body.index(insertion_target), acknowledgments)

    # Turn typed reference numbers into true Word numbering controlled by MDPI_8.1_references.
    reference_index = body.index(reference_heading)
    reference_paragraphs: list[etree._Element] = []
    for node in list(body)[reference_index + 1 :]:
        if node.tag != qn("p"):
            continue
        if not paragraph_text(node).strip():
            continue
        strip_matching_prefix(node, r"\s*\d+\.\s+")
        set_pstyle(node, "MDPI81references")
        reference_paragraphs.append(node)
    if len(reference_paragraphs) != 44:
        raise RuntimeError(f"Expected 44 references, found {len(reference_paragraphs)}")

    # Data tables: fixed three-line MDPI tables with repeating headers.
    data_tables = body.findall(qn("tbl"))
    if len(data_tables) != 16:
        raise RuntimeError(f"Expected 16 source data tables, found {len(data_tables)}")
    for tbl in data_tables:
        set_table_widths_and_rules(tbl)

    # In Table 5, keep the two reported changes legible as separate lines in the final cell.
    tuning_table = data_tables[4]
    tuning_rows = tuning_table.findall(qn("tr"))
    if len(tuning_rows) >= 9:
        final_cell = tuning_rows[8].findall(qn("tc"))[-1]
        final_p = final_cell.find(qn("p"))
        if final_p is not None:
            for run in final_p.findall(qn("r")):
                if "".join(run.xpath(".//w:t/text()", namespaces=NS)).isspace():
                    for node in list(run):
                        if node.tag != qn("rPr"):
                            run.remove(node)
                    run.append(etree.Element(qn("br")))
                    break

    # Equations: clone the template's exact two-cell equation component and preserve Office Math nodes.
    equation_template = find_equation_table(template_doc)
    equation_paragraphs = [
        p for p in body.findall(qn("p")) if p.find("./m:oMathPara", NS) is not None
    ]
    if len(equation_paragraphs) != 3:
        raise RuntimeError(f"Expected three display equations, found {len(equation_paragraphs)}")
    for number, source_p in enumerate(equation_paragraphs, start=1):
        eq_table = make_equation_table(equation_template, source_p, number)
        body.replace(source_p, eq_table)

    set_section_geometry(doc)
    enable_field_updates(settings)

    # Structural fidelity gates before writing the binary artifact.
    allowed_styles = defined_style_ids(styles)
    undefined_pstyles = sorted(
        {
            style_id
            for p in doc.xpath(".//w:p", namespaces=NS)
            if (style_id := pstyle(p)) and style_id not in allowed_styles
        }
    )
    undefined_tblstyles = sorted(
        {
            node.get(qn("val"))
            for node in doc.xpath(".//w:tblPr/w:tblStyle", namespaces=NS)
            if node.get(qn("val")) not in allowed_styles
        }
    )
    if undefined_pstyles or undefined_tblstyles:
        raise RuntimeError(
            f"Undefined styles remain: paragraphs={undefined_pstyles}, tables={undefined_tblstyles}"
        )

    final_text = "\n".join(paragraph_text(p) for p in doc.xpath(".//w:p", namespaces=NS))
    unresolved = re.findall(r"\[eq:[^\]]+\]|2-3\(lr\)4-5", final_text)
    if unresolved:
        raise RuntimeError(f"Unresolved internal tokens remain: {unresolved}")

    entries["word/document.xml"] = serialize_xml(doc)
    entries["word/settings.xml"] = serialize_xml(settings)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp_output = OUTPUT.with_suffix(".tmp.docx")
    if temp_output.exists():
        temp_output.unlink()
    with zipfile.ZipFile(temp_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
        for name, blob in entries.items():
            zout.writestr(name, blob)
    with zipfile.ZipFile(temp_output, "r") as check:
        bad = check.testzip()
        if bad:
            raise RuntimeError(f"Corrupt DOCX member after write: {bad}")
    shutil.move(temp_output, OUTPUT)

    return {
        "output": str(OUTPUT),
        "output_size": OUTPUT.stat().st_size,
        "template_sha256": sha256(TEMPLATE),
        "source_sha256": sha256(SOURCE),
        "output_sha256": sha256(OUTPUT),
        "table_captions": len(table_captions),
        "figure_captions": len(figure_captions),
        "references": len(reference_paragraphs),
        "equations": len(equation_paragraphs),
        "debris_removed": debris_count,
        "equation_refs_replaced": sum(eq_ref_counts.values()),
    }


if __name__ == "__main__":
    result = build()
    for key, value in result.items():
        print(f"{key}: {value}")
