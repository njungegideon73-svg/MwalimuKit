"""Tests for admin dashboard, roadmap, and billing endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
async def test_dashboard_returns_counts(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/admin/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for key in ("total_learners", "total_classes", "total_assessments", "total_runs", "total_scores"):
        assert key in data


@pytest.mark.asyncio
async def test_dashboard_empty_school(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/admin/dashboard", headers=auth_headers)
    data = resp.json()
    assert data["total_learners"] == 0
    assert data["total_classes"] == 0
    assert data["total_assessments"] == 0
    assert data["total_runs"] == 0
    assert data["total_scores"] == 0


@pytest.mark.asyncio
async def test_roadmap_list_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/admin/roadmap", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_roadmap_create_feature(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/admin/roadmap",
        headers=auth_headers,
        json={"title": "Dark mode", "description": "Add dark mode support"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["title"] == "Dark mode"
    assert data["vote_count"] == 0


@pytest.mark.asyncio
async def test_roadmap_vote_toggle(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/api/v1/admin/roadmap",
        headers=auth_headers,
        json={"title": "Feature X", "description": "A cool feature"},
    )
    feature_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/admin/roadmap/{feature_id}/vote",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["vote_count"] == 1
    assert data["user_has_voted"] is True

    resp2 = await client.post(
        f"/api/v1/admin/roadmap/{feature_id}/vote",
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["vote_count"] == 0
    assert data2["user_has_voted"] is False


@pytest.mark.asyncio
async def test_subscription_default_trial(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/billing/subscription", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "trialing"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_subscription_checkout_no_stripe(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/billing/checkout",
        headers=auth_headers,
        json={"price_id": "price_test123"},
    )
    assert resp.status_code == 500
