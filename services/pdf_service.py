import io
import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import os

# Try to register a font that supports Cyrillic
FONT_NAME = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"

# Try to find and register a Cyrillic font
_font_registered = False
_possible_fonts = [
    ("DejaVuSans", "DejaVuSans.ttf"),
    ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"),
]
_font_dirs = [
    "C:/Windows/Fonts",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/TTF",
    os.path.join(os.path.dirname(__file__), "fonts"),
]

for font_dir in _font_dirs:
    regular = os.path.join(font_dir, "DejaVuSans.ttf")
    bold = os.path.join(font_dir, "DejaVuSans-Bold.ttf")
    if os.path.exists(regular):
        try:
            pdfmetrics.registerFont(TTFont("DejaVuSans", regular))
            FONT_NAME = "DejaVuSans"
            if os.path.exists(bold):
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold))
                FONT_NAME_BOLD = "DejaVuSans-Bold"
            else:
                FONT_NAME_BOLD = "DejaVuSans"
            _font_registered = True
            break
        except Exception:
            pass

# Fallback: try Arial on Windows
if not _font_registered:
    arial_path = "C:/Windows/Fonts/arial.ttf"
    arial_bold_path = "C:/Windows/Fonts/arialbd.ttf"
    if os.path.exists(arial_path):
        try:
            pdfmetrics.registerFont(TTFont("Arial", arial_path))
            FONT_NAME = "Arial"
            if os.path.exists(arial_bold_path):
                pdfmetrics.registerFont(TTFont("Arial-Bold", arial_bold_path))
                FONT_NAME_BOLD = "Arial-Bold"
            else:
                FONT_NAME_BOLD = "Arial"
            _font_registered = True
        except Exception:
            pass


def _get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="RuTitle", fontName=FONT_NAME_BOLD, fontSize=18,
        alignment=TA_CENTER, spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        name="RuHeading", fontName=FONT_NAME_BOLD, fontSize=13,
        spaceAfter=8, spaceBefore=12
    ))
    styles.add(ParagraphStyle(
        name="RuBody", fontName=FONT_NAME, fontSize=10,
        alignment=TA_JUSTIFY, spaceAfter=6, leading=14
    ))
    styles.add(ParagraphStyle(
        name="RuBodyCenter", fontName=FONT_NAME, fontSize=10,
        alignment=TA_CENTER, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="RuSmall", fontName=FONT_NAME, fontSize=8,
        alignment=TA_LEFT, spaceAfter=4
    ))
    return styles


