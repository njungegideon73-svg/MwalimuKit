"""report_card_generator.py

Multi-tenant PDF report card generator. The school identity (name, address,
phone, email, crest, stamp, and brand color) is NEVER hardcoded — every
report card is rendered entirely from a `SchoolConfig` object you build per
school (e.g. from a `schools` table row). Point the same function at two
different `SchoolConfig` instances and you get two differently branded
report cards, with everything else (chart, tables, comments, footer)
following the same layout.

Layout matched: header with crest, student info block, a student-vs-class
performance chart, summary stat boxes, a subjects table, pathway mean
scores, comments, term dates, and stamp/QR footer.

Dependencies:
    pip install reportlab matplotlib qrcode --break-system-packages

Usage (single school):
    from report_card_generator import generate_report_card_pdf, SchoolConfig

    school = SchoolConfig(name="...", po_box="...", phone="...", email="...")
    pdf_path = generate_report_card_pdf(school, student_data,
                                         subjects, pathways, output_path)

Usage (multi-tenant, e.g. inside a Flask/Django view):
    school = build_school_config(get_school_row_from_db(school_id))
    pdf_path = generate_report_card_pdf(school, student_data,
                                         subjects, pathways, output_path)
"""

import io
import os
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --------------------------------------------------------------------------
# Theme constants -- fallbacks only. Override per school via SchoolConfig.
# --------------------------------------------------------------------------

DEFAULT_ACCENT = colors.HexColor("#2AA9BF")
DEFAULT_ACCENT_DARK = colors.HexColor("#1D7E90")
LIGHT_GREY = colors.HexColor("#F4F4F4")
BORDER_GREY = colors.HexColor("#BFBFBF")
TEXT_DARK = colors.HexColor("#2B2B2B")

PAGE_W, PAGE_H = A4

MARGIN = 5 * mm  # was 8mm -- shrinking slimmed the page w/o touching design
ACCENT_BAR_W = 6 * mm  # left vertical color strip

HEADER_MAX_SPACE = 442.0  # pt: horizontal room for the centered school name


# --------------------------------------------------------------------------
# Data containers -- swap these for your ORM models / dicts as needed
# --------------------------------------------------------------------------


@dataclass
class SchoolConfig:
    """Everything that makes a report card 'belong' to one school. Build one
    instance of this per school -- e.g. one row in your `schools` table --
    and pass the right instance in for whichever student's report you're
    rendering. No school name, color, or contact detail is ever hardcoded
    in the rendering functions; it all flows through this object."""

    name: str
    po_box: str
    phone: str
    email: str
    logo_path: str | None = None  # crest image, ~40x40mm square
    stamp_path: str | None = None  # official stamp image (optional)
    analytics_platform: str = "Zeraki Analytics"
    accent_color: colors.Color = DEFAULT_ACCENT
    accent_color_dark: colors.Color = DEFAULT_ACCENT_DARK


def build_school_config(school_row: dict) -> SchoolConfig:
    """Maps a row from your `schools` table (or any dict-like record) into a
    `SchoolConfig`. Adjust the key names to match your schema.

    Expected keys (all optional except name/po_box/phone/email):
        name, po_box, phone, email, logo_path, stamp_path,
        analytics_platform, accent_color_hex, accent_color_dark_hex
    """
    accent = (
        colors.HexColor(school_row["accent_color_hex"])
        if school_row.get("accent_color_hex")
        else DEFAULT_ACCENT
    )
    accent_dark = (
        colors.HexColor(school_row["accent_color_dark_hex"])
        if school_row.get("accent_color_dark_hex")
        else DEFAULT_ACCENT_DARK
    )
    return SchoolConfig(
        name=school_row["name"],
        po_box=school_row["po_box"],
        phone=school_row["phone"],
        email=school_row["email"],
        logo_path=school_row.get("logo_path"),
        stamp_path=school_row.get("stamp_path"),
        analytics_platform=school_row.get("analytics_platform", "Zeraki Analytics"),
        accent_color=accent,
        accent_color_dark=accent_dark,
    )


