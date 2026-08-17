"""Subscription model for Stripe billing."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class Subscription(UUIDPK, Timestamped, Base):
    __tablename__ = "subscriptions"

    school_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, unique=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    stripe_price_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="trialing")
    # statuses: trialing, active, past_due, canceled, unpaid
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
