"""Feature vote model."""
from __future__ import annotations

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class FeatureVote(UUIDPK, Timestamped, Base):
    __tablename__ = "feature_votes"
    __table_args__ = (
        UniqueConstraint("feature_id", "user_id", name="uq_feature_vote_feature_user"),
    )

    feature_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("feature_requests.id"), nullable=False
    )
    user_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
