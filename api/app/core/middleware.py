"""ASGI middleware: security headers, request IDs + access logs, body size
limit, and Prometheus metrics."""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.metrics import inc_counter, normalize_path, observe_duration

logger = structlog.get_logger()


class RequestContextMiddleware:
    """Attaches a per-request ID, emits one structured access log entry,
    and echoes X-Request-ID back to the caller."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                request_id = value.decode("latin-1")[:64]
                break
        request_id = request_id or uuid.uuid4().hex[:16]

        started = time.perf_counter()
        status_holder = {"status": 0}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                headers = message.setdefault("headers", [])
                headers.append((b"x-request-id", request_id.encode("latin-1")))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            client = scope.get("client")
            log = logger.bind(
                request_id=request_id,
                method=scope.get("method"),
                path=scope.get("path"),
                status=status_holder["status"],
                duration_ms=round(duration_ms, 1),
                ip=client[0] if client else "unknown",
            )
            if scope.get("path", "").startswith(("/health", "/ready", "/metrics")):
                log.debug("http.request")
            else:
                log.info("http.request")


class SecurityHeadersMiddleware:
    """Adds hardening headers to every API response."""

    HEADERS = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"cache-control", b"no-store"),
    ]
    HSTS = b"max-age=31536000; includeSubDomains"

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.extend(self.HEADERS)
                if _is_https(scope) or settings.env == "production":
                    headers.append((b"strict-transport-security", self.HSTS))
            await send(message)

        await self.app(scope, receive, send_wrapper)


def _is_https(scope) -> bool:
    if scope.get("scheme") == "https":
        return True
    for name, value in scope.get("headers", []):
        if name == b"x-forwarded-proto" and value.decode("latin-1").strip() == "https":
            return True
    return False


class BodySizeLimitMiddleware:
    """Rejects oversized request bodies early (default 1 MiB)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = 0
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    content_length = int(value)
                except ValueError:
                    content_length = 0
                break

        if content_length > settings.max_body_bytes:
            inc_counter("mwalimukit_oversized_requests_total")
            response = JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


class MetricsMiddleware:
    """Counts requests and records latency histograms per route template."""

    EXEMPT_PATHS = ("/metrics",)

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if any(scope.get("path", "").startswith(p) for p in self.EXEMPT_PATHS):
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        started = time.perf_counter()
        status_holder = {"status": 0}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - started
            request = Request(scope)
            handler = normalize_path(request)
            labels = {"method": method, "handler": handler}
            inc_counter(
                "mwalimukit_http_requests_total", {**labels, "status": str(status_holder["status"])}
            )
            observe_duration(
                "mwalimukit_http_request_duration_seconds", duration, labels
            )
