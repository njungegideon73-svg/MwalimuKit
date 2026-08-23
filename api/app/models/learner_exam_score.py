"""Learner exam score model – stores raw marks for a learner in a term exam."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDPK, Base


class LearnerExamScore(UUIDPK, Base):
    __tablename__ = "learner_exam_scores"
    __table_args__ = (
        UniqueConstraint("term_exam_id", "learner_id", name="uq_learner_exam_score"),
    )

    term_exam_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("term_exams.id"), nullable=False
    )
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("learners.id"), nullable=False
    )
    school_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    marks: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 to max_marks
    grade: Mapped[str | None] = mapped_column(Text, nullable=True)  # optional letter grade
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)  # optional teacher comment
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
