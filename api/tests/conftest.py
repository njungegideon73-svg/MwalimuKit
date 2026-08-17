"""Shared test fixtures using SQLite in-memory database."""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, hash_password
from app.models.base import Base
from app.models.school import School
from app.models.user import User, UserRole
from app.models.curriculum import LearningArea, Strand, SubStrand, CurriculumLevel
from app.models.assessment import Assessment, AssessmentSource
from app.models.school_class import SchoolClass
from app.models.learner import Learner
from app.models.run import AssessmentRun
from app.models.score import Score
from app.main import app
from app.core.db import get_db


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DB_URL, future=True)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_school(db_session: AsyncSession) -> School:
    school = School(
        id=uuid4(),
        name="Test School",
        code="TEST01",
        county="Nairobi",
        level="primary",
        settings={},
    )
    db_session.add(school)
    await db_session.commit()
    await db_session.refresh(school)
    return school


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_school: School) -> User:
    user = User(
        id=uuid4(),
        school_id=test_school.id,
        email="teacher@test.com",
        full_name="Test Teacher",
        role=UserRole.teacher,
        password_hash=hash_password("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_learning_area(db_session: AsyncSession) -> LearningArea:
    la = LearningArea(
        id=uuid4(),
        code="LP-MATH",
        name="Mathematics",
        level=CurriculumLevel.lower_primary,
        sort_order=1,
    )
    db_session.add(la)
    await db_session.commit()
    await db_session.refresh(la)
    return la


@pytest_asyncio.fixture
async def test_strand(db_session: AsyncSession, test_learning_area: LearningArea) -> Strand:
    s = Strand(
        id=uuid4(),
        learning_area_id=test_learning_area.id,
        code="LP-MATH-NUM",
        name="Numbers",
        sort_order=1,
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest_asyncio.fixture
async def test_sub_strand(db_session: AsyncSession, test_strand: Strand) -> SubStrand:
    ss = SubStrand(
        id=uuid4(),
        strand_id=test_strand.id,
        code="LP-MATH-NUM-1.1",
        name="Counting 0 to 20",
        sort_order=1,
    )
    db_session.add(ss)
    await db_session.commit()
    await db_session.refresh(ss)
    return ss


@pytest_asyncio.fixture
async def test_assessment(
    db_session: AsyncSession, test_user: User, test_school: School, test_learning_area: LearningArea
) -> Assessment:
    a = Assessment(
        id=uuid4(),
        owner_id=test_user.id,
        school_id=test_school.id,
        learning_area_id=test_learning_area.id,
        name="Test Assessment",
        description="A test",
        strand_code="LP-MATH-NUM",
        sub_strand_codes=["LP-MATH-NUM-1.1"],
        source=AssessmentSource.manual,
        rubric={"levels": [], "criteria": []},
        items=[{"id": "itm_01", "criterion": "accuracy", "stem": "Count to 5", "answer_guide": "5", "max_level": 4}],
        tags=[],
        is_favourite=False,
    )
    db_session.add(a)
    await db_session.commit()
    await db_session.refresh(a)
    return a


@pytest_asyncio.fixture
async def test_class(
    db_session: AsyncSession, test_user: User, test_school: School
) -> SchoolClass:
    c = SchoolClass(
        id=uuid4(),
        school_id=test_school.id,
        teacher_id=test_user.id,
        name="Grade 1 Blue",
        grade_level="Grade 1",
        learning_area_ids=[],
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


@pytest_asyncio.fixture
async def test_learner(db_session: AsyncSession, test_class: SchoolClass, test_school: School) -> Learner:
    l = Learner(
        id=uuid4(),
        school_id=test_school.id,
        class_id=test_class.id,
        full_name="Achieng Omondi",
        admission_no="ADM001",
        gender="F",
    )
    db_session.add(l)
    await db_session.commit()
    await db_session.refresh(l)
    return l


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_user: User) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
