"""Security tests: account lockout, logout, session invalidation (token_version)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.rate_limit import (
    LOCKOUT_MAX_FAILURES,
    is_locked_out,
    register_login_failure,
)

pytestmark = pytest.mark.asyncio


# ── Account lockout ──────────────────────────────────────────────────────────


class TestAccountLockout:
    async def test_lockout_after_repeated_failures(self, client: AsyncClient):
        for i in range(LOCKOUT_MAX_FAILURES):
            res = await client.post(
                "/api/v1/auth/login",
                json={"email": "victim@example.com", "password": "wrongpass1"},
            )
            if i < LOCKOUT_MAX_FAILURES - 1:
                assert res.status_code == 401
        # Threshold reached → locked out with 429, not a credential error
        assert res.status_code == 429
        assert "locked" in res.json()["detail"].lower()

    async def test_successful_login_resets_failure_counter(self, client: AsyncClient, test_user):
        for _ in range(LOCKOUT_MAX_FAILURES - 1):
            await client.post(
                "/api/v1/auth/login",
                json={"email": test_user.email, "password": "wrongpass1"},
            )
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        assert res.status_code == 200

        # Failures were cleared → next bad attempt starts counting at 1
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "wrongpass1"},
        )
        assert res.status_code == 401

    async def test_is_locked_out_unit(self):
        email, ip = "unit@example.com", "10.0.0.9"
        assert not await is_locked_out(email, ip)
        for _ in range(LOCKOUT_MAX_FAILURES):
            await register_login_failure(email, ip)
        assert await is_locked_out(email, ip)
        # Different IP for same email is unaffected
        assert not await is_locked_out(email, "10.0.0.10")

    async def test_login_blocked_while_locked(self, client: AsyncClient, test_user):
        for _ in range(LOCKOUT_MAX_FAILURES):
            await register_login_failure(test_user.email, "test")
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        assert res.status_code == 429


# ── Logout ───────────────────────────────────────────────────────────────────


class TestLogout:
    async def test_logout_revokes_refresh_token(self, client: AsyncClient, test_user):
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        refresh_token = login.json()["refresh_token"]

        logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert logout.status_code == 200
        assert logout.json() == {"ok": True}

        # Revoked token can no longer be used to obtain a new pair
        refreshed = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert refreshed.status_code == 401

    async def test_logout_with_garbage_token_still_succeeds(self, client: AsyncClient):
        """Logout never leaks token validity information."""
        res = await client.post(
            "/api/v1/auth/logout", json={"refresh_token": "not-a-real-token"}
        )
        assert res.status_code == 200
        assert res.json() == {"ok": True}


# ── Session invalidation via token_version ───────────────────────────────────


class TestTokenVersionInvalidation:
    async def test_change_password_invalidates_old_tokens_and_returns_new_pair(
        self, db_session, client: AsyncClient, test_user
    ):
        from app.core.security import create_access_token
        from app.models.user import User as UserModel

        old_token = create_access_token(str(test_user.id))
        old_headers = {"Authorization": f"Bearer {old_token}"}

        res = await client.post(
            "/api/v1/auth/change-password",
            headers=old_headers,
            json={"current_password": "testpassword123", "new_password": "NewStr0ngPass99"},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["access_token"]
        assert body["refresh_token"]

        # The pre-password-change access token no longer authenticates.
        me = await client.get("/api/v1/auth/sessions", headers=old_headers)
        assert me.status_code in (401, 403)

        # New tokens work.
        new_headers = {"Authorization": f"Bearer {body['access_token']}"}
        me = await client.get("/api/v1/auth/sessions", headers=new_headers)
        assert me.status_code == 200

        user = await db_session.get(UserModel, test_user.id)
        assert user.token_version >= 1

    async def test_change_password_requires_correct_current_password(
        self, client: AsyncClient, auth_headers
    ):
        res = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={"current_password": "totally-wrong", "new_password": "NewStr0ngPass99"},
        )
        assert res.status_code == 400

    async def test_change_password_enforces_complexity(self, client: AsyncClient, auth_headers):
        res = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={"current_password": "testpassword123", "new_password": "short1"},
        )
        assert res.status_code == 422

    async def test_refresh_rejected_after_version_bump(self, db_session, client, test_user):
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        refresh_token = login.json()["refresh_token"]

        # Simulate a password change bumping the version out-of-band.
        from app.models.user import User as UserModel
        from sqlalchemy import update

        await db_session.execute(
            update(UserModel).where(UserModel.id == test_user.id).values(token_version=3)
        )
        await db_session.commit()

        res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert res.status_code == 401
