# MDPI Agronomy template contract

## Reference

- Retained reference: `C:/Users/zergu/repos/greenhouse-control/mdpi-template/agronomy-template.docx`
- SHA-256: `87a0d307c497cf8ed1cb6b108669d8cc1b6ea049bdb7198572f4080a38bb7768`
- Size: 81,948 bytes; six pages when exported by Microsoft Word 16.0.
- One section; all six rendered pages were inspected from `.codex-tmp/mdpi-review/template/`.
- Content type is Word template (`application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml`) despite the `.docx` suffix. The retained file is preserve-only.

## Page system

- A4 portrait, `11906 x 16838` twips.
- Margins: top 1417, right 720, bottom 907, left 720 twips; header 720, footer 612.
- Continuous line numbers, every line, distance 255 twips; page numbering begins at 1.
- Different first page is enabled. Preserve header/footer parts, journal/MDPI logos, horizontal rules, DOI placeholder, journal string, PAGE and NUMPAGES fields.

## Typography and paragraph roles

- Base face: Palatino Linotype, black, fully justified, line height at least 280 twips.
- `MDPI_1.1_article_type`: italic, 12 pt before.
- `MDPI_1.2_title`: Palatino Linotype 18 pt bold, 12 pt after, 12 pt minimum line.
- `MDPI_1.3_authornames`: bold, 18 pt after, 13 pt minimum line.
- `MDPI_1.6_affiliation`: 8 pt, left 2806 twips, hanging 198, 10 pt line.
- `MDPI_1.7_abstract`: left 2608 twips, 12 pt before, 6 pt after, 14 pt line; label bold inline.
- `MDPI_1.8_keywords`: left 2608 twips, 12 pt before, 14 pt line; label bold inline.
- `MDPI_1.9_line`: horizontal separator after keywords.
- `MDPI_2.1_heading1`: 12 pt bold, left 2608, 12 pt before, 3 pt after, outline level 0.
- `MDPI_2.2_heading2`: 11 pt italic, left 2608, 3 pt before/after, outline level 1.
- `MDPI_2.3_heading3`: 11 pt roman, left 2608, 3 pt before/after, outline level 2.
- `MDPI_3.1_text`: 11 pt, left 2608, first-line 425, justified, 14 pt line, no paragraph-after gap.
- `MDPI_3.2_text_no_indent`: same body rhythm without first-line indent.
- `MDPI_3.8_bullet` and `MDPI_3.7_itemize`: real numbering definitions from the template.
- `MDPI_4.1_table_caption`: 9 pt, left 2608, 12 pt before/6 pt after; literal `Table N.` bold.
- `MDPI_4.2_table_body`: Palatino, centered by default, 13 pt line; selective left alignment permitted for narrative columns.
- `MDPI_4.3_table_footer`: 9 pt.
- `MDPI_5.2_figure`: inline, centered.
- `MDPI_5.1_figure_caption`: 9 pt, left 2608, 6 pt before/12 pt after; literal `Figure N.` bold.
- `MDPI_6.2_back_matter`: 9 pt, left 2608, 6 pt after, 14 pt line; section label bold inline.
- `MDPI_8.1_references`: 9 pt, justified, real reference numbering (`numId 25`).

## Tables, figures, equations, and lists

- Data tables use the source three-line pattern: top rule, rule under the header, bottom rule; no vertical grid.
- Table width is 7920 twips for manuscript tables, explicit fixed grid and matching cell widths; first row repeats on page breaks; rows expand automatically.
- Cell margins are small but nonzero; header cells bold and centered; narrative cells left, short numeric cells centered.
- Captions precede tables and follow figures; keep captions with their table/figure.
- Figures remain inline, centered, un-stretched, and close to the first citation.
- Display equations are centered and receive sequential right-aligned numbers `(1)`, `(2)`, `(3)`; replace unresolved `[eq:*]` text with `Equation (n)`.
- Existing real list numbering is preserved and mapped to MDPI list roles where applicable.

## Content flow and slot map

1. Add article type `Article` before the title.
2. Preserve the scientific title and all article prose, tables, equations, figures, hyperlinks, and footnotes.
3. Rebuild the author/affiliation/correspondence block using MDPI roles while retaining explicit fill-in placeholders for unavailable personal data.
4. Keep the single-paragraph abstract (195 words) and seven keywords; apply MDPI roles and separator.
5. Number Heading 1 sections: 1 Introduction; 2 Materials and Methods; 3 Results; 4 Discussion; 5 Conclusions. Number Heading 2 subsections hierarchically by position.
6. Add `Table 1.` through `Table 16.` and `Figure 1.` through `Figure 6.` to captions. The sixth image is both the conclusion summary figure and graphical-abstract candidate; label it Figure 6 in the manuscript, with `Graphical Abstract` retained as a short lead-in where appropriate.
7. Keep back matter after Figure 6: Author Contributions, Funding, Institutional Review Board Statement, Informed Consent Statement, Data Availability Statement, Acknowledgments, Conflicts of Interest. Missing facts remain explicit bracketed fields and are not invented.
8. Format References with the MDPI reference style and real numbering while preserving all 44 entries and DOI hyperlinks.

## Package preservation

- Preserve source-derived `word/header*.xml`, `word/footer*.xml`, `word/theme/theme1.xml`, `word/fontTable.xml`, relationships to journal logos, footnotes, hyperlinks, comments plumbing, core document text, and all six manuscript figure media.
- Editable: `word/document.xml`, `word/styles.xml`, `word/numbering.xml`, `word/settings.xml`, `docProps/core.xml`, and only relationships required by existing manuscript content.
- The existing article package already contains byte-identical template headers, footers, theme, and font table. The edit therefore starts from a copy of the article, verifies those preserve-only hashes against the reference, and patches only editable parts.

## Fidelity and QA gates

- Retained reference SHA-256 must remain unchanged.
- Final section geometry, line numbering, logos, header/footer rules, and page fields must match the reference.
- No paragraph or table may reference an undefined style.
- All 16 table and six figure captions must carry visible numbered labels.
- No unresolved `[eq:*]`, generator debris such as `2-3(lr)4-5`, or internal citation tokens may remain.
- All final pages must be exported by Microsoft Word, rasterized, and inspected for clipping, overlap, broken tables, missing headers, awkward blank pages, or unreadable figures.
