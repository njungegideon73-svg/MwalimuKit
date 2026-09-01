"""Tests for the Schemes of Work content-bank + scheduling engine."""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.schemes_of_work import LessonContent
from app.services.schemes_of_work import (
    ContentBlock,
    Interruption,
    _as_str_list,
    schedule_lessons,
)


def _sample_blocks() -> list[ContentBlock]:
    return [
        ContentBlock(
            id=None,
            topic="Counting 0 to 20",
            learning_outcomes=["Count objects up to 20", "Match numbers to quantities"],
            learning_experiences=["Learners count bottle tops in groups"],
            key_inquiry_questions=["How many bottle tops do we have?"],
            resources=['Mentor Mathematics Grade 1 pg. 12'],
            assessment_methods=["Observation checklist", "Oral questions"],
        ),
        ContentBlock(
            id=None,
            topic="Place value 0 to 20",
            learning_outcomes=["Identify tens and ones"],
            learning_experiences=["Learners group sticks into bundles of ten"],
            key_inquiry_questions=["What is the value of 1 in 14?"],
            resources=['Mentor Mathematics Grade 1 pg. 15'],
            assessment_methods=["Pencil-and-paper task"],
        ),
    ]


def test_as_str_list_handles_strings_dicts_and_none() -> None:
    raw = [
        "KLB Visionary Mathematics pg. 45",
        {"title": "Mentor Mathematics", "cite": "pg. 20"},
        None,
        {"other": "ignored"},
    ]
    result = _as_str_list(raw)
    assert "KLB Visionary Mathematics pg. 45" in result
    assert "Mentor Mathematics — pg. 20" in result
    assert _as_str_list(None) == []
    assert _as_str_list([]) == []


def test_schedule_walks_content_in_sequence() -> None:
    blocks = _sample_blocks()

    # 1 week x 2 lessons -> both unique blocks used in order
    lessons = schedule_lessons(blocks, total_weeks=1, lessons_per_week=2, interruptions=[])
    assert len(lessons) == 2
    assert lessons[0].content.topic == "Counting 0 to 20"
    assert lessons[1].content.topic == "Place value 0 to 20"
    assert lessons[0].lesson_sequence == 1
    assert lessons[1].lesson_sequence == 2


def test_schedule_stretches_last_block_when_slots_exceed_content() -> None:
    blocks = _sample_blocks()

    # 2 weeks x 2 lessons = 4 slots but only 2 unique blocks
    lessons = schedule_lessons(blocks, total_weeks=2, lessons_per_week=2, interruptions=[])
    topics = [l.content.topic for l in lessons]
    assert topics[:2] == ["Counting 0 to 20", "Place value 0 to 20"]
    # The final block is reused verbatim rather than rewritten.
    assert topics[2] == "Place value 0 to 20"
    assert topics[3] == "Place value 0 to 20"
    assert lessons[2].content.learning_outcomes == lessons[1].content.learning_outcomes


def test_schedule_inserts_break_rows_at_their_week() -> None:
    blocks = _sample_blocks()
    interruptions = [
        Interruption(week_number=2, type="mid_term_break", label="Mid-Term Break"),
    ]
    lessons = schedule_lessons(blocks, total_weeks=3, lessons_per_week=2, interruptions=interruptions)

    week2 = [l for l in lessons if l.week_number == 2]
    assert len(week2) == 1
    assert week2[0].is_break is True
    assert week2[0].break_label == "Mid-Term Break"

    week1 = [l for l in lessons if l.week_number == 1]
    week3 = [l for l in lessons if l.week_number == 3]
    assert len(week1) == 2 and len(week3) == 2
    assert all(not l.is_break for l in week1 + week3)
    assert week1[0].lesson_sequence == 1


def test_schedule_with_empty_content_bank_is_safe() -> None:
    lessons = schedule_lessons([], total_weeks=1, lessons_per_week=2, interruptions=[])
    assert len(lessons) == 2
    assert lessons[0].content is not None
    assert lessons[0].content.topic == ""


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------

