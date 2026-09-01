"""Schemes of Work scheduling engine.

This module implements the "content-bank + scheduling engine" model:
a pre-authored curriculum content bank is walked in fixed sequence and
slotted into the lesson cells produced by a term calendar.  It is not a
generative-AI system — quality comes from the underlying content bank,
and "customization" only changes the shape of the calendar and which
pre-written content block is selected.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculum import Strand, SubStrand
from app.models.schemes_of_work import LessonContent, SchemeOfWork


@dataclass
class Interruption:
    week_number: int
    type: str
    label: str


@dataclass
class ContentBlock:
    id: UUID | None
    topic: str
    learning_outcomes: list[str] = field(default_factory=list)
    learning_experiences: list[str] = field(default_factory=list)
    key_inquiry_questions: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    assessment_methods: list[str] = field(default_factory=list)


@dataclass
class ScheduledLesson:
    week_number: int
    lesson_number: int
    lesson_sequence: int
    content: ContentBlock | None = None
    is_break: bool = False
    break_label: str | None = None


def _as_str_list(value: list | dict | None) -> list[str]:
    """Normalise a JSONB content field (list or list-of-citations) to strings."""
    if not value:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                # e.g. resource entries like {"title": "...", "cite": "pg. 121"}
                if "cite" in item or "pages" in item or "title" in item:
                    title = str(item.get("title", "")).strip()
                    cite = str(item.get("cite", item.get("pages", ""))).strip()
                    if title and cite:
                        rendered = f"{title} — {cite}"
                    else:
                        rendered = title or cite
                    if rendered:
                        out.append(rendered)
                else:
                    out.extend(_as_str_list(list(item.values())))
        return out
    return []


async def load_content_bank(
    db: AsyncSession,
    sub_strand_code: str,
    term_number: int,
) -> list[ContentBlock]:
    """Load the pre-authored content-bank entries for a sub-strand/term,
    in fixed pedagogical sequence."""
    rows = (
        await db.execute(
            select(LessonContent)
            .where(
                LessonContent.sub_strand_code == sub_strand_code,
                LessonContent.term_number == term_number,
            )
            .order_by(LessonContent.sequence_order)
        )
    ).scalars().all()

    blocks: list[ContentBlock] = []
    for row in rows:
        blocks.append(
            ContentBlock(
                id=row.id,
                topic=row.topic,
                learning_outcomes=_as_str_list(row.learning_outcomes),
                learning_experiences=_as_str_list(row.learning_experiences),
                key_inquiry_questions=_as_str_list(row.key_inquiry_questions),
                resources=_as_str_list(row.resources),
                assessment_methods=_as_str_list(row.assessment_methods),
            )
        )
    return blocks


async def resolve_strand_codes(
    db: AsyncSession, sub_strand_code: str
) -> tuple[str | None, list[str]]:
    """Return (strand_code, [all sub_strand codes in that strand in order])."""
    sub = (
        await db.execute(select(SubStrand).where(SubStrand.code == sub_strand_code))
    ).scalar_one_or_none()
    if sub is None:
        return None, [sub_strand_code]

    strand = (
        await db.execute(select(Strand).where(Strand.id == sub.strand_id))
    ).scalar_one_or_none()
    if strand is None:
        return None, [sub_strand_code]

    siblings = (
        await db.execute(
            select(SubStrand)
            .where(SubStrand.strand_id == sub.strand_id)
            .order_by(SubStrand.sort_order, SubStrand.code)
        )
    ).scalars().all()
    return strand.code, [s.code for s in siblings]


def _build_calendar(
    total_weeks: int,
    lessons_per_week: int,
    interruptions: list[Interruption],
) -> list[tuple[int, int, str | None]]:
    """Build the term calendar as a flat list of (week, lesson, break_label)
    cells, inserting break/exam rows automatically at their week positions."""
    cells: list[tuple[int, int, str | None]] = []
    interruptions_by_week: dict[int, str] = {}
    for interruption in interruptions:
        if 1 <= interruption.week_number <= total_weeks:
            label = interruption.label or interruption.type.replace("_", " ").title()
            interruptions_by_week[interruption.week_number] = label

    for week in range(1, total_weeks + 1):
        break_label = interruptions_by_week.get(week)
        if break_label:
            # A break/exam week occupies the whole week: no regular lessons.
            cells.append((week, 0, break_label))
        else:
            for lesson in range(1, lessons_per_week + 1):
                cells.append((week, lesson, None))
    return cells


def schedule_lessons(
    content_blocks: list[ContentBlock],
    total_weeks: int,
    lessons_per_week: int,
    interruptions: list[Interruption],
) -> list[ScheduledLesson]:
    """Walk the fixed content sequence and slot it into the calendar cells.

    The content bank is consumed in order; when a fixed content unit
    must stretch across more lesson slots than it has unique entries for,
    the last available block is reused *without rewriting its text* — this
    mirrors how CBMS-style schedulers behave and is why adjacent lesson
    slots can carry identical wording.
    """
    calendar = _build_calendar(total_weeks, lessons_per_week, interruptions)

    lessons: list[ScheduledLesson] = []
    content_index = 0
    lesson_sequence = 0

    for week, lesson_number, break_label in calendar:
        if break_label:
            lessons.append(
                ScheduledLesson(
                    week_number=week,
                    lesson_number=lesson_number,
                    lesson_sequence=0,
                    is_break=True,
                    break_label=break_label,
                )
            )
            continue

        lesson_sequence += 1
        if content_blocks:
            block = content_blocks[min(content_index, len(content_blocks) - 1)]
            content_index += 1
        else:
            block = ContentBlock(
                id=None,
                topic="",
                learning_outcomes=[],
                learning_experiences=[],
                key_inquiry_questions=[],
                resources=[],
                assessment_methods=[],
            )
        lessons.append(
            ScheduledLesson(
                week_number=week,
                lesson_number=lesson_number,
                lesson_sequence=lesson_sequence,
                content=block,
            )
        )

    return lessons


def preview_payload(
    params: SchemeOfWork,
    lessons: list[ScheduledLesson],
    strand_code: str | None = None,
) -> dict:
    """Render a schedule into the API shape used for preview + export."""
    scheme_out = {
        "id": str(params.id),
        "name": params.name,
        "sub_strand_code": params.sub_strand_code,
        "grade": params.grade,
        "learning_area_code": params.learning_area_code,
        "term_number": params.term_number,
        "academic_year": params.academic_year,
        "lessons_per_week": params.lessons_per_week,
        "total_weeks": params.total_weeks,
        "created_at": params.created_at.isoformat() if params.created_at else None,
        "updated_at": params.updated_at.isoformat() if params.updated_at else None,
    }
    lesson_payloads = []
    for lesson in lessons:
        item = {
            "week_number": lesson.week_number,
            "lesson_number": lesson.lesson_number,
            "lesson_sequence": lesson.lesson_sequence or None,
            "is_break": lesson.is_break,
            "break_label": lesson.break_label,
            "strand_code": strand_code,
            "sub_strand_code": params.sub_strand_code,
            "topic": lesson.content.topic if lesson.content and not lesson.is_break else None,
            "learning_outcomes": lesson.content.learning_outcomes if lesson.content and not lesson.is_break else [],
            "learning_experiences": lesson.content.learning_experiences if lesson.content and not lesson.is_break else [],
            "key_inquiry_questions": lesson.content.key_inquiry_questions if lesson.content and not lesson.is_break else [],
            "resources": lesson.content.resources if lesson.content and not lesson.is_break else [],
            "assessment_methods": lesson.content.assessment_methods if lesson.content and not lesson.is_break else [],
            "notes": None,
        }
        lesson_payloads.append(item)
    return {"scheme": scheme_out, "lessons": lesson_payloads}