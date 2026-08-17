#!/usr/bin/env python3
from pathlib import Path
ROOT = Path("/home/merchant/mwalimukit")

def w(rel, content):
    target = ROOT / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print("wrote", rel)


# --- files appended below ---

w("api/Dockerfile", """FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
        build-essential libpq-dev curl \\
    && apt-get clean

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""")

w("api/alembic/env.py", """import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.models.base import Base
import app.models  # noqa: F401  (registers models on Base.metadata)

config = context.config
db_url = settings.database_url.replace('%', '%%')
if db_url.startswith("postgresql+psycopg://"):
    db_url = db_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
config.set_main_option('sqlalchemy.url', db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option('sqlalchemy.url'),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
        connect_args={"statement_cache_size": 0},
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
""")

w("api/alembic/versions/0001_initial.py", '''"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-17 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "schools",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False, unique=True),
        sa.Column("county", sa.Text(), nullable=True),
        sa.Column("level", sa.Text(), nullable=True),
        sa.Column("settings", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
                CREATE TYPE user_role AS ENUM ('teacher', 'school_admin', 'super_admin');
            END IF;
        END $$;
    """)

    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("school_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("email", sa.dialects.postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="teacher"),
        sa.CheckConstraint("role IN ('teacher', 'school_admin', 'super_admin')", name="ck_user_role"),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'curriculum_level') THEN
                CREATE TYPE curriculum_level AS ENUM ('lower_primary', 'upper_primary', 'jss');
            END IF;
        END $$;
    """)

    op.create_table(
        "learning_areas",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("level", sa.Text(), nullable=False),
        sa.CheckConstraint("level IN ('lower_primary', 'upper_primary', 'jss')", name="ck_learning_area_level"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "strands",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("learning_area_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("learning_areas.id"), nullable=False),
        sa.Column("code", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "sub_strands",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("strand_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("strands.id"), nullable=False),
        sa.Column("code", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'assessment_source') THEN
                CREATE TYPE assessment_source AS ENUM ('ai', 'manual', 'template');
            END IF;
        END $$;
    """)

    op.create_table(
        "assessments",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("school_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("learning_area_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("learning_areas.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.CheckConstraint("source IN ('ai', 'manual', 'template')", name="ck_assessment_source"),
        sa.Column("rubric", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("items", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("tags", sa.dialects.postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("is_favourite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "classes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("school_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("teacher_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("grade_level", sa.Text(), nullable=False),
        sa.Column("learning_area_ids", sa.dialects.postgresql.ARRAY(sa.dialects.postgresql.UUID(as_uuid=True)), nullable=False, server_default=sa.text("'{}'::uuid[]")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "learners",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("school_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("class_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("admission_no", sa.Text(), nullable=True),
        sa.Column("gender", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "assessment_runs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("school_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("class_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("assessment_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("term", sa.Text(), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_table(
        "scores",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("assessment_runs.id"), nullable=False),
        sa.Column("learner_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("run_id", "learner_id", "item_id", name="uq_scores_run_learner_item"),
    )

    op.create_table(
        "feature_flags",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute(
        sa.text(
            \"\"\"
            INSERT INTO feature_flags (key, value) VALUES
              ('paywall_enabled',       'false'::jsonb),
              ('ai_generation_enabled', 'true'::jsonb),
              ('max_classes',           'null'::jsonb),
              ('max_learners_per_class','null'::jsonb)
            ON CONFLICT (key) DO NOTHING
            \"\"\"
        )
    )


def downgrade() -> None:
    for t in [
        "scores", "assessment_runs", "learners", "classes", "assessments",
        "sub_strands", "strands", "learning_areas", "feature_flags",
        "users", "schools",
    ]:
        op.drop_table(t)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'assessment_source') THEN
                DROP TYPE assessment_source;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'curriculum_level') THEN
                DROP TYPE curriculum_level;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
                DROP TYPE user_role;
            END IF;
        END $$;
    """)
''')


w("api/app/__init__.py", '''"""MwalimuKit API package."""
__version__ = "0.1.0"
''')

w("api/app/main.py", '''"""FastAPI application entrypoint."""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    auth, assessments, classes, curriculum, feature_flags, health,
    learners, runs, scores, schools,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="MwalimuKit API",
        version="0.1.0",
        description="Backend for the MwalimuKit CBC assessment platform.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _log_startup() -> None:
        structlog.configure(
            processors=[structlog.processors.add_log_level, structlog.processors.JSONRenderer()],
            wrapper_class=structlog.make_filtering_bound_logger(20),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        log = structlog.get_logger()
        log.info("mwalimukit.api.startup", env=settings.env, version="0.1.0")

    app.include_router(health.router, tags=["health"])
    app.include_router(feature_flags.router, prefix="/api/v1", tags=["feature-flags"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(schools.router, prefix="/api/v1/schools", tags=["schools"])
    app.include_router(curriculum.router, prefix="/api/v1/curriculum", tags=["curriculum"])
    app.include_router(assessments.router, prefix="/api/v1/assessments", tags=["assessments"])
    app.include_router(classes.router, prefix="/api/v1/classes", tags=["classes"])
    app.include_router(learners.router, prefix="/api/v1/learners", tags=["learners"])
    app.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])
    app.include_router(scores.router, prefix="/api/v1/scores", tags=["scores"])

    return app


app = create_app()
''')


w("api/app/core/__init__.py", "")

w("api/app/core/config.py", '''"""Centralised settings, loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = Field(default="development", alias="API_ENV")
    api_port: int = Field(default=8000, alias="API_PORT")
    secret_key: str = Field(default="dev-secret-change-me", alias="API_SECRET_KEY")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"], alias="API_CORS_ORIGINS")

    database_url: str = Field(default="postgresql+psycopg://mwalimu:mwalimu@db:5432/mwalimukit", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    ai_provider: str = Field(default="mock", alias="AI_PROVIDER")
    ai_api_key: str = Field(default="", alias="AI_API_KEY")
    ai_model: str = Field(default="gpt-4o-mini", alias="AI_MODEL")

    feature_paywall_enabled: bool = Field(default=False, alias="FEATURE_PAYWALL_ENABLED")
    feature_ai_generation_enabled: bool = Field(default=True, alias="FEATURE_AI_GENERATION_ENABLED")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
''')

w("api/app/core/db.py", '''"""SQLAlchemy async engine + session factory."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _to_async_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(_to_async_url(settings.database_url), future=True, pool_pre_ping=True, connect_args={"statement_cache_size": 0})
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
''')

w("api/app/core/security.py", '''"""Password hashing + JWT helpers."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

JWT_ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject: str, ttl: timedelta, token_type: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(minutes=settings.access_token_ttl_minutes), "access")


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(days=settings.refresh_token_ttl_days), "refresh")


def decode_token(token: str) -> dict:
    """Raise JWTError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
''')

