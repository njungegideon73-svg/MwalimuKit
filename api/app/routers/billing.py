"""Stripe billing endpoints."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.subscription import Subscription
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
    SubscriptionOut,
)

router = APIRouter()

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")


def _stripe_configured() -> bool:
    return bool(STRIPE_SECRET_KEY)


def _init_stripe() -> None:
    stripe.api_key = STRIPE_SECRET_KEY


# ── GET /billing/subscription ────────────────────────────────────────────────


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut:
    result = await db.execute(
        select(Subscription).where(Subscription.school_id == user.school_id)
    )
    sub = result.scalar_one_or_none()

    if sub is None:
        now = datetime.now(timezone.utc)
        return SubscriptionOut(
            status="trialing",
            current_period_start=now.isoformat(),
            current_period_end=(now + timedelta(days=30)).isoformat(),
            plan="free_trial",
            is_active=True,
        )

    return SubscriptionOut(
        id=sub.id,
        status=sub.status,
        current_period_start=sub.current_period_start.isoformat()
        if sub.current_period_start
        else None,
        current_period_end=sub.current_period_end.isoformat()
        if sub.current_period_end
        else None,
        plan=sub.stripe_price_id or "free_trial",
        is_active=sub.status in ("active", "trialing"),
    )


# ── POST /billing/checkout ───────────────────────────────────────────────────


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    if not _stripe_configured():
        raise HTTPException(status_code=500, detail="Stripe not configured")

    try:
        _init_stripe()
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": body.price_id, "quantity": 1}],
            success_url=f"{FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/billing",
            metadata={
                "school_id": str(user.school_id),
                "user_id": str(user.id),
            },
        )
        return CheckoutResponse(checkout_url=session.url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── POST /billing/portal ─────────────────────────────────────────────────────


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PortalResponse:
    if not _stripe_configured():
        raise HTTPException(status_code=500, detail="Stripe not configured")

    result = await db.execute(
        select(Subscription).where(Subscription.school_id == user.school_id)
    )
    sub = result.scalar_one_or_none()

    if sub is None or not sub.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription to manage")

    try:
        _init_stripe()
        portal = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=f"{FRONTEND_URL}/billing",
        )
        return PortalResponse(portal_url=portal.url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── POST /billing/webhook ────────────────────────────────────────────────────


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not _stripe_configured():
        raise HTTPException(status_code=500, detail="Stripe not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        _init_stripe()
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (stripe.error.SignatureVerificationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid signature") from exc

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        school_id = data["metadata"]["school_id"]
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(Subscription).where(Subscription.school_id == school_id)
        )
        sub = result.scalar_one_or_none()

        sub_data = stripe.Subscription.retrieve(data["subscription"])
        period_end = datetime.fromtimestamp(sub_data["current_period_end"], tz=timezone.utc)
        period_start = datetime.fromtimestamp(sub_data["current_period_start"], tz=timezone.utc)

        if sub is None:
            sub = Subscription(
                school_id=school_id,
                stripe_customer_id=data.get("customer"),
                stripe_subscription_id=data.get("subscription"),
                stripe_price_id=sub_data["items"]["data"][0]["price"]["id"],
                status=sub_data["status"],
                current_period_start=period_start,
                current_period_end=period_end,
            )
            db.add(sub)
        else:
            sub.stripe_customer_id = data.get("customer")
            sub.stripe_subscription_id = data.get("subscription")
            sub.stripe_price_id = sub_data["items"]["data"][0]["price"]["id"]
            sub.status = sub_data["status"]
            sub.current_period_start = period_start
            sub.current_period_end = period_end

        await db.commit()

    elif event_type == "customer.subscription.updated":
        sub_id = data["id"]
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == sub_id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = data["status"]
            sub.current_period_start = datetime.fromtimestamp(
                data["current_period_start"], tz=timezone.utc
            )
            sub.current_period_end = datetime.fromtimestamp(
                data["current_period_end"], tz=timezone.utc
            )
            await db.commit()

    elif event_type == "customer.subscription.deleted":
        sub_id = data["id"]
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == sub_id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = "canceled"
            sub.canceled_at = datetime.now(timezone.utc)
            await db.commit()

    return {"received": True}