@dataclass
class StudentData:
    name: str
    admission_no: str
    grade: str
    term_label: str  # e.g. "GRADE 10 - END OF TERM TWO COMBINED - (2026 TERM 2)"
    photo_path: str | None = None
    performance_level: str = ""
    performance_rank: str = "0"
    total_marks: str = ""  # "285/700"
    total_marks_rank: str = "0"
    total_points: str = ""  # "30/56"
    total_points_rank: str = "0"
    class_teacher_name: str = ""
    class_teacher_remark: str = ""
    principal_name: str = ""
    principal_remark: str = ""
    term_ends: str = ""
    next_term_begins: str = ""


@dataclass
class SubjectRow:
    subject: str
    cat1: float  # percent
    end_term: float  # percent
    marks: float  # percent (combined)
    deviation: str = "--"
    grade: str = ""
    comment: str = ""
    teacher: str = ""
    is_support_subject: bool = False  # renders under "SUPPORT SUBJECTS" sub-header


@dataclass
class PathwayScore:
    label: str
    mean_score: float


# --------------------------------------------------------------------------
# Chart: student vs class-average line chart
# --------------------------------------------------------------------------


def _build_performance_chart(
    subjects: list, class_avg: list | None = None, width_in=7.6, height_in=0.9
) -> io.BytesIO:
    """Renders the 'Subject Performance - Student vs Class' line chart to a
    PNG buffer for embedding. `class_avg` should be a list the same length
    as `subjects`; if omitted, a flat placeholder line is drawn.

    The chart is drawn on a single line of tick labels, so it can be kept
    short without losing legibility -- this is what keeps the report card on
    one page.
    """
    labels = [s.subject_code for s in subjects]
    student_vals = [s.marks for s in subjects]
    class_vals = (
        class_avg if class_avg else [sum(student_vals) / len(student_vals)] * len(student_vals)
    )

    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=200)
    ax.plot(
        labels,
        student_vals,
        marker="o",
        markersize=3.2,
        linewidth=1.5,
        color="#4C5B6B",
        label="Student",
    )
    ax.plot(
        labels,
        class_vals,
        marker="o",
        markersize=3.2,
        linewidth=1.5,
        color="#8FBF3F",
        label="Class",
    )

    ax.set_ylim(0, max(10, max(student_vals + class_vals) * 1.18))
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="both", labelsize=6, length=2, pad=1)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.22),
        ncol=2,
        fontsize=6,
        frameon=False,
        handlelength=1.2,
        borderaxespad=0.1,
        handletextpad=0.3,
        columnspacing=0.9,
    )
    fig.tight_layout(pad=0.25)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


@dataclass
class ChartSubjectPoint:
    subject_code: str
    marks: float


# --------------------------------------------------------------------------
# QR code helper
# --------------------------------------------------------------------------


def _build_qr_code(data: str, box_size=4) -> io.BytesIO:
    qr = qrcode.QRCode(border=1, box_size=box_size)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# --------------------------------------------------------------------------
# Layout helpers
# --------------------------------------------------------------------------


def _auto_fit_name(
    name: str, avail_width: float, max_size: float = 12.5, min_size: float = 9.0
) -> float:
    """Shrink the school name so it always fits on ONE line inside
    `avail_width`. This is what stops the name wrapping down onto the
    P.O. Box / phone / email lines and colliding with them."""
    font = "Helvetica-Bold"
    size = max_size
    while size > min_size and stringWidth(name, font, size) > avail_width:
        size -= 0.25
    return size


def _teal_banner(text: str, width, accent_color, height=5 * mm, font_size=8):
    """A full-width accent banner with centered white bold text, used for the
    report title and the COMMENTS divider."""
    style = ParagraphStyle(
        "Banner",
        fontName="Helvetica-Bold",
        fontSize=font_size,
        textColor=colors.white,
        alignment=TA_CENTER,
        leading=font_size + 1,
    )
    tbl = Table([[Paragraph(text, style)]], colWidths=[width], rowHeights=[height])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), accent_color),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return tbl


def _stat_box(label: str, value: str, secondary: str | None, width):
    label_style = ParagraphStyle(
        "StatLabel", fontName="Helvetica", fontSize=7, textColor=colors.grey
    )
    value_style = ParagraphStyle(
        "StatValue", fontName="Helvetica-Bold", fontSize=11, textColor=TEXT_DARK
    )
    value_text = value if not secondary else f"{value}  &rarr;  {secondary}"
    cell = [
        Paragraph(label, label_style),
        Spacer(1, 1.5),
        Paragraph(value_text, value_style),
    ]
    tbl = Table([[cell]], colWidths=[width])
    tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, BORDER_GREY),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return tbl


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------


