"""CORS preflight (OPTIONS) tests for state-changing endpoints.

The API uses JWT bearer tokens, so classic CSRF does not apply to
authenticated calls. These tests lock in the preflight contract instead:
allowed origins are explicit (never a wildcard alongside credentials)
and browsers can actually POST/PATCH/DELETE from the web app.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

ALLOWED_ORIGIN = "http://localhost:5173"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/signup",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/scores/batch",
    ],
)
async def test_preflight_allows_configured_origin(client: AsyncClient, path: str):
    resp = await client.options(
        path,
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "POST" in resp.headers["access-control-allow-methods"]
    assert "authorization" in resp.headers["access-control-allow-headers"].lower()
    # Credentials are enabled, so the origin must never be echoed as "*"
    assert resp.headers["access-control-allow-origin"] != "*"


@pytest.mark.asyncio
async def test_preflight_rejects_unknown_origin(client: AsyncClient):
    resp = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 400
    assert "access-control-allow-origin" not in resp.headers


@pytest.mark.asyncio
async def test_actual_post_sends_cors_headers(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "wrongpass1"},
        headers={"Origin": ALLOWED_ORIGIN},
    )
    assert resp.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
