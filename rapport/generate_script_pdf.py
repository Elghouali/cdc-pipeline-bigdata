"""
Convert script_presentation.md to a styled PDF.
Run: python rapport/generate_script_pdf.py
Output: rapport/script_presentation.pdf
"""

import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = HexColor("#1A1A1A")
ACCENT  = HexColor("#CF6C4F")
EMERALD = HexColor("#34D399")
AMBER   = HexColor("#FCD34D")
PURPLE  = HexColor("#A78BFA")
TEXT    = HexColor("#ECECEC")
DIM     = HexColor("#878787")
BORDER  = HexColor("#333333")
P1_CLR  = HexColor("#CF6C4F")
P2_CLR  = HexColor("#34D399")

W, H = A4

# ── Styles ────────────────────────────────────────────────────────────────────

def S(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE       = S("title",   fontSize=22, leading=28, textColor=TEXT,
                fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4)
SUBTITLE    = S("sub",     fontSize=10, leading=14, textColor=DIM,
                fontName="Helvetica", alignment=TA_CENTER, spaceAfter=3)
SLIDE_H     = S("slide_h", fontSize=13, leading=17, textColor=ACCENT,
                fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=4)
SEC_H       = S("sec_h",   fontSize=11, leading=15, textColor=PURPLE,
                fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3)
SPEAKER_P1  = S("sp1",     fontSize=10, leading=14, textColor=P1_CLR,
                fontName="Helvetica-Bold", spaceBefore=5, spaceAfter=2)
SPEAKER_P2  = S("sp2",     fontSize=10, leading=14, textColor=P2_CLR,
                fontName="Helvetica-Bold", spaceBefore=5, spaceAfter=2)
BODY        = S("body",    fontSize=9.5, leading=14, textColor=TEXT,
                fontName="Helvetica", spaceAfter=4, leftIndent=14)
TIP         = S("tip",     fontSize=9, leading=13, textColor=AMBER,
                fontName="Helvetica-Oblique", leftIndent=14, spaceAfter=3)
TH          = S("th",      fontSize=8, leading=11, textColor=ACCENT,
                fontName="Helvetica-Bold", alignment=TA_CENTER)
TD          = S("td",      fontSize=8, leading=11, textColor=TEXT,
                fontName="Helvetica", alignment=TA_CENTER)
FOOTER_S    = S("footer",  fontSize=7.5, leading=10, textColor=DIM,
                fontName="Helvetica", alignment=TA_CENTER)

# ── Markdown helpers ──────────────────────────────────────────────────────────

def inline(text: str) -> str:
    text = re.sub(r"`([^`]+)`",
                  r'<font name="Courier" color="#CF6C4F">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*",     r"<i>\1</i>", text)
    for src, dst in [("→","→"),("·","·"),("–","–"),("—","—"),("✓","✓")]:
        text = text.replace(src, dst)
    return text


def parse(md_path: str):
    items = []
    table_buf = []

    def flush_table():
        if table_buf:
            items.append(("table", table_buf[:]))
            table_buf.clear()

    with open(md_path, encoding="utf-8") as f:
        for line in f:
            raw = line.rstrip()

            if raw.startswith("|"):
                table_buf.append(raw)
                continue

            flush_table()

            if not raw:
                items.append(("space", ""))
            elif raw.startswith("---"):
                items.append(("hr", ""))
            elif raw.startswith("# "):
                items.append(("h1", raw[2:]))
            elif raw.startswith("## SLIDE"):
                items.append(("slide", raw[3:]))
            elif raw.startswith("## "):
                items.append(("h2", raw[3:]))
            elif raw.startswith("**P1"):
                items.append(("p1", ""))
            elif raw.startswith("**P2"):
                items.append(("p2", ""))
            elif raw.startswith("> "):
                items.append(("tip", raw[2:]))
            else:
                items.append(("body", raw))

    flush_table()
    return items


def make_table(rows):
    data = []
    for i, row in enumerate(rows):
        if re.match(r"^\|[-| :]+\|$", row):
            continue
        cells = [c.strip() for c in row.strip("|").split("|")]
        sty = TH if i == 0 else TD
        data.append([Paragraph(inline(c), sty) for c in cells])
    if not data:
        return None
    ncols = max(len(r) for r in data)
    cw = (W - 4 * cm) / ncols
    t = Table(data, colWidths=[cw] * ncols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",      (0, 0), (-1, 0),  HexColor("#2A2A2A")),
        ("ROWBACKGROUNDS",  (0, 1), (-1, -1), [HexColor("#1E1E1E"),
                                               HexColor("#232323")]),
        ("GRID",            (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",      (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",   (0, 0), (-1, -1), 5),
        ("LEFTPADDING",     (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",    (0, 0), (-1, -1), 6),
        ("VALIGN",          (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t

# ── PDF builder ───────────────────────────────────────────────────────────────

def generate(md_path: str, out_path: str):
    items  = parse(md_path)
    story  = []

    # ── Cover ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.0 * cm))
    story.append(Paragraph("CDC Pipeline", TITLE))
    story.append(Paragraph("Script de Présentation", SUBTITLE))
    story.append(Paragraph(
        "ENSET Mohammedia  ·  Module Big Data  ·  2025–2026", SUBTITLE))
    story.append(Spacer(1, 0.25 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5,
                            color=ACCENT, spaceAfter=12))

    for kind, text in items:
        if kind == "h1":
            pass
        elif kind == "h2":
            story.append(Paragraph(inline(text), SEC_H))
        elif kind == "slide":
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=BORDER, spaceBefore=6, spaceAfter=4))
            story.append(Paragraph(
                f'<font color="#CF6C4F">◆</font>  {inline(text)}',
                SLIDE_H))
        elif kind == "p1":
            story.append(Paragraph(
                '<font color="#CF6C4F">▶  P1 — Zakaria Elghouali</font>',
                SPEAKER_P1))
        elif kind == "p2":
            story.append(Paragraph(
                '<font color="#34D399">▶  P2 — Binôme</font>',
                SPEAKER_P2))
        elif kind == "body":
            if text.strip():
                story.append(Paragraph(inline(text), BODY))
        elif kind == "tip":
            story.append(Paragraph(f"  {inline(text)}", TIP))
        elif kind == "hr":
            story.append(Spacer(1, 0.1 * cm))
        elif kind == "space":
            story.append(Spacer(1, 0.18 * cm))
        elif kind == "table":
            t = make_table(text)
            if t:
                story.append(Spacer(1, 0.15 * cm))
                story.append(t)
                story.append(Spacer(1, 0.25 * cm))

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(
        "Zakaria Elghouali  ·  zakariaelgouali@gmail.com  ·  ENSET Mohammedia",
        FOOTER_S))

    # ── Page canvas (dark background + bars) ──────────────────────────────
    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BG)
        canvas.rect(0, 0, W, H, fill=1, stroke=0)
        canvas.setFillColor(ACCENT)
        canvas.rect(0, H - 5, W, 5, fill=1, stroke=0)   # top accent bar
        canvas.setFillColor(HexColor("#242424"))
        canvas.rect(0, 0, W, 20, fill=1, stroke=0)       # bottom bar
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(DIM)
        canvas.drawCentredString(W / 2, 6, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.6 * cm, bottomMargin=1.5 * cm,
        title="Script Présentation CDC Pipeline",
        author="Zakaria Elghouali",
    )
    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    print(f"Saved → {out_path}")


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    generate(
        os.path.join(base, "script_presentation.md"),
        os.path.join(base, "script_presentation.pdf"),
    )
