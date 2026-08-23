"""Score model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDPK, Base


class Score(UUIDPK, Base):
    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("run_id", "learner_id", "item_id", name="uq_scores_run_learner_item"),
    )

    run_id: Mapped[__import__('uuid').UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assessment_runs.id"), nullable=False
    )
    learner_id: Mapped[__import__('uuid').UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("learners.id"), nullable=False
    )
    school_id: Mapped[__import__('uuid').UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    item_id: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
