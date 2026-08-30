"""Feature request model."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class FeatureRequest(UUIDPK, Timestamped, Base):
    __tablename__ = "feature_requests"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    vote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped["__import__('uuid').UUID | None"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    school_id: Mapped["__import__('uuid').UUID | None"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=True
    )