w("api/app/core/deps.py", '''"""Common FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_token
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exc
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc from None

    user = (
        await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    ).scalar_one_or_none()
    if user is None:
        raise credentials_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
''')


w("api/app/models/__init__.py", '''"""Import every model module here so Alembic can find them."""
from app.models.school import School
from app.models.user import User
from app.models.curriculum import LearningArea, Strand, SubStrand
from app.models.assessment import Assessment
from app.models.school_class import SchoolClass
from app.models.learner import Learner
from app.models.run import AssessmentRun
from app.models.score import Score
from app.models.feature_flag import FeatureFlag

__all__ = [
    "School", "User", "LearningArea", "Strand", "SubStrand", "Assessment",
    "SchoolClass", "Learner", "AssessmentRun", "Score", "FeatureFlag",
]
''')

w("api/app/models/base.py", '''"""Declarative base + shared mixins."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPK:
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
''')

w("api/app/models/school.py", '''"""School model."""
from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class School(UUIDPK, Timestamped, Base):
    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    county: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
''')

w("api/app/models/user.py", '''"""User model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import CITEXT, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class UserRole(str, PyEnum):
    teacher = "teacher"
    school_admin = "school_admin"
    super_admin = "super_admin"


class User(UUIDPK, Timestamped, Base):
    __tablename__ = "users"

    school_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True),
        nullable=False,
        default=UserRole.teacher,
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
''')

w("api/app/models/curriculum.py", '''"""Curriculum models: LearningArea -> Strand -> SubStrand."""
from __future__ import annotations

from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class CurriculumLevel(str, PyEnum):
    lower_primary = "lower_primary"
    upper_primary = "upper_primary"
    jss = "jss"


class LearningArea(UUIDPK, Timestamped, Base):
    __tablename__ = "learning_areas"

    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[CurriculumLevel] = mapped_column(
        Enum(CurriculumLevel, name="curriculum_level", native_enum=True), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Strand(UUIDPK, Timestamped, Base):
    __tablename__ = "strands"

    learning_area_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("learning_areas.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SubStrand(UUIDPK, Timestamped, Base):
    __tablename__ = "sub_strands"

    strand_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("strands.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
''')

w("api/app/models/assessment.py", '''"""Assessment template model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class AssessmentSource(str, PyEnum):
    ai = "ai"
    manual = "manual"
    template = "template"


class Assessment(UUIDPK, Timestamped, Base):
    __tablename__ = "assessments"

    owner_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    school_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    learning_area_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("learning_areas.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[AssessmentSource] = mapped_column(
        Enum(AssessmentSource, name="assessment_source", native_enum=True),
        nullable=False,
        default=AssessmentSource.manual,
    )
    rubric: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    is_favourite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
''')

w("api/app/models/school_class.py", '''"""Class model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class SchoolClass(UUIDPK, Timestamped, Base):
    __tablename__ = "classes"

    school_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    teacher_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    grade_level: Mapped[str] = mapped_column(Text, nullable=False)
    learning_area_ids: Mapped[list["__import__('uuid').UUID"]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)), nullable=False, default=list
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
''')

w("api/app/models/learner.py", '''"""Learner model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class Learner(UUIDPK, Timestamped, Base):
    __tablename__ = "learners"

    school_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    class_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("classes.id"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    admission_no: Mapped[str | None] = mapped_column(Text, nullable=True)
    gender: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
''')

w("api/app/models/run.py", '''"""Assessment run model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPK


class AssessmentRun(UUIDPK, Base):
    __tablename__ = "assessment_runs"

    school_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    class_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("classes.id"), nullable=False
    )
    assessment_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False
    )
    term: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
''')

w("api/app/models/score.py", '''"""Score model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPK


class Score(UUIDPK, Base):
    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("run_id", "learner_id", "item_id", name="uq_scores_run_learner_item"),
    )

    run_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assessment_runs.id"), nullable=False
    )
    learner_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("learners.id"), nullable=False
    )
    item_id: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
''')

w("api/app/models/feature_flag.py", '''"""Feature flag model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[object] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
''')


w("api/app/schemas/__init__.py", "")

w("api/app/schemas/auth.py", '''"""Auth request/response schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    school_code: str = Field(min_length=4, max_length=16)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: UUID
    school_id: UUID
    email: EmailStr
    full_name: str
    role: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
''')

w("api/app/schemas/curriculum.py", '''"""Curriculum schemas."""
from __future__ import annotations

from pydantic import BaseModel


class LearningAreaOut(BaseModel):
    code: str
    name: str
    level: str
    sort_order: int


class StrandOut(BaseModel):
    code: str
    learning_area_code: str
    name: str
    sort_order: int


class SubStrandOut(BaseModel):
    code: str
    strand_code: str
    name: str
    sort_order: int


class CurriculumCatalogue(BaseModel):
    learning_areas: list[LearningAreaOut]
    strands: list[StrandOut]
    sub_strands: list[SubStrandOut]
''')

w("api/app/schemas/assessment.py", '''"""Assessment + AI generation schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RubricLevel(BaseModel):
    level: int = Field(ge=1, le=4)
    label: str
    descriptor: str = ""


class RubricCriterion(BaseModel):
    id: str
    label: str


class Rubric(BaseModel):
    levels: list[RubricLevel]
    criteria: list[RubricCriterion]


class AssessmentItem(BaseModel):
    id: str
    criterion: str
    stem: str
    answer_guide: str | None = None
    max_level: int = 4


class GenerateAssessmentRequest(BaseModel):
    learning_area_code: str
    strand_code: str
    sub_strand_codes: list[str] = Field(min_length=1)
    grade_level: str
    teacher_prompt: str | None = None
    item_count: int = Field(default=5, ge=1, le=10)


class GenerateAssessmentResponse(BaseModel):
    rubric: Rubric
    items: list[AssessmentItem]
    provider: str
    model: str


class AssessmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    learning_area_code: str
    strand_code: str
    sub_strand_codes: list[str]
    source: str = "manual"
    rubric: Rubric
    items: list[AssessmentItem]
    tags: list[str] = Field(default_factory=list)
    is_favourite: bool = False


class AssessmentOut(AssessmentIn):
    id: UUID
    owner_id: UUID
    school_id: UUID
    created_at: str
    updated_at: str
    deleted_at: str | None = None
''')

