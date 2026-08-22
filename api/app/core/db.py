"""SQLAlchemy async engine + session factory with RLS GUC injection."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.tenant import get_auth_email, get_tenant


def _to_async_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(_to_async_url(settings.database_url), future=True, pool_pre_ping=True, connect_args={"statement_cache_size": 0})
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession, begin=False)


async def _apply_rls_gucs(session: AsyncSession) -> None:
    """Set PostgreSQL GUCs from the current tenant context (session-level).

    Uses ``set_config(..., is_local=false)`` so the setting persists across
    commits within the same connection (the auth flow commits before
    refreshing user data).  GUCs are RESET in the finally block of
    :func:`get_db` to prevent leakage across pooled connections.
    """
    tenant = get_tenant()
    if tenant is not None:
        await session.execute(
            text("SELECT set_config('app.current_school_id', :val, false)")
            .bindparams(val=str(tenant.school_id)),
        )
        await session.execute(
            text("SELECT set_config('app.current_role', :val, false)")
            .bindparams(val=tenant.role),
        )
    else:
        await session.execute(text("SELECT set_config('app.current_school_id', '', false)"))
        await session.execute(text("SELECT set_config('app.current_role', 'app', false)"))

    email = get_auth_email()
    if email:
        await session.execute(
            text("SELECT set_config('app.current_email', :val, false)")
            .bindparams(val=email),
        )
    else:
        await session.execute(text("SELECT set_config('app.current_email', '', false)"))


async def _reset_rls_gucs(session: AsyncSession) -> None:
    await session.execute(text("RESET app.current_school_id"))
    await session.execute(text("RESET app.current_role"))
    await session.execute(text("RESET app.current_email"))


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        await _apply_rls_gucs(session)
        try:
            yield session
        finally:
            await _reset_rls_gucs(session)
