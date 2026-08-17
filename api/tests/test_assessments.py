"""Assessment endpoint tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_assessment(
    client: AsyncClient, auth_headers: dict, test_learning_area, test_strand, test_sub_strand
):
    resp = await client.post(
        "/api/v1/assessments",
        json={
            "name": "Counting Test",
            "description": "A test assessment",
            "learning_area_code": test_learning_area.code,
            "strand_code": test_strand.code,
            "sub_strand_codes": [test_sub_strand.code],
            "source": "manual",
            "rubric": {"levels": [], "criteria": []},
            "items": [
                {"id": "itm_01", "criterion": "accuracy", "stem": "Count to 5", "answer_guide": "5", "max_level": 4}
            ],
            "tags": [],
            "is_favourite": False,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Counting Test"


@pytest.mark.asyncio
async def test_list_assessments(client: AsyncClient, auth_headers: dict, test_assessment):
    resp = await client.get("/api/v1/assessments", headers=auth_headers)
    assert resp.status_code == 200
    assessments = resp.json()
    assert len(assessments) >= 1


@pytest.mark.asyncio
async def test_get_assessment(client: AsyncClient, auth_headers: dict, test_assessment):
    resp = await client.get(
        f"/api/v1/assessments/{test_assessment.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Assessment"


@pytest.mark.asyncio
async def test_duplicate_assessment(client: AsyncClient, auth_headers: dict, test_assessment):
    resp = await client.post(
        f"/api/v1/assessments/{test_assessment.id}/duplicate", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Assessment (copy)"
    assert data["id"] != str(test_assessment.id)


@pytest.mark.asyncio
async def test_delete_assessment(client: AsyncClient, auth_headers: dict, test_assessment):
    resp = await client.delete(
        f"/api/v1/assessments/{test_assessment.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Should not appear in list after soft delete
    list_resp = await client.get("/api/v1/assessments", headers=auth_headers)
    assessments = list_resp.json()
    assert not any(a["id"] == str(test_assessment.id) for a in assessments)


@pytest.mark.asyncio
async def test_generate_mock_assessment(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/assessments/generate",
        json={
            "learning_area_code": "LP-MATH",
            "strand_code": "LP-MATH-NUM",
            "sub_strand_codes": ["LP-MATH-NUM-1.1"],
            "grade_level": "Grade 1",
            "item_count": 3,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "rubric" in data
    assert len(data["items"]) == 3
