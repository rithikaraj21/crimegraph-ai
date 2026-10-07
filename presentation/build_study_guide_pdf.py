import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "presentation" / "Project_Study_Guide.md"
OUTPUTS = [
    ROOT / "presentation" / "Project_Study_Guide.pdf",
    ROOT / "CrimeGraph_AI_Project_Guide.pdf",
]
QUICK_ANSWERS = ROOT / "CrimeGraph_AI_Viva_Quick_Answers.pdf"

NAVY = colors.HexColor("#14213A")
CYAN = colors.HexColor("#217E80")
MUTED = colors.HexColor("#586579")
PALE = colors.HexColor("#EDF3F8")
GRID = colors.HexColor("#D0D9E4")


def register_fonts():
    regular = Path(r"C:\Windows\Fonts\segoeui.ttf")
    bold = Path(r"C:\Windows\Fonts\segoeuib.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("GuideSans", str(regular)))
        pdfmetrics.registerFont(TTFont("GuideSans-Bold", str(bold)))
        pdfmetrics.registerFontFamily(
            "GuideSans",
            normal="GuideSans",
            bold="GuideSans-Bold",
            italic="GuideSans",
            boldItalic="GuideSans-Bold",
        )
        return "GuideSans", "GuideSans-Bold"
    return "Helvetica", "Helvetica-Bold"


def inline_markup(text):
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", escaped)
    return escaped


def create_styles(regular, bold):
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "GuideTitle",
            parent=base["Title"],
            fontName=bold,
            fontSize=21,
            leading=26,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "GuideH2",
            fontName=bold,
            fontSize=15.5,
            leading=19,
            textColor=NAVY,
            spaceBefore=13,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "GuideH3",
            fontName=bold,
            fontSize=11.5,
            leading=14,
            textColor=CYAN,
            spaceBefore=9,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "GuideBody",
            fontName=regular,
            fontSize=8.6,
            leading=11.8,
            textColor=colors.HexColor("#202B39"),
            spaceAfter=5,
            splitLongWords=True,
        ),
        "quote": ParagraphStyle(
            "GuideQuote",
            fontName=regular,
            fontSize=9,
            leading=12.2,
            textColor=NAVY,
            leftIndent=10,
            borderColor=CYAN,
            borderWidth=2,
            borderPadding=6,
            spaceBefore=3,
            spaceAfter=8,
        ),
        "list": ParagraphStyle(
            "GuideList",
            fontName=regular,
            fontSize=8.5,
            leading=11.3,
            textColor=colors.HexColor("#202B39"),
            leftIndent=15,
            firstLineIndent=-9,
            spaceAfter=3,
        ),
        "table": ParagraphStyle(
            "GuideTable",
            fontName=regular,
            fontSize=6.5,
            leading=8.3,
            textColor=colors.HexColor("#202B39"),
            splitLongWords=True,
        ),
        "table_header": ParagraphStyle(
            "GuideTableHeader",
            fontName=bold,
            fontSize=6.5,
            leading=8.3,
            textColor=colors.white,
            splitLongWords=True,
        ),
        "code": ParagraphStyle(
            "GuideCode",
            fontName="Courier",
            fontSize=7.1,
            leading=9.3,
            textColor=NAVY,
            backColor=PALE,
            borderColor=GRID,
            borderWidth=0.4,
            borderPadding=6,
            leftIndent=7,
            rightIndent=7,
            spaceBefore=3,
            spaceAfter=7,
        ),
    }


def is_table_row(line):
    return line.strip().startswith("|") and line.strip().endswith("|")