w("api/app/schemas/classes.py", '''"""Class + learner schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    grade_level: str = Field(min_length=1, max_length=16)
    learning_area_codes: list[str] = Field(default_factory=list)


class ClassOut(ClassIn):
    id: UUID
    school_id: UUID
    teacher_id: UUID
    deleted_at: str | None = None
    created_at: str
    updated_at: str


class LearnerIn(BaseModel):
    class_id: UUID
    full_name: str = Field(min_length=1, max_length=120)
    admission_no: str | None = None
    gender: str | None = None


class LearnerBulkIn(BaseModel):
    class_id: UUID
    lines: list[str] = Field(min_length=1)


class LearnerOut(BaseModel):
    id: UUID
    school_id: UUID
    class_id: UUID
    full_name: str
    admission_no: str | None
    gender: str | None
    deleted_at: str | None
''')

w("api/app/schemas/run_score.py", '''"""Run + score schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RunIn(BaseModel):
    class_id: UUID
    assessment_id: UUID
    term: str | None = None


class RunOut(BaseModel):
    id: UUID
    school_id: UUID
    class_id: UUID
    assessment_id: UUID
    term: str | None
    started_at: str
    closed_at: str | None


class ScoreIn(BaseModel):
    id: UUID
    run_id: UUID
    learner_id: UUID
    item_id: str
    level: int | None = Field(default=None, ge=1, le=4)
    note: str | None = None
    updated_at: str


class ScoreBatchIn(BaseModel):
    scores: list[ScoreIn]


class ScoreBatchResult(BaseModel):
    accepted: int
    rejected: list[dict]
''')

w("api/app/schemas/feature_flags.py", '''"""Feature flag schemas."""
from __future__ import annotations

from pydantic import BaseModel


class FeatureFlagsOut(BaseModel):
    paywall_enabled: bool
    ai_generation_enabled: bool
    max_classes: int | None
    max_learners_per_class: int | None
''')


w("api/app/services/__init__.py", "")

w("api/app/services/auth.py", '''"""Auth business logic."""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token, create_refresh_token, hash_password, verify_password,
)
from app.models.school import School
from app.models.user import User, UserRole
from app.schemas.auth import SignupRequest, TokenPair, UserOut


async def signup(db: AsyncSession, payload: SignupRequest) -> TokenPair:
    school = (
        await db.execute(select(School).where(School.code == payload.school_code))
    ).scalar_one_or_none()
    if school is None:
        raise ValueError("School code not found. Ask your school admin for the join code.")

    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing is not None:
        raise ValueError("Email already registered. Try logging in.")

    user = User(
        id=uuid4(),
        school_id=school.id,
        email=payload.email,
        full_name=payload.full_name,
        role=UserRole.teacher,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return _pair(user)


async def login(db: AsyncSession, *, email: str, password: str) -> TokenPair:
    user = (
        await db.execute(select(User).where(User.email == email, User.is_active.is_(True)))
    ).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password.")
    return _pair(user)


def _pair(user: User) -> TokenPair:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserOut(
            id=user.id,
            school_id=user.school_id,
            email=user.email,
            full_name=user.full_name,
            role=role,
        ),
    )
''')

w("api/app/services/scores.py", '''"""Score batching with last-write-wins."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.score import Score
from app.schemas.run_score import ScoreBatchIn, ScoreBatchResult, ScoreIn


async def upsert_scores(db: AsyncSession, school_id, batch: ScoreBatchIn) -> ScoreBatchResult:
    accepted = 0
    rejected: list[dict] = []

    for s in batch.scores:
        try:
            updated_at = datetime.fromisoformat(s.updated_at.replace("Z", "+00:00"))
            stmt = (
                pg_insert(Score)
                .values(
                    id=s.id,
                    run_id=s.run_id,
                    learner_id=s.learner_id,
                    item_id=s.item_id,
                    level=s.level,
                    note=s.note,
                    updated_at=updated_at,
                )
                .on_conflict_do_update(
                    index_elements=["run_id", "learner_id", "item_id"],
                    set_={"level": s.level, "note": s.note, "updated_at": updated_at},
                )
            )
            await db.execute(stmt)
            accepted += 1
        except Exception as exc:  # noqa: BLE001
            rejected.append({"id": str(s.id), "reason": str(exc)})

    await db.commit()
    return ScoreBatchResult(accepted=accepted, rejected=rejected)
''')


w("api/app/ai/__init__.py", "")

w("api/app/ai/provider.py", '''"""Pluggable AI provider interface."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class GeneratedAssessment:
    rubric: dict
    items: list[dict]
    provider: str
    model: str


class AIProvider(Protocol):
    async def generate_assessment(
        self,
        *,
        learning_area: str,
        strand: str,
        sub_strand: str,
        grade_level: str,
        teacher_prompt: str | None = None,
        item_count: int = 5,
    ) -> GeneratedAssessment: ...


def build_system_prompt() -> str:
    return (
        "You design rubric-aligned formative assessments for Kenyan CBC teachers.\\n"
        "- Use Kenyan context (names like Achieng, Baraka, Wanjiku; places like Nairobi, Kisumu; "
        "currency in KES).\\n"
        "- Use the official 4-level vocabulary: "
        "'Below expectation', 'Approaching expectation', 'Meeting expectation', 'Exceeding expectation'.\\n"
        "- Output valid JSON only — no prose.\\n"
    )


def build_user_prompt(
    *,
    learning_area: str,
    strand: str,
    sub_strand: str,
    grade_level: str,
    teacher_prompt: str | None,
    item_count: int,
) -> str:
    extra = f"\\nTeacher guidance: {teacher_prompt}" if teacher_prompt else ""
    return (
        f"Generate a formative assessment.\\n"
        f"Learning area: {learning_area}\\n"
        f"Strand: {strand}\\n"
        f"Sub-strand: {sub_strand}\\n"
        f"Grade level: {grade_level}\\n"
        f"Item count: {item_count}{extra}\\n\\n"
        "Return JSON with this shape:\\n"
        "{\\n"
        '  "rubric": {\\n'
        '    "levels": [\\n'
        '      {"level": 1, "label": "Below expectation", "descriptor": "..."},\\n'
        '      {"level": 2, "label": "Approaching expectation", "descriptor": "..."},\\n'
        '      {"level": 3, "label": "Meeting expectation", "descriptor": "..."},\\n'
        '      {"level": 4, "label": "Exceeding expectation", "descriptor": "..."}\\n'
        "    ],\\n"
        '    "criteria": [{"id": "accuracy", "label": "Accuracy of response"}]\\n'
        "  },\\n"
        '  "items": [\\n'
        '    {"id": "itm_01", "criterion": "accuracy", "stem": "...", "answer_guide": "...", "max_level": 4}\\n'
        "  ]\\n"
        "}"
    )
''')

