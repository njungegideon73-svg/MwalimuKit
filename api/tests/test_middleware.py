"""Security tests: security headers, metrics endpoint, body size limit,
sanitized error responses."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def bare_client():
    """Client hitting the real app (no DB override) — for middleware tests."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestSecurityHeaders:
    async def test_headers_on_every_response(self, bare_client: AsyncClient):
        res = await bare_client.get("/health")
        assert res.status_code == 200
        assert res.headers["x-content-type-options"] == "nosniff"
        assert res.headers["x-frame-options"] == "DENY"
        assert res.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert res.headers["cache-control"] == "no-store"

    async def test_request_id_echoed(self, bare_client: AsyncClient):
        res = await bare_client.get("/health", headers={"X-Request-ID": "abc-123"})
        assert res.headers["x-request-id"] == "abc-123"

    async def test_request_id_generated_when_missing(self, bare_client: AsyncClient):
        res = await bare_client.get("/health")
        assert len(res.headers["x-request-id"]) >= 8


class TestMetricsEndpoint:
    async def test_metrics_exposes_http_counters(self, bare_client: AsyncClient):
        await bare_client.get("/health")
        await bare_client.get("/health")
        res = await bare_client.get("/metrics")
        assert res.status_code == 200
        assert "text/plain" in res.headers["content-type"]
        assert 'mwalimukit_http_requests_total{handler="/health",method="GET",status="200"} 2' in res.text

    async def test_metrics_uses_route_templates_not_ids(self, client: AsyncClient):
        """Path cardinality guard: concrete ids must be normalised away."""
        await client.get("/api/v1/learners/00000000-0000-0000-0000-000000000000")
        res = await client.get("/metrics")
        text = res.text
        assert "/api/v1/learners/{learner_id}" in text or 'handler="/api/v1/learners/{id}"' in text or "{id}" in text
        # The raw UUID must not appear as a label value anywhere.
        assert 'handler="/api/v1/learners/00000000' not in text


class TestBodySizeLimit:
    async def test_oversized_body_rejected_413(self, bare_client: AsyncClient):
        big = b"x" * (2 * 1024 * 1024)  # 2 MiB > default 1 MiB limit
        res = await bare_client.post(
            "/api/v1/auth/login",
            content=big,
            headers={"Content-Type": "application/json", "Content-Length": str(len(big))},
        )
        assert res.status_code == 413
        assert res.json()["detail"] == "Request body too large"

    async def test_normal_body_allowed(self, bare_client: AsyncClient):
        res = await bare_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "whatever123"},
        )
        # 401 (bad credentials) proves the body passed the size gate.
        assert res.status_code in (401, 429)


class TestSanitizedErrors:
    async def test_validation_errors_do_not_echo_input(self, bare_client: AsyncClient):
        secret_value = "super-secret-password-value"
        res = await bare_client.post(
            "/api/v1/auth/login",
            json={"email": 12345, "password": secret_value},
        )
        assert res.status_code == 422
        body = res.text
        # Pydantic's default handler echoes the offending input; ours must not.
        assert secret_value not in body
        assert '"input"' not in body
        # But still useful: locations + messages retained.
        data = res.json()
        assert isinstance(data["detail"], list) and data["detail"]

    async def test_internal_errors_sanitized(self):
        """A raised exception must become a generic 500 with no stack trace."""
        from app.core.db import get_db

        async def broken_db():
            raise RuntimeError("s3cr3t-internals leaked")
            yield  # pragma: no cover

        app.dependency_overrides[get_db] = broken_db
        try:
            transport = ASGITransport(app=app, raise_app_exceptions=False)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                res = await c.post(
                    "/api/v1/auth/login",
                    json={"email": "a@b.com", "password": "whatever123"},
                )
            assert res.status_code == 500
            assert res.json() == {"detail": "Internal server error"}
            assert "s3cr3t" not in res.text
        finally:
            app.dependency_overrides.clear()