def split_cells(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def build_table(lines, page_width, styles):
    rows = [split_cells(line) for line in lines]
    rows = [
        row
        for row in rows
        if not row or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in row)
    ]
    if not rows:
        return None

    columns = max(len(row) for row in rows)
    normalized = [row + [""] * (columns - len(row)) for row in rows]
    formatted = []
    for row_index, row in enumerate(normalized):
        style = styles["table_header"] if row_index == 0 else styles["table"]
        formatted.append([Paragraph(inline_markup(cell), style) for cell in row])

    table = Table(formatted, colWidths=[page_width / columns] * columns, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("GRID", (0, 0), (-1, -1), 0.35, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def parse_markdown(path, page_width, styles):
    lines = path.read_text(encoding="utf-8").splitlines()
    story = []
    index = 0
    in_code = False
    code_lines = []

    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if not stripped:
            index += 1
            continue

        if stripped.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["code"]))
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(raw)
            index += 1
            continue

        if stripped.startswith("# "):
            story.append(Paragraph(inline_markup(stripped[2:]), styles["title"]))
            story.append(HRFlowable(width="100%", thickness=1.1, color=CYAN, spaceAfter=8))
            index += 1
            continue
        if stripped.startswith("## "):
            story.append(Paragraph(inline_markup(stripped[3:]), styles["h2"]))
            index += 1
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(inline_markup(stripped[4:]), styles["h3"]))
            index += 1
            continue
        if is_table_row(stripped):
            table_lines = []
            while index < len(lines) and is_table_row(lines[index].strip()):
                table_lines.append(lines[index])
                index += 1
            table = build_table(table_lines, page_width, styles)
            if table:
                story.extend([Spacer(1, 3), table, Spacer(1, 7)])
            continue
        if stripped.startswith("> "):
            quote = []
            while index < len(lines) and lines[index].strip().startswith("> "):
                quote.append(lines[index].strip()[2:])
                index += 1
            story.append(Paragraph(inline_markup(" ".join(quote)), styles["quote"]))
            continue
        if stripped.startswith("- ") or re.match(r"^\d+\.\s+", stripped):
            item_lines = []
            while index < len(lines):
                current = lines[index].strip()
                if current.startswith("- "):
                    item_lines.append("• " + current[2:])
                elif re.match(r"^\d+\.\s+", current):
                    item_lines.append(current)
                else:
                    break
                index += 1
            for item in item_lines:
                story.append(Paragraph(inline_markup(item), styles["list"]))
            continue

        paragraph = [stripped]
        index += 1
        while index < len(lines):
            following = lines[index].strip()
            if (
                not following
                or following.startswith(("#", "```", "> "))
                or is_table_row(following)
                or following.startswith("- ")
                or re.match(r"^\d+\.\s+", following)
            ):
                break
            paragraph.append(following)
            index += 1
        story.append(Paragraph(inline_markup(" ".join(paragraph)), styles["body"]))

    if in_code and code_lines:
        story.append(Preformatted("\n".join(code_lines), styles["code"]))
    return story


