"""Tests for v0.2 backend additions: PATCH assessment, favourite toggle,
change password, change school code."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── PATCH /assessments/{id} ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_assessment_name(client: AsyncClient, auth_headers: dict, test_assessment):
    resp = await client.patch(
        f"/api/v1/assessments/{test_assessment.id}",
        json={"name": "Updated Assessment"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Assessment"
    assert data["id"] == str(test_assessment.id)


@pytest.mark.asyncio
async def test_patch_assessment_rubric(client: AsyncClient, auth_headers: dict, test_assessment):
    new_rubric = {
        "levels": [
            {"level": 1, "label": "Beginning", "descriptor": "Needs support"},
            {"level": 2, "label": "Developing", "descriptor": "Some understanding"},
            {"level": 3, "label": "Meeting", "descriptor": "Meets expectations"},
            {"level": 4, "label": "Exceeding", "descriptor": "Exceeds expectations"},
        ],
        "criteria": [
            {"id": "crit_1", "label": "Accuracy"}
        ],
    }
    resp = await client.patch(
        f"/api/v1/assessments/{test_assessment.id}",
        json={"rubric": new_rubric},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rubric"]["levels"]) == 4
    assert data["rubric"]["levels"][0]["label"] == "Beginning"


@pytest.mark.asyncio
async def test_patch_assessment_items(client: AsyncClient, auth_headers: dict, test_assessment):
    new_items = [
        {"id": "itm_a", "criterion": "knowledge", "stem": "What is 2+2?", "answer_guide": "4", "max_level": 4},
        {"id": "itm_b", "criterion": "reasoning", "stem": "Explain why", "answer_guide": "Because", "max_level": 3},
    ]
    resp = await client.patch(
        f"/api/v1/assessments/{test_assessment.id}",
        json={"items": new_items},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_patch_assessment_not_found(client: AsyncClient, auth_headers: dict):
    from uuid import uuid4
    resp = await client.patch(
        f"/api/v1/assessments/{uuid4()}",
        json={"name": "Nope"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_assessment_empty_body(client: AsyncClient, auth_headers: dict, test_assessment):
    resp = await client.patch(
        f"/api/v1/assessments/{test_assessment.id}",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 200


# ── POST /assessments/{id}/favourite ────────────────────────────────────

@pytest.mark.asyncio
async def test_toggle_favourite(client: AsyncClient, auth_headers: dict, test_assessment):
    assert test_assessment.is_favourite is False
    resp = await client.post(
        f"/api/v1/assessments/{test_assessment.id}/favourite",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_favourite"] is True

    # Toggle back
    resp2 = await client.post(
        f"/api/v1/assessments/{test_assessment.id}/favourite",
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["is_favourite"] is False


@pytest.mark.asyncio
async def test_toggle_favourite_not_found(client: AsyncClient, auth_headers: dict):
    from uuid import uuid4
    resp = await client.post(
        f"/api/v1/assessments/{uuid4()}/favourite",
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── POST /auth/change-password ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpassword123", "new_password": "newsecure12345"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["changed"] is True


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrongpassword", "new_password": "newsecure12345"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_too_short(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpassword123", "new_password": "short"},
        headers=auth_headers,
    )
    assert resp.status_code in (400, 422)


# ── POST /auth/change-school-code ──────────────────────────────────────

@pytest.mark.asyncio
async def test_change_school_code(client: AsyncClient, auth_headers: dict, test_school):
    resp = await client.post(
        "/api/v1/auth/change-school-code",
        json={"current_password": "testpassword123", "new_school_code": test_school.code},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["changed"] is True


@pytest.mark.asyncio
async def test_change_school_code_nonexistent(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/auth/change-school-code",
        json={"current_password": "testpassword123", "new_school_code": "NONEXISTENT"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