def generate_report_card_pdf(
    school: SchoolConfig,
    student: StudentData,
    subjects: list,
    pathways: list,
    output_path: str,
    chart_subjects: list | None = None,
    class_avg: list | None = None,
    qr_data: str | None = None,
) -> str:
    """
    Build the report card PDF and write it to `output_path`.

    subjects: list[SubjectRow]
    pathways: list[PathwayScore]
    chart_subjects: list[ChartSubjectPoint] (defaults to derived from `subjects`)
    Returns the output_path for convenience.

    The layout is tuned to fit on a single A4 page: margins are slim, the
    chart is short, and every spacer/padding is kept minimal. If a school
    name is longer than the header space, it is auto-shrunk to stay on one
    line so it never overlaps the address/contact block below it.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN + ACCENT_BAR_W,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    content_width = A4[0] - doc.leftMargin - doc.rightMargin

    story = []

    # ---- Header: crest + school name/contact -----------------------------
    # Middle column is the only place the identity text can live, so it gets
    # the full remaining width and the name is auto-fit to that width.
    side_col = 18 * mm
    text_col = content_width - 2 * side_col
    name_font_size = _auto_fit_name(school.name.upper(), text_col)

    logo_flow = (
        Image(school.logo_path, width=14 * mm, height=14 * mm)
        if school.logo_path and os.path.exists(school.logo_path)
        else Spacer(14 * mm, 14 * mm)
    )

    name_style = ParagraphStyle(
        "SchoolName",
        fontName="Helvetica-Bold",
        fontSize=name_font_size,
        alignment=TA_CENTER,
        textColor=TEXT_DARK,
        leading=name_font_size * 1.25,
        spaceAfter=3,
    )
    contact_style = ParagraphStyle(
        "SchoolContact",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        alignment=TA_CENTER,
        textColor=TEXT_DARK,
        leading=10.5,
    )
    contact_lines = [
        f"P.O. Box {school.po_box}",
        f"Phone: {school.phone}",
        f"Email: {school.email}",
    ]
    header_text = [
        Paragraph(school.name.upper(), name_style),
        Paragraph("<br/>".join(contact_lines), contact_style),
    ]
    header_tbl = Table(
        [[logo_flow, header_text, Spacer(side_col, 14 * mm)]],
        colWidths=[side_col, text_col, side_col],
    )
    header_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(header_tbl)
    story.append(Spacer(1, 2 * mm))

    # ---- Title banner -----------------------------------------------------
    story.append(
        _teal_banner(
            f"ACADEMIC REPORT FORM - {student.term_label}".upper(),
            content_width,
            school.accent_color,
            height=5 * mm,
            font_size=8,
        )
    )
    story.append(Spacer(1, 2 * mm))

    # ---- Student info block ------------------------------------------------
    photo_flow = (
        Image(student.photo_path, width=24 * mm, height=28 * mm)
        if student.photo_path and os.path.exists(student.photo_path)
        else Table(
            [[""]],
            colWidths=[24 * mm],
            rowHeights=[24 * mm],
            style=TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, BORDER_GREY),
                    ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
                ]
            ),
        )
    )

    info_style_bold = ParagraphStyle("InfoBold", fontName="Helvetica-Bold", fontSize=10)
    info_style = ParagraphStyle(
        "Info", fontName="Helvetica", fontSize=8, textColor=colors.grey, leading=10
    )
    info_block = [
        Paragraph(student.name, info_style_bold),
        Paragraph(f"ADMNO: {student.admission_no}", info_style),
        Paragraph(f"GRADE: {student.grade}", info_style),
    ]
    student_tbl = Table([[photo_flow, info_block]], colWidths=[28 * mm, content_width - 28 * mm])
    student_tbl.setStyle(
        TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (1, 0), (1, 0), 8)])
    )
    story.append(student_tbl)
    story.append(Spacer(1, 1.5 * mm))

    # ---- Performance chart --------------------------------------------------
    chart_points = chart_subjects or [
        ChartSubjectPoint(s.subject[:3].upper(), s.marks) for s in subjects
    ]
    chart_width_in = content_width / 72.0
    chart_height_in = 0.88  # drawn height = 0.88 * 72pt ~= short band
    chart_buf = _build_performance_chart(
        chart_points, class_avg=class_avg, width_in=chart_width_in, height_in=chart_height_in
    )
    story.append(
        Paragraph(
            "Subject Performance - Student vs Class",
            ParagraphStyle("ChartTitle", fontName="Helvetica-Bold", fontSize=7.5),
        )
    )
    story.append(Image(chart_buf, width=content_width, height=chart_height_in * 72))
    story.append(Spacer(1, 1.5 * mm))

    # ---- Summary stat boxes --------------------------------------------------
    box_w = (content_width - 3 * 4) / 4
    stats_row = [
        _stat_box("Performance Level", student.performance_level, student.performance_rank, box_w),
        _stat_box("Total Marks", student.total_marks, student.total_marks_rank, box_w),
        _stat_box("Total Points", student.total_points, student.total_points_rank, box_w),
        _stat_box("Performance Level", student.performance_level, None, box_w),
    ]
    stats_tbl = Table([stats_row], colWidths=[box_w] * 4, spaceAfter=0)
    stats_tbl.setStyle(
        TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2)])
    )
    story.append(stats_tbl)
    story.append(Spacer(1, 2 * mm))

    # ---- Subjects table --------------------------------------------------
    cell_style = ParagraphStyle("Cell", fontName="Helvetica", fontSize=7, leading=8.2)
    header_style = ParagraphStyle(
        "CellHeader",
        fontName="Helvetica-Bold",
        fontSize=7,
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    col_widths = [content_width * w for w in (0.19, 0.08, 0.09, 0.07, 0.06, 0.05, 0.28, 0.18)]

    table_data = [
        ["", "", "END OF TERM TWO COMBINED", "", "", "", "", ""],
        ["SUBJECT", "CAT 1", "END TERM", "Marks", "DEV.", "GR.", "COMMENT", "TEACHER"],
    ]
    span_commands = [
        ("SPAN", (2, 0), (5, 0)),
        ("BACKGROUND", (0, 1), (-1, 1), school.accent_color_dark),
        ("BACKGROUND", (2, 0), (5, 0), LIGHT_GREY),
    ]
    for i in range(8):
        table_data[1][i] = Paragraph(table_data[1][i], header_style)

    core_subjects = [s for s in subjects if not s.is_support_subject]
    support_subjects = [s for s in subjects if s.is_support_subject]

    for s in core_subjects:
        table_data.append(
            [
                Paragraph(s.subject, cell_style),
                f"{s.cat1:.0f} %",
                f"{s.end_term:.0f} %",
                f"{s.marks:.0f} %",
                s.deviation,
                s.grade,
                Paragraph(s.comment, cell_style),
                Paragraph(s.teacher, cell_style),
            ]
        )

    if support_subjects:
        support_header_row_idx = len(table_data)
        table_data.append(["SUPPORT SUBJECTS", "", "", "", "", "", "", ""])
        span_commands.append(("SPAN", (0, support_header_row_idx), (-1, support_header_row_idx)))
        span_commands.append(
            ("BACKGROUND", (0, support_header_row_idx), (-1, support_header_row_idx), LIGHT_GREY)
        )
        span_commands.append(
            ("ALIGN", (0, support_header_row_idx), (-1, support_header_row_idx), "CENTER")
        )
        for s in support_subjects:
            table_data.append(
                [
                    Paragraph(s.subject, cell_style),
                    f"{s.cat1:.0f} %",
                    f"{s.end_term:.0f} %",
                    f"{s.marks:.0f} %",
                    s.deviation,
                    s.grade,
                    Paragraph(s.comment, cell_style),
                    Paragraph(s.teacher, cell_style),
                ]
            )

    subjects_tbl = Table(table_data, colWidths=col_widths, repeatRows=2)
    base_style = [
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_GREY),
        ("INNERGRID", (0, 1), (-1, -1), 0.5, BORDER_GREY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 2), (5, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ] + span_commands
    subjects_tbl.setStyle(TableStyle(base_style))
    story.append(subjects_tbl)
    story.append(Spacer(1, 2 * mm))

    # ---- Pathways mean scores --------------------------------------------
    story.append(
        Paragraph(
            "PATHWAYS MEAN SCORES",
            ParagraphStyle("PathwaysTitle", fontName="Helvetica-Bold", fontSize=7.5),
        )
    )
    story.append(Spacer(1, 1 * mm))
    pw_header = [p.label for p in pathways]
    pw_values = [f"{p.mean_score:.1f}" for p in pathways]
    pw_tbl = Table(
        [pw_header, pw_values], colWidths=[content_width / len(pathways)] * len(pathways)
    )
    pw_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, BORDER_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(pw_tbl)
    story.append(Spacer(1, 2 * mm))

    # ---- Comments banner + boxes -------------------------------------------
    story.append(
        _teal_banner("COMMENTS", content_width, school.accent_color, height=4 * mm, font_size=8)
    )
    story.append(Spacer(1, 1.5 * mm))

    remark_title_style = ParagraphStyle("RemarkTitle", fontName="Helvetica-Bold", fontSize=7.5)
    remark_body_style = ParagraphStyle("RemarkBody", fontName="Helvetica", fontSize=7.5, leading=10)

    left_box = [
        Paragraph(f"Class Teacher Remarks: {student.class_teacher_name}", remark_title_style),
        Spacer(1, 2),
        Paragraph(student.class_teacher_remark, remark_body_style),
        Spacer(1, 3),
        Paragraph("Signature: _______________________", remark_body_style),
    ]
    right_box = [
        Paragraph(f"Principal Remarks: {student.principal_name}", remark_title_style),
        Spacer(1, 2),
        Paragraph(student.principal_remark, remark_body_style),
        Spacer(1, 3),
        Paragraph("Signature: _______________________", remark_body_style),
    ]
    comments_tbl = Table(
        [[left_box, right_box]], colWidths=[content_width / 2 - 3, content_width / 2 - 3]
    )
    comments_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (0, 0), 0.75, BORDER_GREY),
                ("BOX", (1, 0), (1, 0), 0.75, BORDER_GREY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(comments_tbl)
    story.append(Spacer(1, 2 * mm))

    # ---- Term dates ---------------------------------------------------------
    story.append(
        Paragraph(
            "TERM DATES",
            ParagraphStyle("TermDatesTitle", fontName="Helvetica-Bold", fontSize=6.5, spaceAfter=1),
        )
    )
    dates_tbl = Table(
        [["TERM ENDS", "NEXT TERM BEGINS"], [student.term_ends, student.next_term_begins]],
        colWidths=[content_width / 2, content_width / 2],
    )
    dates_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, BORDER_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(dates_tbl)
    story.append(Spacer(1, 1 * mm))

    # ---- Footer: stamp + QR code -------------------------------------------
    if school.stamp_path and os.path.exists(school.stamp_path):
        stamp_flow = Image(school.stamp_path, width=24 * mm, height=16 * mm)
    else:
        stamp_flow = Spacer(24 * mm, 16 * mm)

    qr_target = qr_data or f"https://example.com/profile/{student.admission_no}"
    qr_buf = _build_qr_code(qr_target)
    qr_caption_style = ParagraphStyle(
        "QRCaption", fontName="Helvetica", fontSize=6.5, textColor=colors.grey, leading=8.5
    )
    qr_cell = [Image(qr_buf, width=11 * mm, height=11 * mm)]
    qr_text_cell = [
        Paragraph(
            f"Scan to access interactive student profile on {school.analytics_platform}.",
            qr_caption_style,
        ),
        Paragraph(
            f"Your username is {student.admission_no}@{school.email.split('@')[-1]}",
            qr_caption_style,
        ),
    ]
    footer_tbl = Table(
        [[qr_cell, qr_text_cell, stamp_flow]],
        colWidths=[13 * mm, content_width - 13 * mm - 26 * mm, 26 * mm],
    )
    footer_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(footer_tbl)

    doc.build(
        story,
        onFirstPage=_draw_accent_bar_factory(school.accent_color),
        onLaterPages=_draw_accent_bar_factory(school.accent_color),
    )

    return output_path


def _draw_accent_bar_factory(accent_color):
    """Returns an onPage callback that draws the left vertical color strip."""

    def _draw(canvas_obj: pdfcanvas.Canvas, doc):
        canvas_obj.saveState()
        canvas_obj.setFillColor(accent_color)
        canvas_obj.rect(0, 0, ACCENT_BAR_W, PAGE_H, stroke=0, fill=1)
        canvas_obj.restoreState()

    return _draw


# --------------------------------------------------------------------------
# Demo / self-test
# --------------------------------------------------------------------------

if __name__ == "__main__":
    # ---- Demo: two DIFFERENT schools, same rendering code -----------------
    # This proves nothing about the school is hardcoded: swap the
    # SchoolConfig and the name, contact details, and brand color all change.

    school_a = build_school_config(
        {
            "name": "Gichuru Memorial Secondary School",
            "po_box": "459-00902 Kikuyu",
            "phone": "0790268040",
            "email": "gichurumemo@gmail.com",
            "analytics_platform": "Zeraki Analytics",
        }
    )

    school_b = build_school_config(
        {
            "name": "Riverside Hills Academy",
            "po_box": "1024-00100 Nairobi",
            "phone": "0722445566",
            "email": "info@riversidehills.ac.ke",
            "analytics_platform": "EduTrack Insights",
            "accent_color_hex": "#8E2DE2",
            "accent_color_dark_hex": "#5B1E99",
        }
    )

    student = StudentData(
        name="Esther Wambui Mugure",
        admission_no="89/26",
        grade="Grade 10 Social",
        term_label="GRADE 10 - END OF TERM TWO COMBINED - (2026 TERM 2)",
        performance_level="AE1",
        performance_rank="0",
        total_marks="285/700",
        total_marks_rank="0",
        total_points="30/56",
        total_points_rank="0",
        class_teacher_name="Elizabeth M. Kamau",
        class_teacher_remark="Esther, you are putting in effort, but there's still a gap in meeting "
        "expectations. Let's work together to address areas for improvement, "
        "and I'm confident you can succeed.",
        principal_name="Paul M. Nderitu",
        principal_remark="Esther, your performance is below expectations. It's important to increase "
        "your effort. With additional support and guidance, you can make the "
        "necessary progress.",
        term_ends="29/7/2026",
        next_term_begins="25/8/2026",
    )

    subjects = [
        SubjectRow("English", 53, 50, 52, "--", "ME1", "Average, aim higher", "Ann Gidali"),
        SubjectRow("Kiswahili", 27, 52, 40, "--", "AE1", "Put more effort", "Jacinta K. Kiio"),
        SubjectRow(
            "Essential Mathematics",
            8,
            10,
            9,
            "--",
            "BE2",
            "Weak but has potential",
            "Monicah W. Kinyua",
        ),
        SubjectRow(
            "Community Service Learning",
            47,
            40,
            44,
            "--",
            "AE1",
            "Put more effort",
            "Elizabeth M. Kamau",
        ),
        SubjectRow("C.R.E.", 31, 54, 43, "--", "AE1", "Put more effort", "Jane K. Munuki"),
        SubjectRow(
            "Business Studies",
            71,
            38,
            55,
            "--",
            "EE2",
            "Can do better, aim higher",
            "Teresa Chebeni",
        ),
        SubjectRow("Agriculture", 24, 59, 42, "--", "AE1", "Put more effort", "Lydiah W. Ngugi"),
        SubjectRow(
            "Information Communication Technology",
            25,
            0,
            13,
            "--",
            "BE2",
            "Weak but has potential",
            "Gideon Njunge Kinoko",
            is_support_subject=True,
        ),
    ]

    pathways = [
        PathwayScore("STEM", 4.0),
        PathwayScore("SOCIAL SCIENCES", 46.0),
        PathwayScore("ARTS & SPORTS SCIENCE", 0.0),
    ]

    out_a = generate_report_card_pdf(
        school_a,
        student,
        subjects,
        pathways,
        output_path=os.path.join(os.path.dirname(__file__), "sample_report_card_school_a.pdf"),
    )
    out_b = generate_report_card_pdf(
        school_b,
        student,
        subjects,
        pathways,
        output_path=os.path.join(os.path.dirname(__file__), "sample_report_card_school_b.pdf"),
    )
    print(f"Generated: {out_a}")
    print(f"Generated: {out_b}")
