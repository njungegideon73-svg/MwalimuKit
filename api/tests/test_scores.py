"""Score batch endpoint tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_batch_scores(
    client: AsyncClient, auth_headers: dict, test_class, test_assessment, test_learner
):
    # Create a run first
    run_resp = await client.post(
        "/api/v1/runs",
        json={
            "class_id": str(test_class.id),
            "assessment_id": str(test_assessment.id),
        },
        headers=auth_headers,
    )
    run = run_resp.json()
    run_id = run["id"]

    # Batch scores
    from uuid import uuid4
    resp = await client.post(
        "/api/v1/scores/batch",
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
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] >= 1


@pytest.mark.asyncio
async def test_batch_scores_conflict_detection(
    client: AsyncClient, auth_headers: dict, test_class, test_assessment, test_learner
):
    from uuid import uuid4

    # Create a run
    run_resp = await client.post(
        "/api/v1/runs",
        json={
            "class_id": str(test_class.id),
            "assessment_id": str(test_assessment.id),
        },
        headers=auth_headers,
    )
    run_id = run_resp.json()["id"]
    score_id = uuid4()

    # First write - old timestamp
    await client.post(
        "/api/v1/scores/batch",
        json={
            "scores": [
                {
                    "id": str(score_id),
                    "run_id": run_id,
                    "learner_id": str(test_learner.id),
                    "item_id": "itm_01",
                    "level": 2,
                    "note": None,
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ]
        },
        headers=auth_headers,
    )

    # Second write - even older timestamp (should be a conflict)
    resp = await client.post(
        "/api/v1/scores/batch",
        json={
            "scores": [
                {
                    "id": str(uuid4()),
                    "run_id": run_id,
                    "learner_id": str(test_learner.id),
                    "item_id": "itm_01",
                    "level": 4,
                    "note": None,
                    "updated_at": "2025-12-01T00:00:00Z",
                }
            ]
        },
        headers=auth_headers,
    )
    data = resp.json()
    assert data["conflicts"] >= 1
