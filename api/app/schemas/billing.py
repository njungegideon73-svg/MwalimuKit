"""Billing / subscription schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    price_id: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionOut(BaseModel):
    id: UUID | None = None
    status: str
    current_period_start: str | None = None
    current_period_end: str | None = None
    plan: str = "free_trial"
    is_active: bool = False