_DEFAULT_CREATE = {
    "name": "Grade 1 Mathematics — Numbers (Term 1)",
    "sub_strand_code": "LP-MATH-NUM-1.1",
    "grade": "Grade 1",
    "learning_area_code": "LP-MATH",
    "academic_year": "2026",
    "term_number": 1,
    "lessons_per_week": 3,
    "total_weeks": 3,
}


async def _seed_content(db) -> LessonContent:
    row = LessonContent(
        id=uuid4(),
        sub_strand_code="LP-MATH-NUM-1.1",
        term_number=1,
        sequence_order=1,
        topic="Counting 0 to 20",
        learning_outcomes=["Count objects up to 20"],
        learning_experiences=["Learners count bottle tops in groups"],
        key_inquiry_questions=["How many bottle tops do we have?"],
        resources=["Mentor Mathematics Grade 1 pg. 12"],
        assessment_methods=["Observation checklist"],
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@pytest.mark.asyncio
async def test_create_scheme_generates_lessons(
    client, auth_headers, db_session, test_sub_strand, test_learning_area
) -> None:
    await _seed_content(db_session)

    res = await client.post(
        "/api/v1/schemes",
        headers=auth_headers,
        json={
            **_DEFAULT_CREATE,
            "calendar_interruptions": [
                {"week_number": 2, "interruption_type": "exam_week", "label": "End of Term Assessment"}
            ],
        },
    )
    assert res.status_code == 201, res.text
    scheme = res.json()
    assert scheme["total_weeks"] == 3

    detail = await client.get(f"/api/v1/schemes/{scheme['id']}", headers=auth_headers)
    assert detail.status_code == 200
    lessons = detail.json()["lessons"]

    # 3 weeks x 3 lessons minus the exam week = 6 lessons + 1 break row
    assert len(lessons) == 7
    break_rows = [l for l in lessons if l["is_break"]]
    assert len(break_rows) == 1
    assert break_rows[0]["week_number"] == 2
    assert break_rows[0]["break_label"] == "End of Term Assessment"

    regular = [l for l in lessons if not l["is_break"]]
    assert all(l["topic"] == "Counting 0 to 20" for l in regular)
    assert regular[0]["learning_outcomes"] == ["Count objects up to 20"]


@pytest.mark.asyncio
async def test_preview_mirrors_schedule(client, auth_headers, db_session) -> None:
    await _seed_content(db_session)
    res = await client.post("/api/v1/schemes", headers=auth_headers, json=_DEFAULT_CREATE)
    scheme_id = res.json()["id"]

    preview = await client.get(f"/api/v1/schemes/{scheme_id}/preview", headers=auth_headers)
    assert preview.status_code == 200
    payload = preview.json()
    assert payload["scheme"]["id"] == scheme_id
    # 3 weeks x 3 = 9 slots, one content block stretched across all
    assert len(payload["lessons"]) == 9
    assert all(not l["is_break"] for l in payload["lessons"])


@pytest.mark.asyncio
async def test_update_lesson_cell_persists_teacher_edits(
    client, auth_headers, db_session
) -> None:
    await _seed_content(db_session)
    scheme_id = (
        await client.post("/api/v1/schemes", headers=auth_headers, json=_DEFAULT_CREATE)
    ).json()["id"]

    res = await client.patch(
        f"/api/v1/schemes/{scheme_id}/lessons/W1-L2",
        headers=auth_headers,
        json={"topic": "Edited topic", "notes": "Skipped due to assembly"},
    )
    assert res.status_code == 200

    detail = await client.get(f"/api/v1/schemes/{scheme_id}", headers=auth_headers)
    lesson = next(l for l in detail.json()["lessons"] if l["week_number"] == 1 and l["lesson_number"] == 2)
    assert lesson["topic"] == "Edited topic"
    assert lesson["notes"] == "Skipped due to assembly"


@pytest.mark.asyncio
async def test_preview_overlays_saved_notes_and_edits(
    client, auth_headers, db_session
) -> None:
    """The preview endpoint should reflect teacher edits and notes."""
    await _seed_content(db_session)
    scheme_id = (
        await client.post("/api/v1/schemes", headers=auth_headers, json=_DEFAULT_CREATE)
    ).json()["id"]

    await client.patch(
        f"/api/v1/schemes/{scheme_id}/lessons/W1-L2",
        headers=auth_headers,
        json={
            "topic": "Adjusted topic",
            "learning_outcomes": ["Outcome A", "Outcome B"],
            "notes": "Rescheduled assembly",
        },
    )

    preview = await client.get(f"/api/v1/schemes/{scheme_id}/preview", headers=auth_headers)
    assert preview.status_code == 200
    lesson = next(
        l
        for l in preview.json()["lessons"]
        if l["week_number"] == 1 and l["lesson_number"] == 2
    )
    assert lesson["topic"] == "Adjusted topic"
    assert lesson["learning_outcomes"] == ["Outcome A", "Outcome B"]
    assert lesson["notes"] == "Rescheduled assembly"


@pytest.mark.asyncio
async def test_generate_with_empty_content_bank_returns_404(
    client, auth_headers, db_session
) -> None:
    res = await client.post("/api/v1/schemes", headers=auth_headers, json=_DEFAULT_CREATE)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_scheme_scoped_to_school(
    client, auth_headers, db_session, test_school
) -> None:
    from app.core.security import create_access_token
    from app.models.school import School
    from app.models.user import User, UserRole

    await _seed_content(db_session)
    res = await client.post("/api/v1/schemes", headers=auth_headers, json=_DEFAULT_CREATE)
    scheme_id = res.json()["id"]

    other_school = School(
        id=uuid4(), name="Other School", code="OTHER01", county="Mombasa", level="primary", settings={}
    )
    db_session.add(other_school)
    await db_session.commit()
    other_admin = User(
        id=uuid4(),
        school_id=other_school.id,
        email="other@test.com",
        full_name="Other Admin",
        role=UserRole.school_admin,
        password_hash="x",
        is_active=True,
    )
    db_session.add(other_admin)
    await db_session.commit()

    other_headers = {"Authorization": f"Bearer {create_access_token(str(other_admin.id))}"}
    other = await client.get(f"/api/v1/schemes/{scheme_id}", headers=other_headers)
    assert other.status_code == 404


@pytest.mark.asyncio
async def test_lesson_content_crud_requires_school_admin(
    client, db_session, admin_auth_headers
) -> None:
    res = await client.post(
        "/api/v1/schemes/content",
        headers=admin_auth_headers,
        json={
            "sub_strand_code": "LP-MATH-NUM-1.1",
            "term_number": 2,
            "sequence_order": 1,
            "topic": "Addition within 20",
            "learning_outcomes": ["Add two single-digit numbers"],
            "learning_experiences": ["Learners combine bottle tops and count"],
            "key_inquiry_questions": ["How many in all?"],
            "resources": ["Mentor Mathematics Grade 1 pg. 30"],
            "assessment_methods": ["Observation"],
        },
    )
    assert res.status_code == 201, res.text
    content_id = res.json()["id"]

    listing = await client.get("/api/v1/schemes/content/LP-MATH-NUM-1.1", headers=admin_auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    delete_res = await client.delete(
        f"/api/v1/schemes/content/{content_id}", headers=admin_auth_headers
    )
    assert delete_res.status_code == 204


@pytest.mark.asyncio
async def test_content_create_denied_for_teacher(client, auth_headers) -> None:
    res = await client.post(
        "/api/v1/schemes/content",
        headers=auth_headers,
        json={
            "sub_strand_code": "LP-MATH-NUM-1.1",
            "term_number": 1,
            "sequence_order": 1,
            "topic": "x",
        },
    )
    assert res.status_code == 403