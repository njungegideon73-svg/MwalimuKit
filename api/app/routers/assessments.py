"""Assessment generation + CRUD + export."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_provider
from app.core.db import get_db
from app.core.deps import CurrentUser
from app.core.rate_limit import rate_limit_generate
from app.models.assessment import Assessment, AssessmentSource
from app.models.curriculum import LearningArea
from app.models.prompt_history import PromptHistory
from app.schemas.assessment import (
    AssessmentIn, AssessmentOut, AssessmentUpdate,
    GenerateAssessmentRequest, GenerateAssessmentResponse,
)
from app.utils.activity_logger import log_activity
try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


router = APIRouter()


@router.post("/generate", response_model=GenerateAssessmentResponse)
async def generate(
    request: Request,
    req: GenerateAssessmentRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_generate),
) -> GenerateAssessmentResponse:
    provider = get_provider()
    result = await provider.generate_assessment(
        learning_area=req.learning_area_code,
        strand=req.strand_code,
        sub_strand=", ".join(req.sub_strand_codes),
        grade_level=req.grade_level,
        teacher_prompt=req.teacher_prompt,
        item_count=req.item_count,
        include_diagrams=req.include_diagrams,
    )

    history = PromptHistory(
        user_id=user.id,
        school_id=user.school_id,
        learning_area_code=req.learning_area_code,
        strand_code=req.strand_code,
        sub_strand_codes=req.sub_strand_codes,
        grade_level=req.grade_level,
        teacher_prompt=req.teacher_prompt,
        item_count=req.item_count,
        response_rubric=result.rubric.model_dump() if hasattr(result.rubric, "model_dump") else result.rubric,
        response_items=[i.model_dump() for i in result.items] if hasattr(result.items[0], "model_dump") else result.items,
        provider=result.provider,
        model=result.model,
    )
    db.add(history)
    await db.commit()

    return GenerateAssessmentResponse(
        rubric=result.rubric,
        items=result.items,
        provider=result.provider,
        model=result.model,
    )


@router.get("", response_model=list[AssessmentOut])
async def list_assessments(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[AssessmentOut]:
    rows = (
        await db.execute(
            select(Assessment)
            .where(Assessment.school_id == user.school_id, Assessment.deleted_at.is_(None))
            .order_by(Assessment.updated_at.desc())
        )
    ).scalars().all()
    return [_to_out(a) for a in rows]


@router.post("", response_model=AssessmentOut)
async def create_assessment(
    payload: AssessmentIn, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> AssessmentOut:
    la = (
        await db.execute(select(LearningArea).where(LearningArea.code == payload.learning_area_code))
    ).scalar_one_or_none()
    if la is None:
        raise HTTPException(status_code=400, detail="Unknown learning_area_code")

    source = AssessmentSource(payload.source) if payload.source in {s.value for s in AssessmentSource} else AssessmentSource.manual
    a = Assessment(
        id=uuid4(),
        owner_id=user.id,
        school_id=user.school_id,
        learning_area_id=la.id,
        name=payload.name,
        description=payload.description,
        strand_code=payload.strand_code,
        sub_strand_codes=payload.sub_strand_codes,
        source=source,
        rubric=payload.rubric.model_dump(),
        items=[i.model_dump() for i in payload.items],
        tags=payload.tags,
        is_favourite=payload.is_favourite,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="assessment.created",
        details={"name": a.name, "learning_area_code": payload.learning_area_code},
    )
    return _to_out(a)


@router.get("/{assessment_id}", response_model=AssessmentOut)
async def get_assessment(
    assessment_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> AssessmentOut:
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return _to_out(a)


@router.post("/{assessment_id}/duplicate", response_model=AssessmentOut)
async def duplicate_assessment(
    assessment_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> AssessmentOut:
    original = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if original is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    dupe = Assessment(
        id=uuid4(),
        owner_id=user.id,
        school_id=user.school_id,
        learning_area_id=original.learning_area_id,
        name=f"{original.name} (copy)",
        description=original.description,
        strand_code=original.strand_code,
        sub_strand_codes=list(original.sub_strand_codes) if original.sub_strand_codes else [],
        source=original.source,
        rubric=dict(original.rubric),
        items=list(original.items),
        tags=list(original.tags),
        is_favourite=False,
    )
    db.add(dupe)
    await db.commit()
    await db.refresh(dupe)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="assessment.duplicated",
        details={"name": dupe.name, "original_id": str(original.id)},
    )
    return _to_out(dupe)


@router.patch("/{assessment_id}", response_model=AssessmentOut)
async def update_assessment(
    assessment_id: UUID,
    payload: AssessmentUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AssessmentOut:
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "rubric" in update_data and update_data["rubric"] is not None:
        rubric_val = update_data["rubric"]
        if hasattr(rubric_val, "model_dump"):
            update_data["rubric"] = rubric_val.model_dump()
    if "items" in update_data and update_data["items"] is not None:
        update_data["items"] = [
            i.model_dump() if hasattr(i, "model_dump") else i
            for i in update_data["items"]
        ]

    for field, value in update_data.items():
        setattr(a, field, value)

    await db.commit()
    await db.refresh(a)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="assessment.updated",
        details={"name": a.name},
    )
    return await _to_out_async(a, db)


@router.post("/{assessment_id}/favourite", response_model=AssessmentOut)
async def toggle_favourite(
    assessment_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AssessmentOut:
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    a.is_favourite = not a.is_favourite
    await db.commit()
    await db.refresh(a)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="assessment.favourited",
        details={"name": a.name, "is_favourite": a.is_favourite},
    )
    return await _to_out_async(a, db)


@router.delete("/{assessment_id}")
async def soft_delete(
    assessment_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id, Assessment.school_id == user.school_id
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    a.deleted_at = datetime.now(tz=timezone.utc)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="assessment.deleted",
        details={"name": a.name},
    )
    await db.commit()
    return {"deleted": True}


# --- alias for learning_area_code lookup ---
_la_cache: dict[str, str] = {}


def _resolve_la_code(db: AsyncSession, learning_area_id: UUID) -> str:
    """Synchronous placeholder — actual resolution happens in _to_out_async."""
    return ""


async def _to_out_async(a: Assessment, db: AsyncSession) -> AssessmentOut:
    la = (
        await db.execute(select(LearningArea).where(LearningArea.id == a.learning_area_id))
    ).scalar_one_or_none()
    return AssessmentOut(
        id=a.id,
        owner_id=a.owner_id,
        school_id=a.school_id,
        name=a.name,
        description=a.description,
        learning_area_code=la.code if la else "",
        strand_code=a.strand_code or "",
        sub_strand_codes=list(a.sub_strand_codes) if a.sub_strand_codes else [],
        source=a.source.value if hasattr(a.source, "value") else str(a.source),
        rubric=a.rubric,
        items=a.items,
        tags=a.tags,
        is_favourite=a.is_favourite,
        created_at=a.created_at.isoformat(),
        updated_at=a.updated_at.isoformat(),
        deleted_at=a.deleted_at.isoformat() if a.deleted_at else None,
    )


def _to_out(a: Assessment) -> AssessmentOut:
    """Fallback for contexts where we don't need the learning area code."""
    return AssessmentOut(
        id=a.id,
        owner_id=a.owner_id,
        school_id=a.school_id,
        name=a.name,
        description=a.description,
        learning_area_code="",
        strand_code=a.strand_code or "",
        sub_strand_codes=list(a.sub_strand_codes) if a.sub_strand_codes else [],
        source=a.source.value if hasattr(a.source, "value") else str(a.source),
        rubric=a.rubric,
        items=a.items,
        tags=a.tags,
        is_favourite=a.is_favourite,
        created_at=a.created_at.isoformat(),
        updated_at=a.updated_at.isoformat(),
        deleted_at=a.deleted_at.isoformat() if a.deleted_at else None,
    )


