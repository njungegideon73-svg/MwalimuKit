"""Tests for the queryable activity log endpoint and password policy."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_activity_log_requires_admin(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/admin/activity-log", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_activity_log_paginated(client: AsyncClient, admin_auth_headers: dict):
    # Generate some activity by logging in.
    await client.post(
        "/api/v1/auth/login",
        json={"email": "schooladmin@test.com", "password": "testpassword123"},
    )

    resp = await client.get("/api/v1/admin/activity-log", headers=admin_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for key in ("total", "offset", "limit", "items"):
        assert key in data
    assert data["total"] >= 1
    actions = [item["action"] for item in data["items"]]
    assert "auth.login" in actions


@pytest.mark.asyncio
async def test_activity_log_filter_by_action(client: AsyncClient, admin_auth_headers: dict):
    await client.post(
        "/api/v1/auth/login",
        json={"email": "schooladmin@test.com", "password": "testpassword123"},
    )

    resp = await client.get(
        "/api/v1/admin/activity-log",
        headers=admin_auth_headers,
        params={"action": "auth.login"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert all(item["action"] == "auth.login" for item in data["items"])

    resp_empty = await client.get(
        "/api/v1/admin/activity-log",
        headers=admin_auth_headers,
        params={"action": "nonexistent.action"},
    )
    assert resp_empty.status_code == 200
    assert resp_empty.json()["items"] == []


@pytest.mark.asyncio
async def test_signup_rejects_weak_passwords(client: AsyncClient, test_school):
    weak_passwords = [
        "short1",          # too short
        "alllettersonly",  # no digit
        "1234567890",      # no letter
    ]
    for i, password in enumerate(weak_passwords):
        resp = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Weak Pass",
                "email": f"weak{i}@test.com",
                "password": password,
                "school_code": test_school.code,
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_signup_accepts_strong_password(client: AsyncClient, test_school):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Strong Pass",
            "email": "strong@test.com",
            "password": "goodpass1",
            "school_code": test_school.code,
        },
    )
    assert resp.status_code == 200