w("api/app/ai/mock_provider.py", '''"""Deterministic stub provider."""
from __future__ import annotations

from app.ai.provider import GeneratedAssessment


class MockProvider:
    name = "mock"
    model = "mock-v1"

    async def generate_assessment(
        self,
        *,
        learning_area: str,
        strand: str,
        sub_strand: str,
        grade_level: str,
        teacher_prompt: str | None = None,
        item_count: int = 5,
    ) -> GeneratedAssessment:
        items: list[dict] = []
        for i in range(1, item_count + 1):
            items.append(
                {
                    "id": f"itm_{i:02d}",
                    "criterion": "accuracy",
                    "stem": (
                        f"[Mock draft {i}] A short, age-appropriate question for "
                        f"{grade_level} learners on '{sub_strand}' in {learning_area} ({strand}). "
                        "Replace with your own item."
                    ),
                    "answer_guide": "Edit me.",
                    "max_level": 4,
                }
            )
        rubric = {
            "levels": [
                {"level": 1, "label": "Below expectation",       "descriptor": "Needs significant support."},
                {"level": 2, "label": "Approaching expectation", "descriptor": "Responds with some guidance."},
                {"level": 3, "label": "Meeting expectation",     "descriptor": "Responds correctly with reasoning."},
                {"level": 4, "label": "Exceeding expectation",    "descriptor": "Responds confidently and extends ideas."},
            ],
            "criteria": [
                {"id": "accuracy",  "label": "Accuracy of response"},
                {"id": "reasoning", "label": "Reasoning / justification"},
            ],
        }
        return GeneratedAssessment(rubric=rubric, items=items, provider=self.name, model=self.model)
''')

w("api/app/ai/openai_provider.py", '''"""OpenAI-backed provider."""
from __future__ import annotations

import json

from openai import AsyncOpenAI

from app.ai.provider import (
    GeneratedAssessment, build_system_prompt, build_user_prompt,
)


class OpenAIProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    async def generate_assessment(
        self,
        *,
        learning_area: str,
        strand: str,
        sub_strand: str,
        grade_level: str,
        teacher_prompt: str | None = None,
        item_count: int = 5,
    ) -> GeneratedAssessment:
        prompt = build_user_prompt(
            learning_area=learning_area,
            strand=strand,
            sub_strand=sub_strand,
            grade_level=grade_level,
            teacher_prompt=teacher_prompt,
            item_count=item_count,
        )
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        text = resp.choices[0].message.content or "{}"
        data = json.loads(text)
        return GeneratedAssessment(
            rubric=data.get("rubric", {}),
            items=data.get("items", []),
            provider=self.name,
            model=self._model,
        )
''')

w("api/app/ai/factory.py", '''"""Pick the AI provider based on settings."""
from __future__ import annotations

from app.ai.mock_provider import MockProvider
from app.ai.provider import AIProvider
from app.core.config import settings


def get_provider() -> AIProvider:
    provider = (settings.ai_provider or "mock").lower()
    if provider == "openai" and settings.ai_api_key:
        from app.ai.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=settings.ai_api_key, model=settings.ai_model)
    return MockProvider()
''')


w("api/app/routers/__init__.py", "")

w("api/app/routers/health.py", '''"""Healthcheck."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "mwalimukit-api", "version": "0.1.0"}
''')

w("api/app/routers/feature_flags.py", '''"""Public feature flags endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.feature_flag import FeatureFlag
from app.schemas.feature_flags import FeatureFlagsOut


router = APIRouter()


@router.get("/feature-flags", response_model=FeatureFlagsOut)
async def get_flags(db: AsyncSession = Depends(get_db)) -> FeatureFlagsOut:
    rows = (await db.execute(select(FeatureFlag))).scalars().all()
    raw = {r.key: r.value for r in rows}

    def _bool(key: str, default: bool) -> bool:
        v = raw.get(key, default)
        return bool(v) if v is not None else default

    def _int_or_none(key: str) -> int | None:
        v = raw.get(key)
        return int(v) if isinstance(v, (int, float)) else None

    return FeatureFlagsOut(
        paywall_enabled=_bool("paywall_enabled", False),
        ai_generation_enabled=_bool("ai_generation_enabled", True),
        max_classes=_int_or_none("max_classes"),
        max_learners_per_class=_int_or_none("max_learners_per_class"),
    )
''')

w("api/app/routers/auth.py", '''"""Auth router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.auth import LoginRequest, SignupRequest, TokenPair
from app.services.auth import login as svc_login
from app.services.auth import signup as svc_signup


router = APIRouter()


@router.post("/signup", response_model=TokenPair)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        return await svc_signup(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        return await svc_login(db, email=payload.email, password=payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None
''')

w("api/app/routers/schools.py", '''"""Schools router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.school import School


router = APIRouter()


@router.get("/me")
async def my_school(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    school = (
        await db.execute(select(School).where(School.id == user.school_id))
    ).scalar_one_or_none()
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    return {
        "id": str(school.id),
        "name": school.name,
        "code": school.code,
        "county": school.county,
        "level": school.level,
    }
''')

w("api/app/routers/curriculum.py", '''"""Curriculum router — returns the catalogue that the PWA caches."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.curriculum import LearningArea, Strand, SubStrand
from app.schemas.curriculum import (
    CurriculumCatalogue, LearningAreaOut, StrandOut, SubStrandOut,
)


router = APIRouter()


@router.get("/catalogue", response_model=CurriculumCatalogue)
async def get_catalogue(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> CurriculumCatalogue:
    _ = user  # auth required so the catalogue is not a public dump
    las = (await db.execute(select(LearningArea).order_by(LearningArea.sort_order))).scalars().all()
    ss = (await db.execute(select(Strand).order_by(Strand.sort_order))).scalars().all()
    subs = (await db.execute(select(SubStrand).order_by(SubStrand.sort_order))).scalars().all()

    la_map = {la.id: la for la in las}
    strand_map = {s.id: s for s in ss}

    return CurriculumCatalogue(
        learning_areas=[
            LearningAreaOut(code=la.code, name=la.name, level=la.level.value, sort_order=la.sort_order)
            for la in las
        ],
        strands=[
            StrandOut(
                code=s.code,
                learning_area_code=la_map[s.learning_area_id].code,
                name=s.name,
                sort_order=s.sort_order,
            )
            for s in ss
            if s.learning_area_id in la_map
        ],
        sub_strands=[
            SubStrandOut(
                code=ss_obj.code,
                strand_code=strand_map[ss_obj.strand_id].code,
                name=ss_obj.name,
                sort_order=ss_obj.sort_order,
            )
            for ss_obj in subs
            if ss_obj.strand_id in strand_map
        ],
    )
''')