# ---------------------------------------------------------------------------
# Assessment export endpoints
# ---------------------------------------------------------------------------

@router.get("/{assessment_id}/export/pdf")
async def export_assessment_pdf(
    assessment_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    la = (
        await db.execute(select(LearningArea).where(LearningArea.id == a.learning_area_id))
    ).scalar_one_or_none()
    la_name = la.name if la else "Unknown"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements: list = []

    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18, spaceAfter=6)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=11, spaceAfter=4)
    body_style = styles["Normal"]
    small_style = ParagraphStyle("Small", parent=body_style, fontSize=9, spaceAfter=2)

    elements.append(Paragraph(f"Assessment: {a.name}", title_style))
    elements.append(Paragraph(f"Learning Area: {la_name}", subtitle_style))
    elements.append(Paragraph(f"Strand: {a.strand_code or '-'}", subtitle_style))
    elements.append(Paragraph(f"Source: {a.source.value if hasattr(a.source, 'value') else a.source}", subtitle_style))
    elements.append(Spacer(1, 0.5 * cm))

    for idx, item in enumerate(a.items or [], start=1):
        elements.append(Paragraph(f"<b>Question {idx}</b>", body_style))
        elements.append(Paragraph(item.get("stem", ""), body_style))
        if item.get("diagram_description"):
            elements.append(Paragraph(
                f"<b>Diagram / Visual:</b> {item['diagram_description']}",
                ParagraphStyle("Diagram", parent=body_style, fontSize=10, textColor=colors.HexColor("#555555"), spaceAfter=4)
            ))
        elements.append(Paragraph(f"<b>Answer guide:</b> {item.get('answer_guide', '') or 'N/A'}", small_style))
        elements.append(Spacer(1, 0.3 * cm))

    if a.rubric:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph("<b>Rubric</b>", ParagraphStyle("RubricTitle", parent=body_style, fontSize=14, spaceAfter=6)))
        for level in a.rubric.get("levels", []):
            elements.append(Paragraph(
                f"Level {level.get('level')}: <b>{level.get('label', '')}</b> — {level.get('descriptor', '')}",
                small_style
            ))

    doc.build(elements)
    buffer.seek(0)
    filename = f"assessment-{a.name.replace(' ', '-').lower()}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=\"{filename}\""
    })


