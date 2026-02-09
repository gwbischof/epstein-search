"""PDF generation utilities for markdown reports."""

import re
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, grey
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable,
)

WIDTH, HEIGHT = letter
MARGIN = 0.75 * inch


# ── Single-file PDF generation (from generate_pdf.py) ───────────────────


def _gen_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "DocTitle", parent=styles["Title"], fontSize=15, spaceAfter=6,
        textColor=HexColor("#1a1a1a"),
    ))
    styles.add(ParagraphStyle(
        "Section", parent=styles["Heading2"], fontSize=13, spaceBefore=18,
        spaceAfter=6, textColor=HexColor("#2c3e50"),
    ))
    styles.add(ParagraphStyle(
        "SubSection", parent=styles["Heading3"], fontSize=11, spaceBefore=12,
        spaceAfter=4, textColor=HexColor("#34495e"),
    ))
    styles.add(ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=9.5, leading=13, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "BulletItem", parent=styles["Normal"], fontSize=9.5, leading=13,
        leftIndent=20, bulletIndent=8, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        "GenTableCell", parent=styles["Normal"], fontSize=8, leading=10,
    ))
    styles.add(ParagraphStyle(
        "GenTableHeader", parent=styles["Normal"], fontSize=8, leading=10,
        fontName="Helvetica-Bold", textColor=HexColor("#ffffff"),
    ))
    return styles


_GEN_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2c3e50")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
     [HexColor("#ffffff"), HexColor("#f2f3f4")]),
    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
])


def _md_inline(text):
    """Convert markdown inline formatting to reportlab XML."""
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" color="#2980b9">\1</a>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)
    text = re.sub(r'`([^`]+)`', r'<font face="Courier">\1</font>', text)
    text = re.sub(r'&(?!amp;|lt;|gt;|quot;|#)', '&amp;', text)
    return text


def _gen_parse_table(lines):
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    if len(rows) > 1 and all(re.match(r'^[-:]+$', c) for c in rows[1]):
        rows.pop(1)
    return rows


def _md_to_story(md_text, styles):
    story = []
    lines = md_text.split("\n")
    i = 0
    title_added = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("# ") and not title_added:
            story.append(Paragraph(_md_inline(stripped[2:]), styles["DocTitle"]))
            story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#2c3e50")))
            story.append(Spacer(1, 8))
            title_added = True
            i += 1
            continue

        if stripped.startswith("## "):
            story.append(Paragraph(_md_inline(stripped[3:]), styles["Section"]))
            i += 1
            continue

        if stripped.startswith("### ") or stripped.startswith("#### "):
            level = 4 if stripped.startswith("####") else 3
            story.append(Paragraph(_md_inline(stripped[level + 1:]), styles["SubSection"]))
            i += 1
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            rows = _gen_parse_table(table_lines)
            if rows:
                h = styles["GenTableHeader"]
                c = styles["GenTableCell"]
                data = []
                for ri, row in enumerate(rows):
                    s = h if ri == 0 else c
                    data.append([Paragraph(_md_inline(cell), s) for cell in row])
                ncols = len(data[0]) if data else 1
                available = 7.0 * inch
                col_w = [available / ncols] * ncols
                t = Table(data, colWidths=col_w, repeatRows=1)
                t.setStyle(_GEN_TABLE_STYLE)
                story.append(t)
                story.append(Spacer(1, 6))
            continue

        if stripped.startswith("- "):
            story.append(Paragraph(
                f"\u2022 {_md_inline(stripped[2:])}", styles["BulletItem"],
            ))
            i += 1
            continue

        m = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if m:
            story.append(Paragraph(
                f"{m.group(1)}. {_md_inline(m.group(2))}", styles["BulletItem"],
            ))
            i += 1
            continue

        para_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (not nxt or nxt.startswith("#") or nxt.startswith("|")
                    or nxt.startswith("- ") or re.match(r'^\d+\.\s+', nxt)):
                break
            para_lines.append(nxt)
            i += 1
        story.append(Paragraph(_md_inline(" ".join(para_lines)), styles["Body"]))

    return story


def generate_pdf(md_path: str, pdf_path: str | None = None) -> str:
    """Convert a single markdown file to a styled PDF.

    Returns the output PDF path.
    """
    md_text = Path(md_path).read_text()
    if pdf_path is None:
        pdf_path = str(Path(md_path).with_suffix(".pdf"))

    styles = _gen_styles()
    story = _md_to_story(md_text, styles)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=letter,
        topMargin=MARGIN, bottomMargin=MARGIN,
        leftMargin=MARGIN, rightMargin=MARGIN,
    )
    doc.build(story)
    return pdf_path


# ── Multi-file merge (from build_pdf.py) ────────────────────────────────


def _merge_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "MDH1", parent=styles["Heading1"], fontSize=18, spaceAfter=12,
        spaceBefore=20, textColor=HexColor("#1a1a1a"),
    ))
    styles.add(ParagraphStyle(
        "MDH2", parent=styles["Heading2"], fontSize=14, spaceAfter=8,
        spaceBefore=16, textColor=HexColor("#2a2a2a"),
    ))
    styles.add(ParagraphStyle(
        "MDH3", parent=styles["Heading3"], fontSize=12, spaceAfter=6,
        spaceBefore=12, textColor=HexColor("#333333"),
    ))
    styles.add(ParagraphStyle(
        "MDBody", parent=styles["Normal"], fontSize=9.5, leading=13,
        spaceAfter=6, spaceBefore=2,
    ))
    styles.add(ParagraphStyle(
        "MDBlockquote", parent=styles["Normal"], fontSize=9.5, leading=13,
        leftIndent=24, spaceAfter=6, spaceBefore=4,
        textColor=HexColor("#444444"), borderColor=HexColor("#cccccc"),
        borderWidth=0, borderPadding=0,
    ))
    styles.add(ParagraphStyle(
        "MDListItem", parent=styles["Normal"], fontSize=9.5, leading=13,
        leftIndent=24, bulletIndent=12, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        "MergeTableCell", parent=styles["Normal"], fontSize=8, leading=10,
        spaceAfter=0, spaceBefore=0,
    ))
    styles.add(ParagraphStyle(
        "MergeTableHeader", parent=styles["Normal"], fontSize=8, leading=10,
        spaceAfter=0, spaceBefore=0, textColor=HexColor("#ffffff"),
    ))
    styles.add(ParagraphStyle(
        "Severity", parent=styles["Normal"], fontSize=10, leading=13,
        spaceAfter=6, spaceBefore=2, textColor=HexColor("#cc0000"),
    ))
    return styles


