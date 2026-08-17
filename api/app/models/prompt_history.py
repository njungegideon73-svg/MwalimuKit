"""AI prompt history model."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPK


class PromptHistory(UUIDPK, Base):
    __tablename__ = "prompt_history"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    school_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    assessment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assessments.id"), nullable=True
    )
    learning_area_code: Mapped[str] = mapped_column(Text, nullable=False)
    strand_code: Mapped[str] = mapped_column(Text, nullable=False)
    sub_strand_codes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    grade_level: Mapped[str] = mapped_column(Text, nullable=False)
    teacher_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_count: Mapped[int] = mapped_column(nullable=False, default=5)
    response_rubric: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_items: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
