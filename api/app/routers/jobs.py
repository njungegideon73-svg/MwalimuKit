"""Job management endpoints."""
from __future__ import annotations

import hashlib
import io
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.assessment import Assessment
from app.models.job import Job, JobType
from app.models.run import AssessmentRun
from app.models.school_class import SchoolClass
from app.schemas.job import JobOut
from app.workers.exports import process_export_job

router = APIRouter()


def _idempotency_key(request: Request, payload: dict) -> str:
    key = request.headers.get("x-idempotency-key")
    if key:
        return key
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


async def _enqueue_job(
    db: AsyncSession,
    user: CurrentUser,
    job_type: JobType,
    payload: dict,
    idempotency_key: str,
) -> Job:
    existing = (
        await db.execute(
            select(Job).where(Job.idempotency_key == idempotency_key, Job.school_id == user.school_id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    job = Job(
        user_id=user.id,
        school_id=user.school_id,
        type=job_type,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    process_export_job.send(str(job.id))
    return job


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> JobOut:
    job = (
        await db.execute(
            select(Job).where(Job.id == job_id, Job.school_id == user.school_id)
        )
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)


@router.get("/{job_id}/download")
async def download_job_result(job_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    job = (
        await db.execute(
            select(Job).where(Job.id == job_id, Job.school_id == user.school_id)
        )
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.result or not job.file_data:
        raise HTTPException(status_code=400, detail="Job result is not ready")

    filename = job.result.get("filename", "export")
    content_type = job.result.get("content_type", "application/octet-stream")
    return StreamingResponse(
        io.BytesIO(job.file_data),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@router.post("/assessments/{assessment_id}/export/pdf")
async def create_assessment_pdf_job(
    assessment_id: UUID,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    mode: str = Query(default="questions"),
):
    if mode not in ("questions", "answer-key"):
        raise HTTPException(status_code=400, detail="Invalid export mode. Use 'questions' or 'answer-key'.")

    assessment = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    payload = {"assessment_id": str(assessment_id), "school_id": str(user.school_id), "mode": mode}
    idem_key = _idempotency_key(request, payload)
    job = await _enqueue_job(db, user, JobType.assessment_pdf, payload, idem_key)
    return JobOut.model_validate(job)


@router.post("/assessments/{assessment_id}/export/docx")
async def create_assessment_docx_job(
    assessment_id: UUID,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    mode: str = Query(default="questions"),
):
    if mode not in ("questions", "answer-key"):
        raise HTTPException(status_code=400, detail="Invalid export mode. Use 'questions' or 'answer-key'.")

    assessment = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    payload = {"assessment_id": str(assessment_id), "school_id": str(user.school_id), "mode": mode}
    idem_key = _idempotency_key(request, payload)
    job = await _enqueue_job(db, user, JobType.assessment_docx, payload, idem_key)
    return JobOut.model_validate(job)


@router.post("/reports/learner/{learner_id}/report-card")
async def create_report_card_job(
    learner_id: UUID,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    run_id: UUID = Query(...),
):
    from app.models.learner import Learner

    learner = (
        await db.execute(
            select(Learner).where(
                Learner.id == learner_id,
                Learner.school_id == user.school_id,
                Learner.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if learner is None:
        raise HTTPException(status_code=404, detail="Learner not found")

    run = (
        await db.execute(
            select(AssessmentRun).where(AssessmentRun.id == run_id, AssessmentRun.school_id == user.school_id)
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    payload = {"learner_id": str(learner_id), "run_id": str(run_id), "school_id": str(user.school_id)}
    idem_key = _idempotency_key(request, payload)
    job = await _enqueue_job(db, user, JobType.report_card_pdf, payload, idem_key)
    return JobOut.model_validate(job)


@router.post("/reports/report-card/{learner_id}")
async def create_sba_report_card_job(
    learner_id: UUID,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    academic_year: str = Query(...),
):
    from app.models.learner import Learner

    learner = (
        await db.execute(
            select(Learner).where(
                Learner.id == learner_id,
                Learner.school_id == user.school_id,
                Learner.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if learner is None:
        raise HTTPException(status_code=404, detail="Learner not found")

    payload = {"learner_id": str(learner_id), "academic_year": academic_year, "school_id": str(user.school_id)}
    idem_key = _idempotency_key(request, payload)
    job = await _enqueue_job(db, user, JobType.sba_report_card_pdf, payload, idem_key)
    return JobOut.model_validate(job)


@router.post("/reports/class/{class_id}/summary-csv")
async def create_class_summary_csv_job(
    class_id: UUID,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    run_id: UUID = Query(...),
):
    school_class = (
        await db.execute(
            select(SchoolClass).where(SchoolClass.id == class_id, SchoolClass.school_id == user.school_id)
        )
    ).scalar_one_or_none()
    if school_class is None:
        raise HTTPException(status_code=404, detail="Class not found")

    payload = {"class_id": str(class_id), "run_id": str(run_id), "school_id": str(user.school_id)}
    idem_key = _idempotency_key(request, payload)
    job = await _enqueue_job(db, user, JobType.class_summary_csv, payload, idem_key)
    return JobOut.model_validate(job)


@router.post("/term-exams/export/class/{class_id}/csv")
async def create_term_exam_csv_job(
    class_id: UUID,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    academic_year: str = Query(...),
):
    school_class = (
        await db.execute(
            select(SchoolClass).where(SchoolClass.id == class_id, SchoolClass.school_id == user.school_id)
        )
    ).scalar_one_or_none()
    if school_class is None:
        raise HTTPException(status_code=404, detail="Class not found")

    payload = {"class_id": str(class_id), "academic_year": academic_year, "school_id": str(user.school_id)}
    idem_key = _idempotency_key(request, payload)
    job = await _enqueue_job(db, user, JobType.term_exam_class_csv, payload, idem_key)
    return JobOut.model_validate(job)