def footer(canvas, document, regular):
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.5)
    canvas.line(document.leftMargin, 0.48 * inch, width - document.rightMargin, 0.48 * inch)
    canvas.setFont(regular, 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(document.leftMargin, 0.3 * inch, "CrimeGraph AI | Classroom prototype | Synthetic data only")
    canvas.drawRightString(width - document.rightMargin, 0.3 * inch, f"Page {document.page}")
    canvas.restoreState()


def build_quick_answers(regular, bold):
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "QuickTitle",
            fontName=bold,
            fontSize=21,
            leading=24,
            textColor=NAVY,
            spaceAfter=5,
        ),
        "subtitle": ParagraphStyle(
            "QuickSubtitle",
            fontName=regular,
            fontSize=8.6,
            leading=11,
            textColor=MUTED,
            spaceAfter=8,
        ),
        "heading": ParagraphStyle(
            "QuickHeading",
            fontName=bold,
            fontSize=11,
            leading=13,
            textColor=CYAN,
            spaceBefore=5,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "QuickBody",
            fontName=regular,
            fontSize=8.1,
            leading=10.3,
            textColor=colors.HexColor("#202B39"),
            spaceAfter=4,
        ),
        "answer": ParagraphStyle(
            "QuickAnswer",
            fontName=regular,
            fontSize=7.8,
            leading=9.7,
            textColor=colors.HexColor("#202B39"),
            leftIndent=8,
            spaceAfter=3,
        ),
        "opening": ParagraphStyle(
            "QuickOpening",
            fontName=regular,
            fontSize=8.3,
            leading=11,
            textColor=NAVY,
            backColor=PALE,
            borderColor=CYAN,
            borderWidth=1,
            borderPadding=7,
            spaceBefore=4,
        ),
    }

    story = [
        Paragraph("CrimeGraph AI — Viva Quick Answers", styles["title"]),
        Paragraph(
            "Short, truthful answers you can say naturally. You do not need to memorize the technical detail in the full guide.",
            styles["subtitle"],
        ),
        Paragraph("Remember these five things", styles["heading"]),
    ]
    anchors = [
        "It organizes sample case information and shows possible links.",
        "The app uses two classifiers: network traffic and file samples.",
        "The default model training uses generated examples, not the original named datasets.",
        "High scores on generated data do not prove real-world accuracy.",
        "Real-data tests, validation, security, and durable storage are future work.",
    ]
    story.extend(
        Paragraph(f"<b>{index}.</b> {inline_markup(point)}", styles["body"])
        for index, point in enumerate(anchors, start=1)
    )
    story.append(Paragraph("Common questions", styles["heading"]))

    answers = [
        ("What does the project do?", "It puts sample case information in one place and shows possible links in a graph."),
        ("Which datasets did you use?", "Computer-generated examples. I did not train on the original CTU-13, IoT-23, or Govdocs1 datasets."),
        ("Why are the scores high?", "The generated examples have easy-to-recognize patterns; the scores are not real-world accuracy."),
        ("What models are used?", "One model checks network traffic; one classifies file samples. The traffic model is CNN-LSTM, and the file model is TF-IDF plus MLP."),
        ("What is an epoch?", "One complete pass through the training examples. The neural models were trained for 50 epochs."),
        ("What do Adam and loss do?", "Adam updates the model as it learns; loss measures its mistakes."),
        ("What are trainable parameters?", "They are the numbers the model adjusts while learning—like learned settings."),
        ("What do precision and recall mean?", "Precision: when it flags something, how often it is right? Recall: how much of what we seek did it find?"),
        ("What does the graph show?", "Possible links among sample records. A link is a lead to check, not proof."),
        ("Is it production-ready?", "No. It is a classroom prototype; real-data testing, stronger validation, login/security, and durable storage are future work."),
        ("Did you use AI to build it?", "Yes. I used AI assistance and have been learning how the parts work."),
    ]
    story.extend(
        Paragraph(f"<b>Q: {question}</b><br/>A: {answer}", styles["answer"])
        for question, answer in answers
    )
    story.append(Paragraph("A short opening you can practice", styles["heading"]))
    story.append(
        Paragraph(
            "“My project is called CrimeGraph AI. It organizes sample case information and shows possible links in a graph. "
            "It has one model for network traffic and one for file samples. I used generated training examples, so the scores "
            "do not tell us how accurate it would be on real cases. It is a classroom prototype, and real-data testing and "
            "security are future work.”",
            styles["opening"],
        )
    )

    document = SimpleDocTemplate(
        str(QUICK_ANSWERS),
        pagesize=letter,
        rightMargin=0.58 * inch,
        leftMargin=0.58 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.6 * inch,
        title="CrimeGraph AI Viva Quick Answers",
        author="CrimeGraph AI",
    )
    document.build(
        story,
        onFirstPage=lambda canvas, doc: footer(canvas, doc, regular),
        onLaterPages=lambda canvas, doc: footer(canvas, doc, regular),
    )
    print(f"Created {QUICK_ANSWERS} ({QUICK_ANSWERS.stat().st_size} bytes)")


def main():
    regular, bold = register_fonts()
    styles = create_styles(regular, bold)
    page_width = letter[0] - 1.05 * inch

    for output in OUTPUTS:
        story = parse_markdown(SOURCE, page_width, styles)
        document = SimpleDocTemplate(
            str(output),
            pagesize=letter,
            rightMargin=0.53 * inch,
            leftMargin=0.53 * inch,
            topMargin=0.58 * inch,
            bottomMargin=0.63 * inch,
            title="CrimeGraph AI: Complete Project and Viva Study Guide",
            author="CrimeGraph AI",
        )
        document.build(
            story,
            onFirstPage=lambda canvas, doc: footer(canvas, doc, regular),
            onLaterPages=lambda canvas, doc: footer(canvas, doc, regular),
        )
        print(f"Created {output} ({output.stat().st_size} bytes)")
    build_quick_answers(regular, bold)


if __name__ == "__main__":
    main()
