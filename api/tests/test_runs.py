"""Tests for the runs router."""
import pytest
from httpx import AsyncClient

from app.models.school_class import SchoolClass
from app.models.assessment import Assessment


@pytest.mark.asyncio
async def test_start_run(client: AsyncClient, auth_headers: dict, test_class: SchoolClass, test_assessment: Assessment):
    resp = await client.post(
        "/api/v1/runs",
        headers=auth_headers,
        json={
            "class_id": str(test_class.id),
            "assessment_id": str(test_assessment.id),
            "term": "Term 1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["class_id"] == str(test_class.id)
    assert data["assessment_id"] == str(test_assessment.id)
    assert data["term"] == "Term 1"
    assert data["closed_at"] is None
    assert "id" in data


@pytest.mark.asyncio
async def test_start_run_missing_class(client: AsyncClient, auth_headers: dict, test_assessment: Assessment):
    from uuid import uuid4
    resp = await client.post(
        "/api/v1/runs",
        headers=auth_headers,
        json={
            "class_id": str(uuid4()),
            "assessment_id": str(test_assessment.id),
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_runs(client: AsyncClient, auth_headers: dict, test_class: SchoolClass, test_assessment: Assessment):
    # Create a run first
    await client.post(
        "/api/v1/runs",
        headers=auth_headers,
        json={"class_id": str(test_class.id), "assessment_id": str(test_assessment.id)},
    )
    resp = await client.get("/api/v1/runs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_run(client: AsyncClient, auth_headers: dict, test_class: SchoolClass, test_assessment: Assessment):
    create_resp = await client.post(
        "/api/v1/runs",
        headers=auth_headers,
        json={"class_id": str(test_class.id), "assessment_id": str(test_assessment.id)},
    )
    run_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/runs/{run_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


@pytest.mark.asyncio
async def test_close_run(client: AsyncClient, auth_headers: dict, test_class: SchoolClass, test_assessment: Assessment):
    create_resp = await client.post(
        "/api/v1/runs",
        headers=auth_headers,
        json={"class_id": str(test_class.id), "assessment_id": str(test_assessment.id)},
    )
    run_id = create_resp.json()["id"]
    resp = await client.post(f"/api/v1/runs/{run_id}/close", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["closed_at"] is not None


@pytest.mark.asyncio
async def test_close_run_already_closed(client: AsyncClient, auth_headers: dict, test_class: SchoolClass, test_assessment: Assessment):
    create_resp = await client.post(
        "/api/v1/runs",
        headers=auth_headers,
        json={"class_id": str(test_class.id), "assessment_id": str(test_assessment.id)},
    )
    run_id = create_resp.json()["id"]
    await client.post(f"/api/v1/runs/{run_id}/close", headers=auth_headers)
    resp = await client.post(f"/api/v1/runs/{run_id}/close", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_run_not_found(client: AsyncClient, auth_headers: dict):
    from uuid import uuid4
    resp = await client.get(f"/api/v1/runs/{uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
