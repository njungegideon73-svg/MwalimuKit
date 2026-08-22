"""Tenant / role context propagation for PostgreSQL RLS.

A context-variable based system that lets the database layer set per-connection
GUCs (``app.current_school_id``, ``app.current_role``, ``app.current_email``)
that the RLS policies in migration ``0009`` depend on.

Flow:
1. ``TenantContextMiddleware`` (registered first in the ASGI stack) decodes
   the bearer JWT header (signature verified downstream) and populates the
   context variables.
2. ``api/app/core/db.py`` ``get_db`` reads these context variables and runs
   ``set_config(...)`` (session-level) on the DB session.  The values are
   RESET in the finally block so they never leak across pooled connections.
3. Auth endpoints (login/signup) call :func:`set_auth_email` explicitly
   since they need to look up users by email before a full tenant context
   is established.
"""
from __future__ import annotations

import contextvars
from typing import NamedTuple

from jose import JWTError, jwt
from starlette.requests import Request

from app.core.config import settings

#: Context variable holding (school_id, role) for the current request.
_tenant: contextvars.ContextVar = contextvars.ContextVar("mwalimukit_tenant", default=None)

#: Context variable holding an email address for auth-endpoint GUC.
_auth_email: contextvars.ContextVar = contextvars.ContextVar("mwalimukit_auth_email", default=None)


class TenantContext(NamedTuple):
    school_id: str
    role: str


def get_tenant() -> TenantContext | None:
    return _tenant.get()


def set_tenant(school_id: str | None, role: str | None) -> None:
    _tenant.set(TenantContext(school_id, role) if school_id and role else None)


def clear_tenant() -> None:
    _tenant.set(None)
    _auth_email.set(None)


def set_auth_email(email: str | None) -> None:
    _auth_email.set(email)


def get_auth_email() -> str | None:
    return _auth_email.get()


def _decode_claims(token: str) -> dict:
    """Decode JWT claims WITHOUT verifying the signature.

    The token is verified downstream by ``core.deps.get_current_user``;
    here we only need the ``school_id`` and ``role`` claims to populate
    the RLS GUCs early.
    """
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"verify_signature": False},
        )
    except JWTError:
        return {}


class TenantContextMiddleware:
    """ASGI middleware that reads the bearer token and populates tenant
    context variables consumed by :func:`app.core.db.apply_tenant_gucs`.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope)
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                claims = _decode_claims(token)
                school_id = claims.get("school_id")
                role = claims.get("role")
                if school_id and role:
                    set_tenant(school_id, role)

        await self.app(scope, receive, send)
