"""Auth endpoint tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient, test_school):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "New Teacher",
            "email": "new@test.com",
            "password": "password123",
            "school_code": test_school.code,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "new@test.com"
    assert data["user"]["full_name"] == "New Teacher"


@pytest.mark.asyncio
async def test_signup_invalid_school_code(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Test",
            "email": "test@test.com",
            "password": "password123",
            "school_code": "NOPE99",
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # First sign up
    await client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Login User",
            "email": "login@test.com",
            "password": "password123",
            "school_code": "TEST01",
        },
    )
    # Then login
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@test.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Wrong Pass",
            "email": "wrong@test.com",
            "password": "password123",
            "school_code": "TEST01",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@test.com", "password": "badpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "password123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient):
    signup_resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Refresh User",
            "email": "refresh@test.com",
            "password": "password123",
            "school_code": "TEST01",
        },
    )
    refresh_token = signup_resp.json()["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert resp.status_code == 401
