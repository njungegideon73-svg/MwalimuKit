"""Schemes of Work router — content-bank + scheduling engine.

Flow:
  1. Curators maintain a pre-authored content bank (``lesson_content``).
  2. A teacher picks grade/subject/term/lessons-per-week + calendar
     interruptions; the backend walks the fixed content sequence and
     slots it into the week/lesson cells of the term calendar.
  3. ``GET /{scheme_id}/preview`` returns the editable HTML-table shape;
     ``POST /{scheme_id}/export/pdf`` renders the actual PDF.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, SchoolAdminUser
from app.models.schemes_of_work import LessonContent, SchemeLesson, SchemeOfWork
from app.schemas.job import JobOut
from app.schemas.schemes_of_work import (
    LessonContentIn,
    LessonContentOut,
    SchemeOfWorkCreate,
    SchemeOfWorkDetail,
    SchemeOfWorkOut,
    SchemePreviewResponse,
)
from app.services.schemes_of_work import (
    Interruption,
    load_content_bank,
    preview_payload,
    resolve_strand_codes,
    schedule_lessons,
)
from app.utils.activity_logger import log_activity

router = APIRouter()


def _interruptions_from_scheme(scheme: SchemeOfWork) -> list[Interruption]:
    interruptions: list[Interruption] = []
    for row in scheme.calendar_interruptions or []:
        if isinstance(row, dict):
            interruptions.append(
                Interruption(
                    week_number=int(row.get("week_number", 0)),
                    type=str(row.get("interruption_type", "other")),
                    label=str(row.get("label", "")),
                )
            )
    return interruptions


async def _build_scheme_from_request(
    db: AsyncSession, user: CurrentUser, req: SchemeOfWorkCreate
) -> SchemeOfWork:
    scheme = SchemeOfWork(
        user_id=user.id,
        school_id=user.school_id,
        name=req.name,
        sub_strand_code=req.sub_strand_code,
        grade=req.grade,
        learning_area_code=req.learning_area_code,
        academic_year=req.academic_year,
        term_number=req.term_number,
        lessons_per_week=req.lessons_per_week,
        calendar_interruptions=[row.model_dump() for row in req.calendar_interruptions],
        total_weeks=req.total_weeks,
    )
    db.add(scheme)
    await db.commit()
    await db.refresh(scheme)
    return scheme


async def _generate_lessons(
    db: AsyncSession,
    scheme: SchemeOfWork,
) -> None:
    """Run the scheduling engine and persist the resulting lesson cells."""
    await db.execute(delete(SchemeLesson).where(SchemeLesson.scheme_id == scheme.id))

    strand_code, _ = await resolve_strand_codes(db, scheme.sub_strand_code)
    blocks = await load_content_bank(db, scheme.sub_strand_code, scheme.term_number)

    if not blocks:
        raise HTTPException(
            status_code=409,
            detail=(
                "No content-bank entries for the selected sub-strand/term. "
                "Add Lesson Content entries before generating a scheme."
            ),
        )

    interruptions = _interruptions_from_scheme(scheme)
    lessons = schedule_lessons(
        content_blocks=blocks,
        total_weeks=scheme.total_weeks,
        lessons_per_week=scheme.lessons_per_week,
        interruptions=interruptions,
    )

    for lesson in lessons:
        if lesson.is_break:
            db.add(
                SchemeLesson(
                    scheme_id=scheme.id,
                    week_number=lesson.week_number,
                    lesson_number=lesson.lesson_number,
                    is_break=True,
                    break_label=lesson.break_label,
                )
            )
            continue

        content = lesson.content
        db.add(
            SchemeLesson(
                scheme_id=scheme.id,
                week_number=lesson.week_number,
                lesson_number=lesson.lesson_number,
                content_id=content.id if content and content.id else None,
                strand_code=strand_code,
                sub_strand_code=scheme.sub_strand_code,
                topic=content.topic if content else None,
                learning_outcomes=(content.learning_outcomes if content else None),
                learning_experiences=(content.learning_experiences if content else None),
                key_inquiry_questions=(content.key_inquiry_questions if content else None),
                resources=(content.resources if content else None),
                assessment_methods=(content.assessment_methods if content else None),
            )
        )
    await db.commit()


@router.post("", response_model=SchemeOfWorkOut, status_code=201)
async def create_scheme(
    req: SchemeOfWorkCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SchemeOfWorkOut:
    scheme = await _build_scheme_from_request(db, user, req)
    await _generate_lessons(db, scheme)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="scheme_of_work.create",
        details={"scheme_id": str(scheme.id), "name": scheme.name},
    )
    return SchemeOfWorkOut.model_validate(scheme)


@router.get("", response_model=list[SchemeOfWorkOut])
async def list_schemes(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[SchemeOfWorkOut]:
    rows = (
        await db.execute(
            select(SchemeOfWork)
            .where(SchemeOfWork.school_id == user.school_id)
            .order_by(SchemeOfWork.created_at.desc())
        )
    ).scalars().all()
    return [SchemeOfWorkOut.model_validate(s) for s in rows]


@router.get("/{scheme_id}", response_model=SchemeOfWorkDetail)
async def get_scheme(
    scheme_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SchemeOfWorkDetail:
    scheme = (
        await db.execute(
            select(SchemeOfWork).where(
                SchemeOfWork.id == scheme_id,
                SchemeOfWork.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme of work not found")

    lessons = (
        await db.execute(
            select(SchemeLesson)
            .where(SchemeLesson.scheme_id == scheme.id)
            .order_by(SchemeLesson.week_number, SchemeLesson.lesson_number)
        )
    ).scalars().all()
    return SchemeOfWorkDetail(
        scheme=SchemeOfWorkOut.model_validate(scheme),
        lessons=[_lesson_out(l) for l in lessons],
    )


@router.get("/{scheme_id}/preview", response_model=SchemePreviewResponse)
async def preview_scheme(
    scheme_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SchemePreviewResponse:
    """Return the editable table shape rendered by the frontend.  The HTML
    cells are contenteditable — the teacher can click and edit any cell
    before printing or exporting to PDF."""
    scheme = (
        await db.execute(
            select(SchemeOfWork).where(
                SchemeOfWork.id == scheme_id,
                SchemeOfWork.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme of work not found")

    lesson_rows = (
        await db.execute(
            select(SchemeLesson)
            .where(SchemeLesson.scheme_id == scheme.id)
            .order_by(SchemeLesson.week_number, SchemeLesson.lesson_number)
        )
    ).scalars().all()

    interruptions = _interruptions_from_scheme(scheme)
    block_query = await load_content_bank(db, scheme.sub_strand_code, scheme.term_number)
    if not block_query:
        # Rebuild from persisted cells so preview works even if content is gone.
        lessons = schedule_lessons(
            content_blocks=[],
            total_weeks=scheme.total_weeks,
            lessons_per_week=scheme.lessons_per_week,
            interruptions=interruptions,
        )
        strand_code, _ = await resolve_strand_codes(db, scheme.sub_strand_code)
        return SchemePreviewResponse.model_validate(
            preview_payload(scheme, lessons, strand_code)
        )

    strand_code, _ = await resolve_strand_codes(db, scheme.sub_strand_code)
    lessons = schedule_lessons(
        content_blocks=block_query,
        total_weeks=scheme.total_weeks,
        lessons_per_week=scheme.lessons_per_week,
        interruptions=interruptions,
    )

    # Recompute the canonical schedule so the preview mirrors the generator;
    # then overlay any teacher edits already saved on individual cells.
    edit_map: dict[tuple[int, int], SchemeLesson] = {}
    for row in lesson_rows:
        edit_map[(row.week_number, row.lesson_number)] = row

    payload = preview_payload(scheme, lessons, strand_code)
    for item in payload["lessons"]:
        key = (item["week_number"], item["lesson_number"])
        edited = edit_map.get(key)
        if edited is not None and not item["is_break"]:
            if edited.topic is not None:
                item["topic"] = edited.topic
            if edited.learning_outcomes:
                item["learning_outcomes"] = edited.learning_outcomes
            if edited.learning_experiences:
                item["learning_experiences"] = edited.learning_experiences
            if edited.key_inquiry_questions:
                item["key_inquiry_questions"] = edited.key_inquiry_questions
            if edited.resources:
                item["resources"] = edited.resources
            if edited.assessment_methods:
                item["assessment_methods"] = edited.assessment_methods
            if edited.notes is not None:
                item["notes"] = edited.notes

    return SchemePreviewResponse.model_validate(payload)


@router.patch("/{scheme_id}/lessons/{lesson_key}")
async def update_lesson_cell(
    scheme_id: UUID,
    lesson_key: str,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Persist a teacher's edit to a single lesson cell.

    ``lesson_key`` is ``W<week>-L<lesson>`` (e.g. ``W2-L1``).
    """
    try:
        raw_week, raw_lesson = lesson_key.removeprefix("W").split("-L")
        week_number = int(raw_week)
        lesson_number = int(raw_lesson)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid lesson key. Use W<week>-L<lesson>.")

    scheme = (
        await db.execute(
            select(SchemeOfWork).where(
                SchemeOfWork.id == scheme_id,
                SchemeOfWork.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme of work not found")

    row = (
        await db.execute(
            select(SchemeLesson).where(
                SchemeLesson.scheme_id == scheme.id,
                SchemeLesson.week_number == week_number,
                SchemeLesson.lesson_number == lesson_number,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Lesson cell not found")

    body = await request.json()
    body = body or {}
    for field in (
        "topic",
        "learning_outcomes",
        "learning_experiences",
        "key_inquiry_questions",
        "resources",
        "assessment_methods",
        "notes",
    ):
        if field in body and body[field] is not None:
            setattr(row, field, body[field])
    await db.commit()
    return {"updated": True, "key": lesson_key}


@router.delete("/{scheme_id}", status_code=204)
async def delete_scheme(
    scheme_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    scheme = (
        await db.execute(
            select(SchemeOfWork).where(
                SchemeOfWork.id == scheme_id,
                SchemeOfWork.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme of work not found")
    await db.execute(delete(SchemeLesson).where(SchemeLesson.scheme_id == scheme.id))
    await db.delete(scheme)
    await db.commit()


@router.post("/{scheme_id}/export/pdf", response_model=JobOut)
async def export_scheme_pdf(
    scheme_id: UUID,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    """Kick off an async PDF export job for the scheme."""
    from app.models.job import JobType
    from app.routers.jobs import _enqueue_job, _idempotency_key

    scheme = (
        await db.execute(
            select(SchemeOfWork).where(
                SchemeOfWork.id == scheme_id,
                SchemeOfWork.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme of work not found")

    payload = {"scheme_id": str(scheme_id), "school_id": str(user.school_id)}
    idem_key = _idempotency_key(request, payload)
    job = await _enqueue_job(db, user, JobType.scheme_of_work_pdf, payload, idem_key)
    return JobOut.model_validate(job)


# ---------------------------------------------------------------------------
# Content bank (curator/admin) endpoints
# ---------------------------------------------------------------------------


@router.get("/content/{sub_strand_code}", response_model=list[LessonContentOut])
async def list_lesson_content(
    sub_strand_code: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    term_number: int | None = None,
) -> list[LessonContentOut]:
    stmt = select(LessonContent).where(LessonContent.sub_strand_code == sub_strand_code)
    if term_number is not None:
        stmt = stmt.where(LessonContent.term_number == term_number)
    rows = (await db.execute(stmt.order_by(LessonContent.sequence_order))).scalars().all()
    return [LessonContentOut.model_validate(r) for r in rows]


@router.post("/content", response_model=LessonContentOut, status_code=201)
async def create_lesson_content(
    req: LessonContentIn,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> LessonContentOut:
    row = LessonContent(**req.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return LessonContentOut.model_validate(row)


@router.put("/content/{content_id}", response_model=LessonContentOut)
async def update_lesson_content(
    content_id: UUID,
    req: LessonContentIn,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> LessonContentOut:
    row = (
        await db.execute(select(LessonContent).where(LessonContent.id == content_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Lesson content not found")
    for k, v in req.model_dump().items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return LessonContentOut.model_validate(row)


@router.delete("/content/{content_id}", status_code=204)
async def delete_lesson_content(
    content_id: UUID,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    row = (
        await db.execute(select(LessonContent).where(LessonContent.id == content_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Lesson content not found")
    await db.delete(row)
    await db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lesson_out(lesson: SchemeLesson):
    return {
        "id": lesson.id,
        "scheme_id": lesson.scheme_id,
        "week_number": lesson.week_number,
        "lesson_number": lesson.lesson_number,
        "content_id": lesson.content_id,
        "is_break": lesson.is_break,
        "break_label": lesson.break_label,
        "strand_code": lesson.strand_code,
        "sub_strand_code": lesson.sub_strand_code,
        "topic": lesson.topic,
        "learning_outcomes": lesson.learning_outcomes or [],
        "learning_experiences": lesson.learning_experiences or [],
        "key_inquiry_questions": lesson.key_inquiry_questions or [],
        "resources": lesson.resources or [],
        "assessment_methods": lesson.assessment_methods or [],
        "notes": lesson.notes,
    }