w("api/app/routers/assessments.py", '''"""Assessment generation + CRUD."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_provider
from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.assessment import Assessment, AssessmentSource
from app.models.curriculum import LearningArea
from app.schemas.assessment import (
    AssessmentIn, AssessmentOut, GenerateAssessmentRequest, GenerateAssessmentResponse,
)


router = APIRouter()


@router.post("/generate", response_model=GenerateAssessmentResponse)
async def generate(req: GenerateAssessmentRequest, user: CurrentUser) -> GenerateAssessmentResponse:
    provider = get_provider()
    result = await provider.generate_assessment(
        learning_area=req.learning_area_code,
        strand=req.strand_code,
        sub_strand=", ".join(req.sub_strand_codes),
        grade_level=req.grade_level,
        teacher_prompt=req.teacher_prompt,
        item_count=req.item_count,
    )
    return GenerateAssessmentResponse(
        rubric=result.rubric,
        items=result.items,
        provider=result.provider,
        model=result.model,
    )


@router.get("", response_model=list[AssessmentOut])
async def list_assessments(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[AssessmentOut]:
    rows = (
        await db.execute(
            select(Assessment)
            .where(Assessment.school_id == user.school_id, Assessment.deleted_at.is_(None))
            .order_by(Assessment.updated_at.desc())
        )
    ).scalars().all()
    return [_to_out(a) for a in rows]


@router.post("", response_model=AssessmentOut)
async def create_assessment(
    payload: AssessmentIn, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> AssessmentOut:
    la = (
        await db.execute(select(LearningArea).where(LearningArea.code == payload.learning_area_code))
    ).scalar_one_or_none()
    if la is None:
        raise HTTPException(status_code=400, detail="Unknown learning_area_code")

    source = AssessmentSource(payload.source) if payload.source in {s.value for s in AssessmentSource} else AssessmentSource.manual
    a = Assessment(
        id=uuid4(),
        owner_id=user.id,
        school_id=user.school_id,
        learning_area_id=la.id,
        name=payload.name,
        description=payload.description,
        source=source,
        rubric=payload.rubric.model_dump(),
        items=[i.model_dump() for i in payload.items],
        tags=payload.tags,
        is_favourite=payload.is_favourite,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return _to_out(a)


@router.get("/{assessment_id}", response_model=AssessmentOut)
async def get_assessment(
    assessment_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> AssessmentOut:
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return _to_out(a)


@router.delete("/{assessment_id}")
async def soft_delete(
    assessment_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id, Assessment.school_id == user.school_id
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    a.deleted_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return {"deleted": True}


def _to_out(a: Assessment) -> AssessmentOut:
    return AssessmentOut(
        id=a.id,
        owner_id=a.owner_id,
        school_id=a.school_id,
        name=a.name,
        description=a.description,
        learning_area_code="",
        strand_code="",
        sub_strand_codes=[],
        source=a.source.value if hasattr(a.source, "value") else str(a.source),
        rubric=a.rubric,
        items=a.items,
        tags=a.tags,
        is_favourite=a.is_favourite,
        created_at=a.created_at.isoformat(),
        updated_at=a.updated_at.isoformat(),
        deleted_at=a.deleted_at.isoformat() if a.deleted_at else None,
    )
''')

w("api/app/routers/classes.py", '''"""Classes CRUD."""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.school_class import SchoolClass
from app.schemas.classes import ClassIn, ClassOut


router = APIRouter()


@router.get("", response_model=list[ClassOut])
async def list_classes(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[ClassOut]:
    rows = (
        await db.execute(
            select(SchoolClass)
            .where(SchoolClass.teacher_id == user.id, SchoolClass.deleted_at.is_(None))
            .order_by(SchoolClass.created_at.desc())
        )
    ).scalars().all()
    return [_to_out(c) for c in rows]


@router.post("", response_model=ClassOut)
async def create_class(payload: ClassIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> ClassOut:
    c = SchoolClass(
        id=uuid4(),
        school_id=user.school_id,
        teacher_id=user.id,
        name=payload.name,
        grade_level=payload.grade_level,
        learning_area_ids=[],
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _to_out(c)


@router.get("/{class_id}", response_model=ClassOut)
async def get_class(class_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> ClassOut:
    c = (
        await db.execute(
            select(SchoolClass).where(
                SchoolClass.id == class_id,
                SchoolClass.teacher_id == user.id,
                SchoolClass.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return _to_out(c)


def _to_out(c: SchoolClass) -> ClassOut:
    return ClassOut(
        id=c.id,
        school_id=c.school_id,
        teacher_id=c.teacher_id,
        name=c.name,
        grade_level=c.grade_level,
        learning_area_codes=[],
        deleted_at=c.deleted_at.isoformat() if c.deleted_at else None,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )
''')

w("api/app/routers/learners.py", '''"""Learner CRUD."""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.learner import Learner
from app.models.school_class import SchoolClass
from app.schemas.classes import LearnerBulkIn, LearnerIn, LearnerOut


router = APIRouter()


async def _class_owned(db: AsyncSession, teacher_id: UUID, class_id: UUID) -> SchoolClass:
    c = (
        await db.execute(
            select(SchoolClass).where(
                SchoolClass.id == class_id, SchoolClass.teacher_id == teacher_id
            )
        )
    ).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return c


@router.get("/by-class/{class_id}", response_model=list[LearnerOut])
async def list_for_class(
    class_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> list[LearnerOut]:
    await _class_owned(db, user.id, class_id)
    rows = (
        await db.execute(
            select(Learner)
            .where(Learner.class_id == class_id, Learner.deleted_at.is_(None))
            .order_by(Learner.full_name)
        )
    ).scalars().all()
    return [_to_out(l) for l in rows]


@router.post("", response_model=LearnerOut)
async def add_learner(payload: LearnerIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> LearnerOut:
    await _class_owned(db, user.id, payload.class_id)
    l = Learner(
        id=uuid4(),
        school_id=user.school_id,
        class_id=payload.class_id,
        full_name=payload.full_name.strip(),
        admission_no=payload.admission_no,
        gender=payload.gender,
    )
    db.add(l)
    await db.commit()
    await db.refresh(l)
    return _to_out(l)


@router.post("/bulk", response_model=list[LearnerOut])
async def bulk_add(payload: LearnerBulkIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[LearnerOut]:
    await _class_owned(db, user.id, payload.class_id)
    learners: list[Learner] = []
    for raw in payload.lines:
        raw = raw.strip()
        if not raw:
            continue
        if "," in raw:
            name, _, adm = raw.partition(",")
            adm = adm.strip() or None
        else:
            name, adm = raw, None
        l = Learner(
            id=uuid4(),
            school_id=user.school_id,
            class_id=payload.class_id,
            full_name=name.strip(),
            admission_no=adm,
        )
        db.add(l)
        learners.append(l)
    await db.commit()
    for l in learners:
        await db.refresh(l)
    return [_to_out(l) for l in learners]


def _to_out(l: Learner) -> LearnerOut:
    return LearnerOut(
        id=l.id,
        school_id=l.school_id,
        class_id=l.class_id,
        full_name=l.full_name,
        admission_no=l.admission_no,
        gender=l.gender,
        deleted_at=l.deleted_at.isoformat() if l.deleted_at else None,
    )
''')

