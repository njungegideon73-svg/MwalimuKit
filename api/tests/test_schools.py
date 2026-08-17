"""Tests for the schools router."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_my_school(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/schools/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "TEST01"
    assert data["name"] == "Test School"
    assert data["county"] == "Nairobi"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_my_school_unauthorized(client: AsyncClient):
    resp = await client.get("/api/v1/schools/me")
    assert resp.status_code in (401, 403)
