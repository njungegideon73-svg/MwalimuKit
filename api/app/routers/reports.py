"""Report generation endpoints (PDF + CSV)."""
from __future__ import annotations

import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.assessment import Assessment
from app.models.curriculum import LearningArea
from app.models.learner import Learner
from app.models.learner_exam_score import LearnerExamScore
from app.models.run import AssessmentRun
from app.models.school import School
from app.models.school_class import SchoolClass
from app.models.score import Score
from app.models.term_exam import TermExam

router = APIRouter()


async def _load_run(
    db: AsyncSession, user: CurrentUser, run_id: UUID
) -> tuple[AssessmentRun, Assessment, SchoolClass]:
    run = (
        await db.execute(
            select(AssessmentRun).where(
                AssessmentRun.id == run_id,
                AssessmentRun.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    assessment = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == run.assessment_id,
                Assessment.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    school_class = (
        await db.execute(
            select(SchoolClass).where(
                SchoolClass.id == run.class_id,
                SchoolClass.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if school_class is None:
        raise HTTPException(status_code=404, detail="Class not found")

    return run, assessment, school_class


def _rubric_label(assessment: Assessment, level: int | None) -> str:
    if level is None:
        return "N/A"
    rubric = assessment.rubric or {}
    for rl in rubric.get("levels", []):
        if rl.get("level") == level:
            return rl.get("label", str(level))
    return str(level)


def _item_title(assessment: Assessment, item_id: str) -> str:
    for item in assessment.items or []:
        if item.get("id") == item_id:
            return item.get("stem", item_id)
    return item_id


# ---------------------------------------------------------------------------
# 1.  Per-learner report card PDF
# ---------------------------------------------------------------------------

@router.get("/learner/{learner_id}/report-card")
async def learner_report_card(
    learner_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    run_id: UUID = Query(...),
):
    learner = (
        await db.execute(
            select(Learner).where(
                Learner.id == learner_id,
                Learner.school_id == user.school_id,
                Learner.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if learner is None:
        raise HTTPException(status_code=404, detail="Learner not found")

    run, assessment, school_class = await _load_run(db, user, run_id)

    if school_class.id != learner.class_id:
        raise HTTPException(status_code=404, detail="Learner not in this class")

    school = (
        await db.execute(
            select(School).where(School.id == user.school_id)
        )
    ).scalar_one_or_none()

    scores = (
        await db.execute(
            select(Score)
            .where(Score.run_id == run_id, Score.learner_id == learner_id)
            .order_by(Score.item_id)
        )
    ).scalars().all()

    if not scores:
        raise HTTPException(status_code=404, detail="No scores found for this learner in this run")

    # --- Build PDF ---
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    elements: list = []

    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=6)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=11, alignment=1, spaceAfter=4)
    body_style = styles["Normal"]
    small_style = ParagraphStyle("Small", parent=body_style, fontSize=9, spaceAfter=2)

    # Header
    school_name = school.name if school else "School"
    school_code = school.code if school else ""
    elements.append(Paragraph(f"{school_name}", title_style))
    elements.append(Paragraph(f"School Code: {school_code}", subtitle_style))
    elements.append(Spacer(1, 0.4 * cm))

    # Learner info
    gender_display = (learner.gender or "-").upper()
    info_data = [
        [
            Paragraph("<b>Learner Name:</b>", body_style),
            Paragraph(learner.full_name, body_style),
            Paragraph("<b>Admission No:</b>", body_style),
            Paragraph(learner.admission_no or "-", body_style),
        ],
        [
            Paragraph("<b>Gender:</b>", body_style),
            Paragraph(gender_display, body_style),
            Paragraph("<b>Class:</b>", body_style),
            Paragraph(school_class.name, body_style),
        ],
    ]
    info_table = Table(info_data, colWidths=[3.5 * cm, 5.5 * cm, 3.5 * cm, 5.5 * cm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3 * cm))

    # Assessment info
    elements.append(Paragraph(f"<b>Assessment:</b> {assessment.name}", body_style))
    elements.append(Paragraph(f"<b>Term:</b> {run.term or '-'}", body_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Scores table
    header = [
        Paragraph("<b>#</b>", body_style),
        Paragraph("<b>Item</b>", body_style),
        Paragraph("<b>Level</b>", body_style),
        Paragraph("<b>Rubric Label</b>", body_style),
    ]
    table_data = [header]

    max_possible = 0
    total_scored = 0
    for idx, score in enumerate(scores, start=1):
        item_stem = _item_title(assessment, score.item_id)
        level = score.level
        label = _rubric_label(assessment, level)

        # Determine max level for this item
        item_max = 4
        for item in assessment.items or []:
            if item.get("id") == score.item_id:
                item_max = item.get("max_level", 4)
                break
        max_possible += item_max
        total_scored += level if level else 0

        table_data.append([
            Paragraph(str(idx), body_style),
            Paragraph(item_stem[:80], small_style),
            Paragraph(str(level) if level is not None else "-", body_style),
            Paragraph(label, body_style),
        ])

    percentage = round((total_scored / max_possible) * 100, 1) if max_possible > 0 else 0.0

    col_widths = [1.2 * cm, 9.5 * cm, 2 * cm, 5 * cm]
    scores_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    scores_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(scores_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Total percentage
    pct_style = ParagraphStyle("Pct", parent=body_style, fontSize=12, alignment=1, spaceAfter=6)
    elements.append(Paragraph(
        f"<b>Total Score: {total_scored} / {max_possible}  ({percentage}%)</b>",
        pct_style,
    ))
    elements.append(Spacer(1, 1.5 * cm))

    # Signature line
    sig_style = ParagraphStyle("Sig", parent=body_style, fontSize=10)
    elements.append(Paragraph("_" * 40 + "          " + "_" * 20, sig_style))
    elements.append(Paragraph("Teacher Signature                                   Date", sig_style))

    doc.build(elements)
    buffer.seek(0)

    filename = f"report_card_{learner.full_name.replace(' ', '_')}_{run_id}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# 2.  SBA learner report card PDF
# ---------------------------------------------------------------------------

EXAM_TYPE_LABELS = {"opener": "Opener", "midterm": "Midterm", "endterm": "End Term"}


@router.get("/report-card/{learner_id}")
async def sba_report_card_pdf(
    learner_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    academic_year: str = Query(...),
    format: str = Query("pdf"),
    school_closed_date: str | None = Query(None),
    next_term_begins_date: str | None = Query(None),
    class_teacher_remarks: str | None = Query(None),
    principal_remarks: str | None = Query(None),
):
    if format != "pdf":
        raise HTTPException(status_code=400, detail="Only PDF format is supported")

    learner = (
        await db.execute(
            select(Learner).where(
                Learner.id == learner_id,
                Learner.school_id == user.school_id,
                Learner.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if learner is None:
        raise HTTPException(status_code=404, detail="Learner not found")

    school_class = (
        await db.execute(
            select(SchoolClass).where(
                SchoolClass.id == learner.class_id,
                SchoolClass.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if school_class is None:
        raise HTTPException(status_code=404, detail="Class not found")

    school = (
        await db.execute(
            select(School).where(School.id == user.school_id)
        )
    ).scalar_one_or_none()

    exams = (
        await db.execute(
            select(TermExam).where(
                TermExam.class_id == learner.class_id,
                TermExam.academic_year == academic_year,
                TermExam.school_id == user.school_id,
            ).order_by(TermExam.term, TermExam.exam_type)
        )
    ).scalars().all()

    exam_ids = [e.id for e in exams]
    if not exam_ids:
        raise HTTPException(status_code=404, detail="No term exams found for this learner in this academic year")

    scores = (
        await db.execute(
            select(LearnerExamScore).where(
                LearnerExamScore.learner_id == learner_id,
                LearnerExamScore.term_exam_id.in_(exam_ids),
            )
        )
    ).scalars().all()
    score_map = {str(s.term_exam_id): s for s in scores}

    # Build subject reports and compute averages
    subjects: list[dict] = []
    exam_type_scores: dict[str, dict[str, list[float]]] = {}

    for exam in exams:
        la = (
            await db.execute(
                select(LearningArea).where(LearningArea.id == exam.learning_area_id)
            )
        ).scalar_one_or_none()
        subject_name = la.name if la else "Unknown"

        score = score_map.get(str(exam.id))
        marks = score.marks if score else None
        pct = round((marks / exam.max_marks) * 100, 1) if marks is not None else None

        subjects.append({
            "subject_name": subject_name,
            "term": exam.term,
            "exam_type": exam.exam_type,
            "marks": marks,
            "max_marks": exam.max_marks,
            "percentage": pct,
            "grade": score.grade if score else None,
        })

        term_key = str(exam.term)
        if term_key not in exam_type_scores:
            exam_type_scores[term_key] = {}
        if exam.exam_type not in exam_type_scores[term_key]:
            exam_type_scores[term_key][exam.exam_type] = []
        if marks is not None:
            exam_type_scores[term_key][exam.exam_type].append((marks / exam.max_marks) * 100)

    term_averages: dict[str, float] = {}
    all_pcts = []
    for term_key, exam_types in exam_type_scores.items():
        term_pcts = []
        for etype_pcts in exam_types.values():
            term_pcts.extend(etype_pcts)
        if term_pcts:
            avg = round(sum(term_pcts) / len(term_pcts), 1)
            term_averages[term_key] = avg
            all_pcts.extend(term_pcts)

    overall_average = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else 0.0

    # --- Build PDF ---
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    elements: list = []

    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=6)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=11, alignment=1, spaceAfter=4)
    body_style = styles["Normal"]
    center_style = ParagraphStyle("Center", parent=body_style, fontSize=11, alignment=1, spaceAfter=4)
    small_style = ParagraphStyle("Small", parent=body_style, fontSize=9, spaceAfter=2)

    school_name = school.name if school else "School"
    school_code = school.code if school else ""
    elements.append(Paragraph(f"{school_name}", title_style))
    elements.append(Paragraph(f"School Code: {school_code}", subtitle_style))
    elements.append(Spacer(1, 0.4 * cm))

    gender_display = (learner.gender or "-").upper()
    info_data = [
        [
            Paragraph("<b>Learner Name:</b>", body_style),
            Paragraph(learner.full_name, body_style),
            Paragraph("<b>Admission No:</b>", body_style),
            Paragraph(learner.admission_no or "-", body_style),
        ],
        [
            Paragraph("<b>Gender:</b>", body_style),
            Paragraph(gender_display, body_style),
            Paragraph("<b>Class:</b>", body_style),
            Paragraph(school_class.name, body_style),
        ],
        [
            Paragraph("<b>Academic Year:</b>", body_style),
            Paragraph(academic_year, body_style),
            Paragraph("", body_style),
            Paragraph("", body_style),
        ],
    ]
    info_table = Table(info_data, colWidths=[3.5 * cm, 5.5 * cm, 3.5 * cm, 5.5 * cm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Group subjects by term
    terms = sorted({s["term"] for s in subjects})
    for term in terms:
        term_subjects = [s for s in subjects if s["term"] == term]
        elements.append(Paragraph(f"<b>Term {term}</b>", center_style))
        elements.append(Spacer(1, 0.2 * cm))

        header = [
            Paragraph("<b>Subject</b>", body_style),
            Paragraph("<b>Exam Type</b>", body_style),
            Paragraph("<b>Marks</b>", body_style),
            Paragraph("<b>Max</b>", body_style),
            Paragraph("<b>%</b>", body_style),
            Paragraph("<b>Grade</b>", body_style),
        ]
        table_data = [header]

        for s in term_subjects:
            table_data.append([
                Paragraph(s["subject_name"], body_style),
                Paragraph(EXAM_TYPE_LABELS.get(s["exam_type"], s["exam_type"]), body_style),
                Paragraph(str(s["marks"]) if s["marks"] is not None else "-", body_style),
                Paragraph(str(s["max_marks"]), body_style),
                Paragraph(f"{s['percentage']}%" if s["percentage"] is not None else "-", body_style),
                Paragraph(s["grade"] or "-", body_style),
            ])

        col_widths = [6 * cm, 3.5 * cm, 2.2 * cm, 2 * cm, 2 * cm, 2 * cm]
        term_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        term_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(term_table)
        elements.append(Spacer(1, 0.4 * cm))

        term_avg = term_averages.get(str(term))
        if term_avg is not None:
            avg_style = ParagraphStyle("Avg", parent=body_style, fontSize=10, alignment=2, spaceAfter=4)
            elements.append(Paragraph(f"<b>Term {term} Average: {term_avg}%</b>", avg_style))
        elements.append(Spacer(1, 0.3 * cm))

    # Overall average
    pct_style = ParagraphStyle("Pct", parent=body_style, fontSize=12, alignment=1, spaceAfter=6)
    elements.append(Paragraph(
        f"<b>Overall Average: {overall_average}%</b>",
        pct_style,
    ))
    elements.append(Spacer(1, 0.5 * cm))

    # Term dates
    if school_closed_date or next_term_begins_date:
        elements.append(Paragraph("<b>Term Dates</b>", ParagraphStyle("Section", parent=body_style, fontSize=12, spaceAfter=4)))
        if school_closed_date:
            elements.append(Paragraph(f"School Closed On: {school_closed_date}", body_style))
        if next_term_begins_date:
            elements.append(Paragraph(f"Next Term Begins On: {next_term_begins_date}", body_style))
        elements.append(Spacer(1, 0.3 * cm))

    # Grade descriptors
    elements.append(Paragraph("<b>Grade Descriptors</b>", ParagraphStyle("Section", parent=body_style, fontSize=12, spaceAfter=4)))
    grade_descriptors = [
        "A (80-100%): Exceeding expectation",
        "B (65-79%): Meeting expectation",
        "C (50-64%): Approaching expectation",
        "D (30-49%): Below expectation",
        "E (0-29%): Far below expectation",
    ]
    for desc in grade_descriptors:
        elements.append(Paragraph(desc, small_style))
    elements.append(Spacer(1, 0.3 * cm))

    # Remarks
    if class_teacher_remarks or principal_remarks:
        elements.append(Paragraph("<b>Remarks</b>", ParagraphStyle("Section", parent=body_style, fontSize=12, spaceAfter=4)))
        if class_teacher_remarks:
            elements.append(Paragraph(f"<b>Class Teacher:</b> {class_teacher_remarks}", body_style))
        if principal_remarks:
            elements.append(Paragraph(f"<b>Principal:</b> {principal_remarks}", body_style))
        elements.append(Spacer(1, 0.3 * cm))

    # Signatures
    elements.append(Spacer(1, 0.5 * cm))
    sig_style = ParagraphStyle("Sig", parent=body_style, fontSize=10)
    elements.append(Paragraph("_" * 40 + "          " + "_" * 20, sig_style))
    elements.append(Paragraph("Class Teacher Signature                Date", sig_style))
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph("_" * 40 + "          " + "_" * 20, sig_style))
    elements.append(Paragraph("Principal Signature                    Date", sig_style))

    doc.build(elements)
    buffer.seek(0)

    filename = f"sba_report_card_{learner.full_name.replace(' ', '_')}_{academic_year}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# 3.  Class summary CSV
# ---------------------------------------------------------------------------

@router.get("/class/{class_id}/summary-csv")
async def class_summary_csv(
    class_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    run_id: UUID = Query(...),
):
    run, assessment, school_class = await _load_run(db, user, run_id)

    if school_class.id != class_id:
        raise HTTPException(status_code=404, detail="Class does not match run")

    learners = (
        await db.execute(
            select(Learner)
            .where(
                Learner.class_id == class_id,
                Learner.school_id == user.school_id,
                Learner.deleted_at.is_(None),
            )
            .order_by(Learner.full_name)
        )
    ).scalars().all()

    if not learners:
        raise HTTPException(status_code=404, detail="No learners found in this class")

    learner_ids = [l.id for l in learners]

    scores = (
        await db.execute(
            select(Score)
            .where(Score.run_id == run_id, Score.learner_id.in_(learner_ids))
            .order_by(Score.learner_id, Score.item_id)
        )
    ).scalars().all()

    # Organise scores by learner
    scores_by_learner: dict[UUID, dict[str, int | None]] = {}
    for s in scores:
        scores_by_learner.setdefault(s.learner_id, {})[s.item_id] = s.level

    # Determine item order from assessment definition
    item_ids = [item.get("id", "") for item in (assessment.items or [])]
    # Fallback: gather any item_ids present in scores not already listed
    seen = set(item_ids)
    for sid_map in scores_by_learner.values():
        for iid in sid_map:
            if iid not in seen:
                item_ids.append(iid)
                seen.add(iid)

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    header = ["Learner Name", "Admission No"] + [f"Item {i + 1}" for i in range(len(item_ids))] + ["Total %"]
    writer.writerow(header)

    max_possible = sum(
        next(
            (item.get("max_level", 4) for item in (assessment.items or []) if item.get("id") == iid),
            4,
        )
        for iid in item_ids
    )

    for learner in learners:
        row_scores = scores_by_learner.get(learner.id, {})
        total = 0
        item_values: list[str] = []
        for iid in item_ids:
            level = row_scores.get(iid)
            item_values.append(str(level) if level is not None else "")
            if level is not None:
                total += level
        pct = round((total / max_possible) * 100, 1) if max_possible > 0 else 0.0
        writer.writerow([learner.full_name, learner.admission_no or ""] + item_values + [pct])

    output.seek(0)
    filename = f"class_summary_{school_class.name.replace(' ', '_')}_{run_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
