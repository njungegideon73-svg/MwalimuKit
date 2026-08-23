"""Report generation endpoints (PDF + CSV)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser
from app.models.assessment import Assessment
from app.models.run import AssessmentRun
from app.models.school_class import SchoolClass

router = APIRouter()


async def _load_run(
    db: AsyncSession, user: CurrentUser, run_id: UUID
) -> tuple[AssessmentRun, Assessment, SchoolClass]:
    run = (
        await db.execute(
            select(AssessmentRun).where(
                AssessmentRun.id == run_id,
                AssessmentRun.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    assessment = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == run.assessment_id,
                Assessment.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    school_class = (
        await db.execute(
            select(SchoolClass).where(
                SchoolClass.id == run.class_id,
                SchoolClass.school_id == user.school_id,
            )
        )
    ).scalar_one_or_none()
    if school_class is None:
        raise HTTPException(status_code=404, detail="Class not found")

    return run, assessment, school_class


# Export endpoints moved to app.routers.jobs for async processing.
# Use:
#   POST /api/v1/jobs/reports/learner/{learner_id}/report-card
#   POST /api/v1/jobs/reports/report-card/{learner_id}
#   POST /api/v1/jobs/reports/class/{class_id}/summary-csv
# Then GET /api/v1/jobs/{job_id}/download
