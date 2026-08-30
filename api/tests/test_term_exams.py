"""Term exam endpoint tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_term_exam_as_school_admin(client: AsyncClient, admin_auth_headers: dict, test_class, test_learning_area):
    resp = await client.post(
        "/api/v1/term-exams",
        json={
            "school_id": str(test_class.school_id),
            "class_id": str(test_class.id),
            "learning_area_id": str(test_learning_area.id),
            "term": 1,
            "exam_type": "opener",
            "academic_year": "2025",
            "max_marks": 100,
        },
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["class_id"] == str(test_class.id)
    assert data["learning_area_id"] == str(test_learning_area.id)
    assert data["term"] == 1
    assert data["exam_type"] == "opener"


@pytest.mark.asyncio
async def test_create_term_exam_as_teacher(client: AsyncClient, auth_headers: dict, test_class, test_learning_area):
    resp = await client.post(
        "/api/v1/term-exams",
        json={
            "class_id": str(test_class.id),
            "learning_area_id": str(test_learning_area.id),
            "term": 1,
            "exam_type": "opener",
            "academic_year": "2025",
            "max_marks": 100,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