w("api/app/routers/runs.py", '''"""Assessment runs (a session of an assessment against a class)."""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.assessment import Assessment
from app.models.run import AssessmentRun
from app.models.school_class import SchoolClass
from app.schemas.run_score import RunIn, RunOut


router = APIRouter()


@router.post("", response_model=RunOut)
async def start_run(payload: RunIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> RunOut:
    cls = (
        await db.execute(
            select(SchoolClass).where(
                SchoolClass.id == payload.class_id, SchoolClass.teacher_id == user.id
            )
        )
    ).scalar_one_or_none()
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")

    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == payload.assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    r = AssessmentRun(
        id=uuid4(),
        school_id=user.school_id,
        class_id=payload.class_id,
        assessment_id=payload.assessment_id,
        term=payload.term,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return _to_out(r)


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> RunOut:
    r = (
        await db.execute(
            select(AssessmentRun).where(
                AssessmentRun.id == run_id, AssessmentRun.school_id == user.school_id
            )
        )
    ).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_out(r)


def _to_out(r: AssessmentRun) -> RunOut:
    return RunOut(
        id=r.id,
        school_id=r.school_id,
        class_id=r.class_id,
        assessment_id=r.assessment_id,
        term=r.term,
        started_at=r.started_at.isoformat(),
        closed_at=r.closed_at.isoformat() if r.closed_at else None,
    )
''')

w("api/app/routers/scores.py", '''"""Score batching endpoints (offline sync target)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.schemas.run_score import ScoreBatchIn, ScoreBatchResult
from app.services.scores import upsert_scores


router = APIRouter()


@router.post("/batch", response_model=ScoreBatchResult)
async def post_batch(
    payload: ScoreBatchIn, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> ScoreBatchResult:
    # School scoping is enforced via the runs the scores reference.
    # v1.x adds an explicit school-id check on each run_id.
    return await upsert_scores(db, user.school_id, payload)
''')


w("api/app/scripts/__init__.py", "")