@router.get("/{assessment_id}/export/docx")
async def export_assessment_docx(
    assessment_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    if not HAS_DOCX:
        raise HTTPException(status_code=501, detail="DOCX export is not available on this server")

    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    la = (
        await db.execute(select(LearningArea).where(LearningArea.id == a.learning_area_id))
    ).scalar_one_or_none()
    la_name = la.name if la else "Unknown"

    document = Document()
    document.add_heading(f"Assessment: {a.name}", level=1)
    document.add_paragraph(f"Learning Area: {la_name}")
    document.add_paragraph(f"Strand: {a.strand_code or '-'}")
    document.add_paragraph(f"Source: {a.source.value if hasattr(a.source, 'value') else a.source}")

    for idx, item in enumerate(a.items or [], start=1):
        p = document.add_paragraph()
        p.add_run(f"Question {idx}: ").bold = True
        p.add_run(item.get("stem", ""))
        if item.get("diagram_description"):
            d = document.add_paragraph()
            d.add_run("Diagram / Visual: ").bold = True
            d.add_run(item["diagram_description"])
        document.add_paragraph(f"Answer guide: {item.get('answer_guide', '') or 'N/A'}")

    if a.rubric:
        document.add_heading("Rubric", level=2)
        for level in a.rubric.get("levels", []):
            p = document.add_paragraph(style='List Bullet')
            p.add_run(f"Level {level.get('level')}: {level.get('label', '')} — {level.get('descriptor', '')}")

    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    filename = f"assessment-{a.name.replace(' ', '-').lower()}.docx"
    return StreamingResponse(buffer, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={
        "Content-Disposition": f"attachment; filename=\"{filename}\""
    })
