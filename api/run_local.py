"""Local dev server using SQLite (no PostgreSQL required).

Creates tables, seeds curriculum + demo school + teacher, starts uvicorn.
"""
from __future__ import annotations

import asyncio
import json
import os
from uuid import UUID

# ── Force SQLite + mock AI before anything imports app.* ────────────────
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./mwalimukit_dev.db"
os.environ["AI_PROVIDER"] = "mock"
os.environ["API_SECRET_KEY"] = "dev-local-secret"
os.environ["FEATURE_AI_GENERATION_ENABLED"] = "true"
os.environ["API_CORS_ORIGINS"] = '["http://localhost:5173"]'

# ── Patch PG types for SQLite (same as conftest.py) ────────────────────
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PGUUID, CITEXT


def _uuid_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            if isinstance(value, UUID):
                return value.hex
            return value.replace("-", "") if isinstance(value, str) else str(value)
        return process
    return None


def _uuid_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            if isinstance(value, UUID):
                return value
            v = value.replace("-", "") if isinstance(value, str) else str(value)
            return UUID(v)
        return process
    return None


def _jsonb_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            return json.dumps(value)
        return process
    return None


def _jsonb_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            if isinstance(value, (dict, list)):
                return value
            return json.loads(value)
        return process
    return None


def _array_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            return json.dumps([str(v) for v in value] if value else [])
        return process
    return None


def _array_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            if isinstance(value, list):
                return value
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return process
    return None


def _citext_bind_processor(self, dialect):
    return None


def _citext_result_processor(self, dialect, coltype):
    return None


PGUUID.bind_processor = _uuid_bind_processor  # type: ignore
PGUUID.result_processor = _uuid_result_processor  # type: ignore
JSONB.bind_processor = _jsonb_bind_processor  # type: ignore
JSONB.result_processor = _jsonb_result_processor  # type: ignore
ARRAY.bind_processor = _array_bind_processor  # type: ignore
ARRAY.result_processor = _array_result_processor  # type: ignore
CITEXT.bind_processor = _citext_bind_processor  # type: ignore
CITEXT.result_processor = _citext_result_processor  # type: ignore

# DDL compilers — tell SQLite how to CREATE these column types
from sqlalchemy.ext.compiler import compiles as sa_compiles


@sa_compiles(JSONB, "sqlite")
def _compile_jsonb(type_, compiler, **kw):
    return "JSON"


@sa_compiles(ARRAY, "sqlite")
def _compile_array(type_, compiler, **kw):
    return "TEXT"


@sa_compiles(PGUUID, "sqlite")
def _compile_uuid(type_, compiler, **kw):
    return "VARCHAR(36)"


@sa_compiles(CITEXT, "sqlite")
def _compile_citext(type_, compiler, **kw):
    return "TEXT"


# ── Now safe to import app modules ─────────────────────────────────────


async def _setup():
    """Create tables and seed data."""
    from app.models.base import Base
    from app.core.db import SessionLocal
    import app.models  # noqa: F401 – register all models

    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine("sqlite+aiosqlite:///./mwalimukit_dev.db", future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("  Tables created.")

    # Seed curriculum
    from app.scripts.seed_curriculum import upsert_all
    async with SessionLocal() as db:
        await upsert_all(db)
    print("  Curriculum seeded.")

    # Seed demo school + users + feature flags
    from app.core.security import hash_password
    from app.models.school import School
    from app.models.user import User, UserRole
    from app.models.feature_flag import FeatureFlag
    from uuid import uuid4

    async with SessionLocal() as db:
        school = School(
            id=uuid4(),
            name="Mwalimu Demo Primary",
            code="DEMO001",
            county="Nairobi",
            level="primary",
            settings={},
        )
        db.add(school)
        await db.flush()

        teacher = User(
            id=uuid4(),
            school_id=school.id,
            email="teacher@demo.mwalimukit.go.ke",
            full_name="Demo Teacher",
            role=UserRole.teacher,
            password_hash=hash_password("password123"),
            is_active=True,
        )
        db.add(teacher)

        admin_user = User(
            id=uuid4(),
            school_id=school.id,
            email="admin@demo.mwalimukit.go.ke",
            full_name="Demo Admin",
            role=UserRole.school_admin,
            password_hash=hash_password("password123"),
            is_active=True,
        )
        db.add(admin_user)

        flags = [
            FeatureFlag(key="ai_generation", value=True),
            FeatureFlag(key="paywall", value=False),
            FeatureFlag(key="offline_sync", value=True),
            FeatureFlag(key="leaderboard", value=False),
        ]
        db.add_all(flags)
        await db.commit()

    print("  Demo school + users + feature flags seeded.")


def main():
    import uvicorn

    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║   MwalimuKit — Local Development Mode    ║")
    print("  ╚══════════════════════════════════════════╝\n")

    asyncio.run(_setup())

    print("\n  API:  http://localhost:8000")
    print("  Docs: http://localhost:8000/docs")
    print("  ──────────────────────────────────────")
    print("  Teacher: teacher@demo.mwalimukit.go.ke / password123")
    print("  Admin:   admin@demo.mwalimukit.go.ke / password123")
    print("  ──────────────────────────────────────\n")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