w("api/app/scripts/seed_curriculum.py", '''"""Seed the curriculum catalogue from the in-Python mirror of the TS catalogue.

The TypeScript catalogue in packages/shared/curriculum/data/catalogue.ts is the
canonical source. This module is a hand-maintained mirror so the seed script
does not need a TS toolchain. If you add a new strand/sub-strand in the TS
catalogue, mirror it here too.
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.models.curriculum import CurriculumLevel, LearningArea, Strand, SubStrand


CATALOGUE: dict = {
    "learning_areas": [
        {"code": "LP-MATH",  "name": "Mathematics",                  "level": "lower_primary", "sort_order": 10},
        {"code": "LP-ENG",   "name": "English",                      "level": "lower_primary", "sort_order": 20},
        {"code": "LP-KIS",   "name": "Kiswahili",                    "level": "lower_primary", "sort_order": 30},
        {"code": "LP-SCI",   "name": "Science and Technology",       "level": "lower_primary", "sort_order": 40},
        {"code": "LP-SST",   "name": "Social Studies",               "level": "lower_primary", "sort_order": 50},
        {"code": "LP-AGR",   "name": "Agriculture and Nutrition",    "level": "lower_primary", "sort_order": 60},
        {"code": "LP-CRE",   "name": "Christian Religious Education","level": "lower_primary", "sort_order": 70},
        {"code": "LP-ART",   "name": "Creative Arts",                "level": "lower_primary", "sort_order": 80},
        {"code": "LP-PE",    "name": "Physical and Health Education","level": "lower_primary", "sort_order": 90},
        {"code": "JSS-ENG",  "name": "English",                      "level": "jss", "sort_order": 110},
        {"code": "JSS-MATH", "name": "Mathematics",                  "level": "jss", "sort_order": 120},
        {"code": "JSS-SCI",  "name": "Integrated Science",           "level": "jss", "sort_order": 130},
    ],
    "strands": [
        {"code": "LP-MATH-NUM", "learning_area_code": "LP-MATH", "name": "Numbers", "sort_order": 1},
        {"code": "LP-MATH-MEA", "learning_area_code": "LP-MATH", "name": "Measurement", "sort_order": 2},
        {"code": "LP-MATH-GEO", "learning_area_code": "LP-MATH", "name": "Geometry", "sort_order": 3},
        {"code": "LP-MATH-DAT", "learning_area_code": "LP-MATH", "name": "Data Handling", "sort_order": 4},
        {"code": "LP-ENG-LIS",  "learning_area_code": "LP-ENG",  "name": "Listening and Speaking", "sort_order": 1},
        {"code": "LP-ENG-READ", "learning_area_code": "LP-ENG",  "name": "Reading", "sort_order": 2},
        {"code": "LP-ENG-WRIT", "learning_area_code": "LP-ENG",  "name": "Writing", "sort_order": 3},
        {"code": "LP-ENG-GRAM", "learning_area_code": "LP-ENG",  "name": "Grammar Usage", "sort_order": 4},
        {"code": "LP-KIS-KUS",  "learning_area_code": "LP-KIS",  "name": "Kusikiliza na Kuzungumza", "sort_order": 1},
        {"code": "LP-KIS-KUSO", "learning_area_code": "LP-KIS",  "name": "Kusoma", "sort_order": 2},
        {"code": "LP-KIS-KUAN", "learning_area_code": "LP-KIS",  "name": "Kuandika", "sort_order": 3},
        {"code": "LP-SCI-LIV",  "learning_area_code": "LP-SCI",  "name": "Living Things and Their Environment", "sort_order": 1},
        {"code": "LP-SCI-ENE",  "learning_area_code": "LP-SCI",  "name": "Energy", "sort_order": 2},
        {"code": "LP-SCI-EAR",  "learning_area_code": "LP-SCI",  "name": "Earth and Space", "sort_order": 3},
        {"code": "LP-SST-HER",  "learning_area_code": "LP-SST",  "name": "Heritage", "sort_order": 1},
        {"code": "LP-SST-CIT",  "learning_area_code": "LP-SST",  "name": "Citizenship", "sort_order": 2},
        {"code": "LP-SST-RES",  "learning_area_code": "LP-SST",  "name": "Resources and Economic Activities", "sort_order": 3},
        {"code": "LP-AGR-CRP",  "learning_area_code": "LP-AGR",  "name": "Crop Production", "sort_order": 1},
        {"code": "LP-AGR-NUT",  "learning_area_code": "LP-AGR",  "name": "Nutrition and Hygiene", "sort_order": 2},
        {"code": "LP-CRE-BIB",  "learning_area_code": "LP-CRE",  "name": "The Bible", "sort_order": 1},
        {"code": "LP-CRE-CRE",  "learning_area_code": "LP-CRE",  "name": "Christian Values", "sort_order": 2},
        {"code": "LP-ART-MUS",  "learning_area_code": "LP-ART",  "name": "Music", "sort_order": 1},
        {"code": "LP-ART-ART",  "learning_area_code": "LP-ART",  "name": "Art and Craft", "sort_order": 2},
        {"code": "LP-PE-MOV",   "learning_area_code": "LP-PE",   "name": "Movement", "sort_order": 1},
        {"code": "LP-PE-HEAL",  "learning_area_code": "LP-PE",   "name": "Health and Hygiene", "sort_order": 2},
        {"code": "JSS-ENG-LIS",  "learning_area_code": "JSS-ENG",  "name": "Listening and Speaking", "sort_order": 1},
        {"code": "JSS-ENG-READ", "learning_area_code": "JSS-ENG",  "name": "Reading", "sort_order": 2},
        {"code": "JSS-ENG-WRIT", "learning_area_code": "JSS-ENG",  "name": "Writing", "sort_order": 3},
        {"code": "JSS-MATH-NUM", "learning_area_code": "JSS-MATH", "name": "Numbers and Algebra", "sort_order": 1},
        {"code": "JSS-MATH-MEA", "learning_area_code": "JSS-MATH", "name": "Measurement", "sort_order": 2},
        {"code": "JSS-MATH-GEO", "learning_area_code": "JSS-MATH", "name": "Geometry", "sort_order": 3},
        {"code": "JSS-SCI-LIV",  "learning_area_code": "JSS-SCI",  "name": "Living Things", "sort_order": 1},
        {"code": "JSS-SCI-CHM",  "learning_area_code": "JSS-SCI",  "name": "Chemistry basics", "sort_order": 2},
        {"code": "JSS-SCI-PHY",  "learning_area_code": "JSS-SCI",  "name": "Physics basics", "sort_order": 3},
    ],
    "sub_strands": [
        {"code": "LP-MATH-NUM-1.1", "strand_code": "LP-MATH-NUM", "name": "Counting 0 to 20", "sort_order": 1},
        {"code": "LP-MATH-NUM-1.2", "strand_code": "LP-MATH-NUM", "name": "Place value 0 to 20", "sort_order": 2},
        {"code": "LP-MATH-NUM-2.1", "strand_code": "LP-MATH-NUM", "name": "Counting 0 to 100", "sort_order": 3},
        {"code": "LP-MATH-NUM-2.2", "strand_code": "LP-MATH-NUM", "name": "Addition within 20", "sort_order": 4},
        {"code": "LP-MATH-NUM-2.3", "strand_code": "LP-MATH-NUM", "name": "Subtraction within 20", "sort_order": 5},
        {"code": "LP-MATH-NUM-3.1", "strand_code": "LP-MATH-NUM", "name": "Counting in 2s, 5s and 10s", "sort_order": 6},
        {"code": "LP-MATH-MEA-1.1", "strand_code": "LP-MATH-MEA", "name": "Comparing length", "sort_order": 1},
        {"code": "LP-MATH-MEA-2.1", "strand_code": "LP-MATH-MEA", "name": "Measuring length in centimetres", "sort_order": 2},
        {"code": "LP-MATH-MEA-2.2", "strand_code": "LP-MATH-MEA", "name": "Mass (heavier/lighter)", "sort_order": 3},
        {"code": "LP-MATH-MEA-3.1", "strand_code": "LP-MATH-MEA", "name": "Telling the time (o'clock)", "sort_order": 4},
        {"code": "LP-MATH-GEO-1.1", "strand_code": "LP-MATH-GEO", "name": "Shapes in the environment", "sort_order": 1},
        {"code": "LP-MATH-GEO-2.1", "strand_code": "LP-MATH-GEO", "name": "Sorting 2D shapes", "sort_order": 2},
        {"code": "LP-MATH-GEO-3.1", "strand_code": "LP-MATH-GEO", "name": "Patterns with shapes", "sort_order": 3},
        {"code": "LP-MATH-DAT-2.1", "strand_code": "LP-MATH-DAT", "name": "Sorting objects into groups", "sort_order": 1},
        {"code": "LP-MATH-DAT-3.1", "strand_code": "LP-MATH-DAT", "name": "Pictographs", "sort_order": 2},
        {"code": "LP-ENG-LIS-1.1", "strand_code": "LP-ENG-LIS",  "name": "Greetings and courtesy words", "sort_order": 1},
        {"code": "LP-ENG-LIS-2.1", "strand_code": "LP-ENG-LIS",  "name": "Listening to short stories", "sort_order": 2},
        {"code": "LP-ENG-LIS-3.1", "strand_code": "LP-ENG-LIS",  "name": "Pronunciation and rhymes", "sort_order": 3},
        {"code": "LP-ENG-READ-1.1", "strand_code": "LP-ENG-READ", "name": "Letter recognition", "sort_order": 1},
        {"code": "LP-ENG-READ-2.1", "strand_code": "LP-ENG-READ", "name": "Reading simple words", "sort_order": 2},
        {"code": "LP-ENG-READ-3.1", "strand_code": "LP-ENG-READ", "name": "Reading short passages and answering questions", "sort_order": 3},
        {"code": "LP-ENG-WRIT-1.1", "strand_code": "LP-ENG-WRIT", "name": "Tracing and copying letters", "sort_order": 1},
        {"code": "LP-ENG-WRIT-2.1", "strand_code": "LP-ENG-WRIT", "name": "Writing simple sentences", "sort_order": 2},
        {"code": "LP-ENG-WRIT-3.1", "strand_code": "LP-ENG-WRIT", "name": "Composing short paragraphs", "sort_order": 3},
        {"code": "LP-ENG-GRAM-1.1", "strand_code": "LP-ENG-GRAM", "name": "Nouns (people, places, things)", "sort_order": 1},
        {"code": "LP-ENG-GRAM-2.1", "strand_code": "LP-ENG-GRAM", "name": "Verbs (action words)", "sort_order": 2},
        {"code": "LP-ENG-GRAM-3.1", "strand_code": "LP-ENG-GRAM", "name": "Punctuation (. ? !)", "sort_order": 3},
        {"code": "LP-KIS-KUS-1.1",  "strand_code": "LP-KIS-KUS",  "name": "Salamu na maneno ya heshima", "sort_order": 1},
        {"code": "LP-KIS-KUS-2.1",  "strand_code": "LP-KIS-KUS",  "name": "Kusikiliza hadithi fupi", "sort_order": 2},
        {"code": "LP-KIS-KUSO-1.1", "strand_code": "LP-KIS-KUSO", "name": "Kutambua herufi", "sort_order": 1},
        {"code": "LP-KIS-KUSO-2.1", "strand_code": "LP-KIS-KUSO", "name": "Kusoma maneno mafupi", "sort_order": 2},
        {"code": "LP-KIS-KUAN-1.1", "strand_code": "LP-KIS-KUAN", "name": "Kunakili herufi", "sort_order": 1},
        {"code": "LP-KIS-KUAN-2.1", "strand_code": "LP-KIS-KUAN", "name": "Kuandika sentensi fupi", "sort_order": 2},
        {"code": "LP-SCI-LIV-2.1", "strand_code": "LP-SCI-LIV", "name": "Parts of a plant", "sort_order": 1},
        {"code": "LP-SCI-LIV-2.2", "strand_code": "LP-SCI-LIV", "name": "Animals around the home", "sort_order": 2},
        {"code": "LP-SCI-ENE-2.1", "strand_code": "LP-SCI-ENE", "name": "Sources of energy (sun, fire, charcoal)", "sort_order": 1},
        {"code": "LP-SCI-EAR-2.1", "strand_code": "LP-SCI-EAR", "name": "Weather and seasons", "sort_order": 1},
        {"code": "LP-SST-HER-2.1", "strand_code": "LP-SST-HER", "name": "My family and community", "sort_order": 1},
        {"code": "LP-SST-CIT-2.1", "strand_code": "LP-SST-CIT", "name": "Rules at home and school", "sort_order": 1},
        {"code": "LP-SST-RES-2.1", "strand_code": "LP-SST-RES", "name": "Goods and services in my county", "sort_order": 1},
        {"code": "LP-AGR-CRP-2.1", "strand_code": "LP-AGR-CRP", "name": "Planting and caring for crops", "sort_order": 1},
        {"code": "LP-AGR-NUT-2.1", "strand_code": "LP-AGR-NUT", "name": "Food groups and balanced diet", "sort_order": 1},
        {"code": "LP-CRE-BIB-2.1", "strand_code": "LP-CRE-BIB", "name": "Stories of creation", "sort_order": 1},
        {"code": "LP-CRE-CRE-2.1", "strand_code": "LP-CRE-CRE", "name": "Love, honesty and respect", "sort_order": 1},
        {"code": "LP-ART-MUS-2.1", "strand_code": "LP-ART-MUS", "name": "Singing Kenyan songs", "sort_order": 1},
        {"code": "LP-ART-ART-2.1", "strand_code": "LP-ART-ART", "name": "Drawing familiar objects", "sort_order": 1},
        {"code": "LP-PE-MOV-1.1",  "strand_code": "LP-PE-MOV",  "name": "Locomotor movements", "sort_order": 1},
        {"code": "LP-PE-HEAL-2.1", "strand_code": "LP-PE-HEAL", "name": "Personal hygiene habits", "sort_order": 1},
        {"code": "JSS-ENG-LIS-1.1",  "strand_code": "JSS-ENG-LIS",  "name": "Listening for gist and detail", "sort_order": 1},
        {"code": "JSS-ENG-READ-1.1", "strand_code": "JSS-ENG-READ", "name": "Reading comprehension", "sort_order": 1},
        {"code": "JSS-ENG-WRIT-1.1", "strand_code": "JSS-ENG-WRIT", "name": "Paragraph writing", "sort_order": 1},
        {"code": "JSS-MATH-NUM-1.1", "strand_code": "JSS-MATH-NUM", "name": "Integers and operations", "sort_order": 1},
        {"code": "JSS-MATH-MEA-1.1", "strand_code": "JSS-MATH-MEA", "name": "Perimeter and area", "sort_order": 1},
        {"code": "JSS-MATH-GEO-1.1", "strand_code": "JSS-MATH-GEO", "name": "Angles and triangles", "sort_order": 1},
        {"code": "JSS-SCI-LIV-1.1", "strand_code": "JSS-SCI-LIV", "name": "Cell structure and function", "sort_order": 1},
        {"code": "JSS-SCI-CHM-1.1", "strand_code": "JSS-SCI-CHM", "name": "States of matter", "sort_order": 1},
        {"code": "JSS-SCI-PHY-1.1", "strand_code": "JSS-SCI-PHY", "name": "Force and motion", "sort_order": 1},
    ],
}


async def upsert_all(db: AsyncSession) -> None:
    la_by_code: dict[str, LearningArea] = {}
    existing_las = (await db.execute(select(LearningArea))).scalars().all()
    for la in existing_las:
        la_by_code[la.code] = la

    for row in CATALOGUE["learning_areas"]:
        if row["code"] in la_by_code:
            continue
        la = LearningArea(
            id=uuid4(),
            code=row["code"],
            name=row["name"],
            level=CurriculumLevel(row["level"]),
            sort_order=row["sort_order"],
        )
        db.add(la)
        la_by_code[row["code"]] = la
    await db.flush()

    strand_by_code: dict[str, Strand] = {}
    existing_ss = (await db.execute(select(Strand))).scalars().all()
    for s in existing_ss:
        strand_by_code[s.code] = s

    for row in CATALOGUE["strands"]:
        if row["code"] in strand_by_code:
            continue
        la = la_by_code[row["learning_area_code"]]
        s = Strand(
            id=uuid4(),
            learning_area_id=la.id,
            code=row["code"],
            name=row["name"],
            sort_order=row["sort_order"],
        )
        db.add(s)
        strand_by_code[row["code"]] = s
    await db.flush()

    existing_subs = (await db.execute(select(SubStrand))).scalars().all()
    have = {s.code for s in existing_subs}
    for row in CATALOGUE["sub_strands"]:
        if row["code"] in have:
            continue
        parent = strand_by_code[row["strand_code"]]
        db.add(
            SubStrand(
                id=uuid4(),
                strand_id=parent.id,
                code=row["code"],
                name=row["name"],
                sort_order=row["sort_order"],
            )
        )
    await db.commit()


async def main() -> None:
    async with SessionLocal() as db:
        await upsert_all(db)
    print("Curriculum seeded.")


if __name__ == "__main__":
    asyncio.run(main())
''')


w("api/tests/__init__.py", "")

w("api/tests/conftest.py", '''"""Pytest fixtures.

For unit tests we use the FastAPI app in-process via httpx. v0.2 will
add a Postgres TestContainer fixture for integration tests.
"""
import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
''')

w("api/tests/test_health.py", '''import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
''')

print("API generator ready.")