def _clean(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'`(.+?)`', r'<font face="Courier" size="8">\1</font>', text)
    return text


def _merge_parse_table(lines, styles):
    rows = []
    for i, line in enumerate(lines):
        line = line.strip().strip("|")
        cells = [c.strip() for c in line.split("|")]
        if i == 1 and all(set(c.strip()) <= set("-: ") for c in cells):
            continue
        rows.append(cells)
    if not rows:
        return None

    table_data = []
    for i, row in enumerate(rows):
        style = "MergeTableHeader" if i == 0 else "MergeTableCell"
        table_data.append([Paragraph(_clean(c), styles[style]) for c in row])

    ncols = max(len(r) for r in table_data)
    for r in table_data:
        while len(r) < ncols:
            r.append(Paragraph("", styles["MergeTableCell"]))

    avail = WIDTH - 2 * MARGIN
    col_w = avail / ncols

    t = Table(table_data, colWidths=[col_w] * ncols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#3a3a3a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f5f5f5")]),
    ]))
    return t


def _md_to_flowables(md_text, styles):
    flowables = []
    lines = md_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped in ("---", "***", "___"):
            flowables.append(Spacer(1, 6))
            flowables.append(HRFlowable(width="100%", thickness=1, color=grey))
            flowables.append(Spacer(1, 6))
            i += 1
            continue

        if stripped.startswith("#"):
            m = re.match(r'^(#{1,6})\s+(.*)', stripped)
            if m:
                level = len(m.group(1))
                text = _clean(m.group(2))
                if level == 1:
                    flowables.append(Paragraph(text, styles["MDH1"]))
                elif level == 2:
                    flowables.append(Paragraph(text, styles["MDH2"]))
                else:
                    flowables.append(Paragraph(text, styles["MDH3"]))
                i += 1
                continue

        if "|" in stripped and i + 1 < len(lines) and "|" in lines[i + 1]:
            table_lines = []
            while i < len(lines) and "|" in lines[i].strip():
                table_lines.append(lines[i])
                i += 1
            t = _merge_parse_table(table_lines, styles)
            if t:
                flowables.append(Spacer(1, 6))
                flowables.append(t)
                flowables.append(Spacer(1, 6))
            continue

        if stripped.startswith(">"):
            bq_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                bq_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            text = _clean(" ".join(bq_lines))
            flowables.append(Paragraph(
                f'<font color="#888888">|</font>&nbsp;&nbsp;{text}',
                styles["MDBlockquote"],
            ))
            continue

        if stripped.startswith("**Severity:"):
            flowables.append(Paragraph(_clean(stripped), styles["Severity"]))
            i += 1
            continue

        if re.match(r'^[-*]\s', stripped):
            while i < len(lines) and re.match(r'^\s*[-*]\s', lines[i].strip()):
                item = re.sub(r'^\s*[-*]\s+', '', lines[i].strip())
                flowables.append(Paragraph(
                    f'&bull;&nbsp;&nbsp;{_clean(item)}', styles["MDListItem"],
                ))
                i += 1
            continue

        if re.match(r'^\d+\.\s', stripped):
            while i < len(lines) and re.match(r'^\s*\d+\.\s', lines[i].strip()):
                item = re.sub(r'^\s*\d+\.\s+', '', lines[i].strip())
                m2 = re.match(r'^\s*(\d+)\.\s', lines[i].strip())
                num = m2.group(1) if m2 else "1"
                flowables.append(Paragraph(
                    f'{num}.&nbsp;&nbsp;{_clean(item)}', styles["MDListItem"],
                ))
                i += 1
            continue

        para_lines = []
        while i < len(lines):
            s = lines[i].strip()
            if not s:
                break
            if s.startswith("#") or s.startswith(">") or s in ("---", "***", "___"):
                break
            if s.startswith("**Severity:"):
                break
            if re.match(r'^[-*]\s', s) or re.match(r'^\d+\.\s', s):
                break
            if "|" in s and i + 1 < len(lines) and "|" in lines[i + 1].strip():
                break
            para_lines.append(s)
            i += 1

        if para_lines:
            text = _clean(" ".join(para_lines))
            flowables.append(Paragraph(text, styles["MDBody"]))

    return flowables


def _add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(grey)
    canvas.drawCentredString(WIDTH / 2, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def merge_markdown_to_pdf(md_paths: list[str], output_path: str) -> str:
    """Merge multiple markdown files into a single PDF with page breaks.

    Returns the output PDF path.
    """
    styles = _merge_styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    story = []

    for idx, md_path in enumerate(md_paths):
        md_text = Path(md_path).read_text()
        if idx > 0:
            story.append(PageBreak())
        story.extend(_md_to_flowables(md_text, styles))

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    return output_path
