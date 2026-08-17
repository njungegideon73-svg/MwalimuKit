"""Feature request model."""
from __future__ import annotations

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class FeatureRequest(UUIDPK, Timestamped, Base):
    __tablename__ = "feature_requests"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    vote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