def generate_resume_pdf(resume_data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = _get_styles()
    story = []

    # Name
    name = resume_data.get("full_name", "")
    story.append(Paragraph(name, styles["RuTitle"]))

    # Contact info
    contacts = []
    if resume_data.get("email"):
        contacts.append(resume_data["email"])
    if resume_data.get("phone"):
        contacts.append(resume_data["phone"])
    if resume_data.get("city"):
        contacts.append(resume_data["city"])
    if contacts:
        story.append(Paragraph(" | ".join(contacts), styles["RuBodyCenter"]))

    story.append(Spacer(1, 12))

    # Bio
    if resume_data.get("bio"):
        story.append(Paragraph("О себе", styles["RuHeading"]))
        story.append(Paragraph(resume_data["bio"], styles["RuBody"]))

    # Work experience
    if resume_data.get("experience"):
        story.append(Paragraph("Опыт работы", styles["RuHeading"]))
        for exp in resume_data["experience"]:
            title = f"<b>{exp.get('position', '')}</b> — {exp.get('company', '')}"
            period = f"{exp.get('start', '')} — {exp.get('end', 'по настоящее время')}"
            story.append(Paragraph(title, styles["RuBody"]))
            story.append(Paragraph(period, styles["RuSmall"]))
            if exp.get("description"):
                story.append(Paragraph(exp["description"], styles["RuBody"]))
            story.append(Spacer(1, 4))

    # Education
    if resume_data.get("education"):
        story.append(Paragraph("Образование", styles["RuHeading"]))
        for edu in resume_data["education"]:
            title = f"<b>{edu.get('institution', '')}</b>"
            details = f"{edu.get('degree', '')} — {edu.get('field', '')}"
            period = f"{edu.get('start', '')} — {edu.get('end', '')}"
            story.append(Paragraph(title, styles["RuBody"]))
            story.append(Paragraph(details, styles["RuBody"]))
            story.append(Paragraph(period, styles["RuSmall"]))
            story.append(Spacer(1, 4))

    # Skills
    if resume_data.get("skills"):
        story.append(Paragraph("Навыки", styles["RuHeading"]))
        story.append(Paragraph(resume_data["skills"], styles["RuBody"]))

    # Languages
    if resume_data.get("languages"):
        story.append(Paragraph("Языки", styles["RuHeading"]))
        story.append(Paragraph(resume_data["languages"], styles["RuBody"]))

    doc.build(story)
    return buffer.getvalue()


def generate_contract_pdf(contract_text: str, contract_data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = _get_styles()
    story = []

    story.append(Paragraph("ТРУДОВОЙ ДОГОВОР", styles["RuTitle"]))
    story.append(Paragraph(
        f"г. {contract_data.get('city', '_____')}    «{datetime.datetime.now().strftime('%d.%m.%Y')}»",
        styles["RuBodyCenter"]
    ))
    story.append(Spacer(1, 20))

    # Split contract text into paragraphs
    for para in contract_text.split("\n"):
        para = para.strip()
        if para:
            story.append(Paragraph(para, styles["RuBody"]))

    story.append(Spacer(1, 30))
    story.append(Paragraph("Подписи сторон:", styles["RuHeading"]))
    story.append(Spacer(1, 20))

    sign_data = [
        ["Работодатель:", "Работник:"],
        ["_________________", "_________________"],
        [contract_data.get("company_name", ""), contract_data.get("employee_name", "")],
    ]
    sign_table = Table(sign_data, colWidths=[8*cm, 8*cm])
    sign_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(sign_table)

    doc.build(story)
    return buffer.getvalue()


def generate_payroll_pdf(payroll_data: list[dict], company_name: str, month: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1*cm, rightMargin=1*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = _get_styles()
    story = []

    story.append(Paragraph(f"Платёжная ведомость — {company_name}", styles["RuTitle"]))
    story.append(Paragraph(f"Период: {month}", styles["RuBodyCenter"]))
    story.append(Spacer(1, 15))

    header = ["Сотрудник", "Оклад", "Премия", "Доплаты", "Удержания", "Аванс", "К выплате"]
    data = [header]
    for p in payroll_data:
        data.append([
            p.get("employee_name", ""),
            f"{p.get('base_salary', 0):,.0f}",
            f"{p.get('bonus', 0):,.0f}",
            f"{p.get('additional', 0):,.0f}",
            f"{p.get('deductions', 0):,.0f}",
            f"{p.get('advance', 0):,.0f}",
            f"{p.get('net_salary', 0):,.0f}",
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTNAME", (0, 0), (-1, 0), FONT_NAME_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    doc.build(story)
    return buffer.getvalue()


def generate_enps_report_pdf(enps_data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = _get_styles()
    story = []

    story.append(Paragraph("Отчёт eNPS", styles["RuTitle"]))
    story.append(Paragraph(
        f"Компания: {enps_data.get('company_name', '')}",
        styles["RuBodyCenter"]
    ))
    story.append(Spacer(1, 15))

    score = enps_data.get("enps_score", 0)
    story.append(Paragraph(f"Показатель eNPS: <b>{score}</b>", styles["RuHeading"]))
    story.append(Paragraph(
        f"Всего ответов: {enps_data.get('total_responses', 0)}",
        styles["RuBody"]
    ))
    story.append(Paragraph(
        f"Сторонники (9-10): {enps_data.get('promoters', 0)}%",
        styles["RuBody"]
    ))
    story.append(Paragraph(
        f"Нейтральные (7-8): {enps_data.get('passives', 0)}%",
        styles["RuBody"]
    ))
    story.append(Paragraph(
        f"Критики (0-6): {enps_data.get('detractors', 0)}%",
        styles["RuBody"]
    ))

    doc.build(story)
    return buffer.getvalue()
