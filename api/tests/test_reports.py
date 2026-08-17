"""Tests for report generation endpoints (PDF + CSV)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
async def test_report_card_returns_pdf(
    client: AsyncClient, auth_headers: dict, test_class, test_assessment, test_learner
):
    run_resp = await client.post(
        "/api/v1/runs",
        headers=auth_headers,
        json={
            "class_id": str(test_class.id),
            "assessment_id": str(test_assessment.id),
            "term": "Term 1",
        },
    )
    run_id = run_resp.json()["id"]

    score_resp = await client.post(
        "/api/v1/scores/batch",
        headers=auth_headers,
        json={
            "scores": [
                {
                    "id": str(uuid4()),
                    "run_id": run_id,
                    "learner_id": str(test_learner.id),
                    "item_id": "itm_01",
                    "level": 3,
                    "note": None,
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ]
        },
    )
    assert score_resp.status_code == 200

    resp = await client.get(
        f"/api/v1/reports/learner/{test_learner.id}/report-card",
        headers=auth_headers,
        params={"run_id": run_id},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0


@pytest.mark.asyncio
async def test_report_card_no_scores(
    client: AsyncClient, auth_headers: dict, test_class, test_assessment, test_learner
):
    run_resp = await client.post(
        "/api/v1/runs",
        headers=auth_headers,
        json={
            "class_id": str(test_class.id),
            "assessment_id": str(test_assessment.id),
            "term": "Term 1",
        },
    )
    run_id = run_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/reports/learner/{test_learner.id}/report-card",
        headers=auth_headers,
        params={"run_id": run_id},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_summary_csv_returns_csv(
    client: AsyncClient, auth_headers: dict, test_class, test_assessment, test_learner
):
    run_resp = await client.post(
        "/api/v1/runs",
        headers=auth_headers,
        json={
            "class_id": str(test_class.id),
            "assessment_id": str(test_assessment.id),
            "term": "Term 1",
        },
    )
    run_id = run_resp.json()["id"]

    await client.post(
        "/api/v1/scores/batch",
        headers=auth_headers,
        json={
            "scores": [
                {
                    "id": str(uuid4()),
                    "run_id": run_id,
                    "learner_id": str(test_learner.id),
                    "item_id": "itm_01",
                    "level": 3,
                    "note": None,
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ]
        },
    )

    resp = await client.get(
        f"/api/v1/reports/class/{test_class.id}/summary-csv",
        headers=auth_headers,
        params={"run_id": run_id},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/csv; charset=utf-8"
    assert len(resp.content) > 0


@pytest.mark.asyncio
async def test_summary_csv_no_learners(
    client: AsyncClient, auth_headers: dict, test_user, test_assessment, test_school, db_session
):
    from app.models.school_class import SchoolClass

    empty_class = SchoolClass(
        id=uuid4(),
        school_id=test_school.id,
        teacher_id=test_user.id,
        name="Empty Class",
        grade_level="Grade 1",
        learning_area_ids=[],
    )
    db_session.add(empty_class)
    await db_session.commit()
    await db_session.refresh(empty_class)

    run_resp = await client.post(
        "/api/v1/runs",
        headers=auth_headers,
        json={
            "class_id": str(empty_class.id),
            "assessment_id": str(test_assessment.id),
            "term": "Term 1",
        },
    )
    run_id = run_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/reports/class/{empty_class.id}/summary-csv",
        headers=auth_headers,
        params={"run_id": run_id},
    )
    assert resp.status_code == 404
