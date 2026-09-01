"""Schemes of Work models: content bank + scheduling engine."""
from __future__ import annotations

from enum import Enum as PyEnum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class TermNumber(int, PyEnum):
    term_1 = 1
    term_2 = 2
    term_3 = 3


class CalendarInterruptionType(str, PyEnum):
    mid_term_break = "mid_term_break"
    exam_week = "exam_week"
    public_holiday = "public_holiday"
    school_activity = "school_activity"
    other = "other"


class LessonContent(UUIDPK, Timestamped, Base):
    """Pre-authored curriculum content bank entry.

    Each row stores a complete pedagogical unit aligned to a specific
    sub-strand, written in CBC/CBE style with citations to approved
    coursebook pages.
    """
    __tablename__ = "lesson_content"

    sub_strand_code: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    term_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    learning_outcomes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    learning_experiences: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    key_inquiry_questions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    resources: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    assessment_methods: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    value_signs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    core_competences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class SchemeOfWork(UUIDPK, Timestamped, Base):
    """A generated scheme-of-work schedule for a teacher's class.

    Stores the configuration parameters (grade, subject, term, lessons
    per week, calendar interruptions) and serves as the parent for
    individual lesson slots.
    """
    __tablename__ = "schemes_of_work"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    school_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sub_strand_code: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    grade: Mapped[str] = mapped_column(Text, nullable=False)
    learning_area_code: Mapped[str] = mapped_column(Text, nullable=False)
    term_number: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year: Mapped[str] = mapped_column(Text, nullable=False)
    lessons_per_week: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    calendar_interruptions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    total_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SchemeLesson(UUIDPK, Timestamped, Base):
    """A single lesson slot within a scheme of work.

    Each row is one cell in the term calendar: it links a week/lesson
    position to a content-bank entry (or is marked as a break/exam slot).
    """
    __tablename__ = "scheme_lessons"

    scheme_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schemes_of_work.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lesson_content.id"), nullable=True
    )
    is_break: Mapped[bool] = mapped_column(default=False)
    break_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    strand_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    sub_strand_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_outcomes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    learning_experiences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    key_inquiry_questions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resources: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    assessment_methods: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
