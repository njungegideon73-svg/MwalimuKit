"""Tests for report generation endpoints (PDF + CSV) via async jobs."""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus, JobType
from app.workers.exports import _build_class_summary_csv, _build_report_card_pdf


@pytest.mark.asyncio
async def test_report_card_via_job(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_class, test_assessment, test_learner
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
    assert run_resp.status_code == 200
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

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.routers.jobs.process_export_job.send", lambda *a, **kw: None)

        create_resp = await client.post(
            f"/api/v1/jobs/reports/learner/{test_learner.id}/report-card",
            headers=auth_headers,
            params={"run_id": run_id},
        )
    assert create_resp.status_code == 200
    job_id = create_resp.json()["id"]

    await _complete_job_inline(db_session, UUID(job_id), {
        "learner_id": str(test_learner.id),
        "run_id": str(run_id),
        "school_id": str(test_learner.school_id),
    })

    download_resp = await client.get(
        f"/api/v1/jobs/{job_id}/download",
        headers=auth_headers,
    )
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert len(download_resp.content) > 0


@pytest.mark.asyncio
async def test_report_card_no_scores_returns_400(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_class, test_assessment, test_learner
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
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.routers.jobs.process_export_job.send", lambda *a, **kw: None)

        create_resp = await client.post(
            f"/api/v1/jobs/reports/learner/{test_learner.id}/report-card",
            headers=auth_headers,
            params={"run_id": run_id},
        )
    assert create_resp.status_code == 200
    job_id = create_resp.json()["id"]

    await _complete_job_inline(db_session, UUID(job_id), {
        "learner_id": str(test_learner.id),
        "run_id": str(run_id),
        "school_id": str(test_learner.school_id),
    })

    download_resp = await client.get(
        f"/api/v1/jobs/{job_id}/download",
        headers=auth_headers,
    )
    assert download_resp.status_code == 400


@pytest.mark.asyncio
async def test_summary_csv_via_job(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_class, test_assessment, test_learner
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
    assert run_resp.status_code == 200
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

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.routers.jobs.process_export_job.send", lambda *a, **kw: None)

        create_resp = await client.post(
            f"/api/v1/jobs/reports/class/{test_class.id}/summary-csv",
            headers=auth_headers,
            params={"run_id": run_id},
        )
    assert create_resp.status_code == 200
    job_id = create_resp.json()["id"]

    await _complete_job_inline(db_session, UUID(job_id), {
        "class_id": str(test_class.id),
        "run_id": str(run_id),
        "school_id": str(test_learner.school_id),
    })

    download_resp = await client.get(
        f"/api/v1/jobs/{job_id}/download",
        headers=auth_headers,
    )
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "text/csv; charset=utf-8"
    assert len(download_resp.content) > 0


@pytest.mark.asyncio
async def test_summary_csv_no_learners_returns_400(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user, test_assessment, test_school
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
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.routers.jobs.process_export_job.send", lambda *a, **kw: None)

        create_resp = await client.post(
            f"/api/v1/jobs/reports/class/{empty_class.id}/summary-csv",
            headers=auth_headers,
            params={"run_id": run_id},
        )
    assert create_resp.status_code == 200
    job_id = create_resp.json()["id"]

    await _complete_job_inline(db_session, UUID(job_id), {
        "class_id": str(empty_class.id),
        "run_id": str(run_id),
        "school_id": str(test_school.id),
    })

    download_resp = await client.get(
        f"/api/v1/jobs/{job_id}/download",
        headers=auth_headers,
    )
    assert download_resp.status_code == 400


async def _complete_job_inline(session: AsyncSession, job_id: UUID, payload: dict) -> None:
    job = await session.get(Job, job_id)
    if job is None:
        return

    try:
        if job.type == JobType.report_card_pdf:
            data, result = await _build_report_card_pdf(session, payload)
        elif job.type == JobType.class_summary_csv:
            data, result = await _build_class_summary_csv(session, payload)
        else:
            return
    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
        await session.commit()
        return

    job.status = JobStatus.completed
    job.result = result
    job.file_data = data
    await session.commit()
