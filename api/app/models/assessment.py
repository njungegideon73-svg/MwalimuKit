"""Assessment template model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class AssessmentSource(str, PyEnum):
    ai = "ai"
    manual = "manual"
    template = "template"


class Assessment(UUIDPK, Timestamped, Base):
    __tablename__ = "assessments"

    owner_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    school_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    learning_area_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("learning_areas.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    strand_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    sub_strand_codes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=True)
    source: Mapped[AssessmentSource] = mapped_column(
        Enum(AssessmentSource, name="assessment_source", native_enum=False),
        nullable=False,
        default=AssessmentSource.manual,
    )
    rubric: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    is_favourite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
