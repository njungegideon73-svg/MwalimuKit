"""Term exam model – represents an exam within a term (opener, midterm, endterm)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPK


class TermExam(UUIDPK, Base):
    __tablename__ = "term_exams"

    school_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    class_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("classes.id"), nullable=False
    )
    learning_area_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("learning_areas.id"), nullable=False
    )
    term: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, or 3
    exam_type: Mapped[str] = mapped_column(Text, nullable=False)  # opener, midterm, endterm
    academic_year: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. "2025"
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
