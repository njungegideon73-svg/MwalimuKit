"""Term exams – SBA management, marks entry, report cards, analytics."""
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.curriculum import LearningArea
from app.models.learner import Learner
from app.models.learner_exam_score import LearnerExamScore
from app.models.school_class import SchoolClass
from app.models.term_exam import TermExam
from app.models.user import UserRole
from app.schemas.term_exam import (
    ClassAnalytics,
    LearnerReportCard,
    LearnerScoreOut,
    MarksEntryPayload,
    SubjectReport,
    TermExamIn,
    TermExamOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXAM_TYPE_LABELS = {"opener": "Opener", "midterm": "Midterm", "endterm": "End Term"}


def _compute_grade(marks: int, max_marks: int) -> str:
    pct = (marks / max_marks) * 100 if max_marks > 0 else 0
    if pct >= 80:
        return "A"
    elif pct >= 70:
        return "B"
    elif pct >= 60:
        return "C"
    elif pct >= 50:
        return "D"
    elif pct >= 40:
        return "E"
    else:
        return "F"


async def _resolve_class(db: AsyncSession, user, class_id: UUID) -> SchoolClass:
    user_role = user.role if hasattr(user.role, "value") else str(user.role)
    if user_role in (UserRole.school_admin.value, UserRole.super_admin.value):
        cls = (
            await db.execute(
                select(SchoolClass).where(
                    SchoolClass.id == class_id, SchoolClass.school_id == user.school_id
                )
            )
        ).scalar_one_or_none()
    else:
        cls = (
            await db.execute(
                select(SchoolClass).where(
                    SchoolClass.id == class_id, SchoolClass.teacher_id == user.id
                )
            )
        ).scalar_one_or_none()
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return cls


# ---------------------------------------------------------------------------
# 1. Term Exam CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[TermExamOut])
async def list_term_exams(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    class_id: str | None = None,
    term: int | None = None,
    academic_year: str | None = None,
) -> list[TermExamOut]:
    stmt = select(TermExam).where(TermExam.school_id == user.school_id)
    if class_id:
        stmt = stmt.where(TermExam.class_id == UUID(class_id))
    if term:
        stmt = stmt.where(TermExam.term == term)
    if academic_year:
        stmt = stmt.where(TermExam.academic_year == academic_year)
    stmt = stmt.order_by(TermExam.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()

    result = []
    for r in rows:
        cls_row = (await db.execute(
            select(SchoolClass).where(SchoolClass.id == r.class_id)
        )).scalar_one_or_none()
        la_row = (await db.execute(
            select(LearningArea).where(LearningArea.id == r.learning_area_id)
        )).scalar_one_or_none()
        result.append(TermExamOut(
            id=str(r.id),
            school_id=str(r.school_id),
            class_id=str(r.class_id),
            class_name=cls_row.name if cls_row else "",
            learning_area_id=str(r.learning_area_id),
            learning_area_name=la_row.name if la_row else "",
            term=r.term,
            exam_type=r.exam_type,
            academic_year=r.academic_year,
            max_marks=r.max_marks,
            created_at=r.created_at.isoformat(),
        ))
    return result


@router.post("", response_model=TermExamOut)
async def create_term_exam(
    payload: TermExamIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TermExamOut:
    await _resolve_class(db, user, UUID(payload.class_id))

    la = (await db.execute(
        select(LearningArea).where(LearningArea.id == UUID(payload.learning_area_id))
    )).scalar_one_or_none()
    if la is None:
        raise HTTPException(status_code=404, detail="Learning area not found")

    te = TermExam(
        id=uuid4(),
        school_id=user.school_id,
        class_id=UUID(payload.class_id),
        learning_area_id=UUID(payload.learning_area_id),
        term=payload.term,
        exam_type=payload.exam_type,
        academic_year=payload.academic_year,
        max_marks=payload.max_marks,
    )
    db.add(te)
    await db.commit()
    await db.refresh(te)

    cls_row = (await db.execute(
        select(SchoolClass).where(SchoolClass.id == te.class_id)
    )).scalar_one_or_none()

    return TermExamOut(
        id=str(te.id),
        school_id=str(te.school_id),
        class_id=str(te.class_id),
        class_name=cls_row.name if cls_row else "",
        learning_area_id=str(te.learning_area_id),
        learning_area_name=la.name,
        term=te.term,
        exam_type=te.exam_type,
        academic_year=te.academic_year,
        max_marks=te.max_marks,
        created_at=te.created_at.isoformat(),
    )


@router.get("/{exam_id}", response_model=TermExamOut)
async def get_term_exam(
    exam_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TermExamOut:
    te = (await db.execute(
        select(TermExam).where(TermExam.id == exam_id, TermExam.school_id == user.school_id)
    )).scalar_one_or_none()
    if te is None:
        raise HTTPException(status_code=404, detail="Term exam not found")

    cls_row = (await db.execute(
        select(SchoolClass).where(SchoolClass.id == te.class_id)
    )).scalar_one_or_none()
    la_row = (await db.execute(
        select(LearningArea).where(LearningArea.id == te.learning_area_id)
    )).scalar_one_or_none()

    return TermExamOut(
        id=str(te.id),
        school_id=str(te.school_id),
        class_id=str(te.class_id),
        class_name=cls_row.name if cls_row else "",
        learning_area_id=str(te.learning_area_id),
        learning_area_name=la_row.name if la_row else "",
        term=te.term,
        exam_type=te.exam_type,
        academic_year=te.academic_year,
        max_marks=te.max_marks,
        created_at=te.created_at.isoformat(),
    )


@router.delete("/{exam_id}")
async def delete_term_exam(
    exam_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    te = (await db.execute(
        select(TermExam).where(TermExam.id == exam_id, TermExam.school_id == user.school_id)
    )).scalar_one_or_none()
    if te is None:
        raise HTTPException(status_code=404, detail="Term exam not found")

    # Delete associated scores first
    await db.execute(
        select(LearnerExamScore).where(LearnerExamScore.term_exam_id == exam_id)
    )
    from sqlalchemy import delete as sa_delete
    await db.execute(
        sa_delete(LearnerExamScore).where(LearnerExamScore.term_exam_id == exam_id)
    )
    await db.delete(te)
    await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 2. Marks Entry (batch upsert)
# ---------------------------------------------------------------------------

@router.get("/{exam_id}/scores", response_model=list[LearnerScoreOut])
async def list_exam_scores(
    exam_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[LearnerScoreOut]:
    te = (await db.execute(
        select(TermExam).where(TermExam.id == exam_id, TermExam.school_id == user.school_id)
    )).scalar_one_or_none()
    if te is None:
        raise HTTPException(status_code=404, detail="Term exam not found")

    learners = (await db.execute(
        select(Learner).where(
            Learner.class_id == te.class_id,
            Learner.school_id == user.school_id,
            Learner.deleted_at.is_(None),
        ).order_by(Learner.full_name)
    )).scalars().all()

    existing_scores = (await db.execute(
        select(LearnerExamScore).where(LearnerExamScore.term_exam_id == exam_id)
    )).scalars().all()
    score_map = {str(s.learner_id): s for s in existing_scores}

    result = []
    for l in learners:
        s = score_map.get(str(l.id))
        result.append(LearnerScoreOut(
            id=str(s.id) if s else "",
            learner_id=str(l.id),
            learner_name=l.full_name,
            admission_no=l.admission_no,
            marks=s.marks if s else 0,
            grade=s.grade if s else None,
            comment=s.comment if s else None,
        ))
    return result


@router.post("/{exam_id}/scores", response_model=list[LearnerScoreOut])
async def upsert_exam_scores(
    exam_id: UUID,
    payload: MarksEntryPayload,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[LearnerScoreOut]:
    te = (await db.execute(
        select(TermExam).where(TermExam.id == exam_id, TermExam.school_id == user.school_id)
    )).scalar_one_or_none()
    if te is None:
        raise HTTPException(status_code=404, detail="Term exam not found")

    for entry in payload.scores:
        existing = (await db.execute(
            select(LearnerExamScore).where(
                LearnerExamScore.term_exam_id == exam_id,
                LearnerExamScore.learner_id == UUID(entry.learner_id),
            )
        )).scalar_one_or_none()

        grade = entry.grade or _compute_grade(entry.marks, te.max_marks)

        if existing:
            existing.marks = entry.marks
            existing.grade = grade
            existing.comment = entry.comment
        else:
            score = LearnerExamScore(
                id=uuid4(),
                term_exam_id=exam_id,
                learner_id=UUID(entry.learner_id),
                school_id=te.school_id,
                marks=entry.marks,
                grade=grade,
                comment=entry.comment,
            )
            db.add(score)

    await db.commit()

    # Return updated scores
    learners = (await db.execute(
        select(Learner).where(
            Learner.class_id == te.class_id,
            Learner.school_id == user.school_id,
            Learner.deleted_at.is_(None),
        ).order_by(Learner.full_name)
    )).scalars().all()

    all_scores = (await db.execute(
        select(LearnerExamScore).where(LearnerExamScore.term_exam_id == exam_id)
    )).scalars().all()
    score_map = {str(s.learner_id): s for s in all_scores}

    result = []
    for l in learners:
        s = score_map.get(str(l.id))
        result.append(LearnerScoreOut(
            id=str(s.id) if s else "",
            learner_id=str(l.id),
            learner_name=l.full_name,
            admission_no=l.admission_no,
            marks=s.marks if s else 0,
            grade=s.grade if s else None,
            comment=s.comment if s else None,
        ))
    return result


# ---------------------------------------------------------------------------
# 3. Learner Report Card
# ---------------------------------------------------------------------------

@router.get("/report-card/learner/{learner_id}")
async def learner_sba_report_card(
    learner_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    academic_year: str = Query(...),
) -> LearnerReportCard:
    learner = (await db.execute(
        select(Learner).where(
            Learner.id == learner_id,
            Learner.school_id == user.school_id,
            Learner.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if learner is None:
        raise HTTPException(status_code=404, detail="Learner not found")

    cls = (await db.execute(
        select(SchoolClass).where(SchoolClass.id == learner.class_id)
    )).scalar_one_or_none()

    # Get all term exams for this class in this academic year
    exams = (await db.execute(
        select(TermExam).where(
            TermExam.class_id == learner.class_id,
            TermExam.academic_year == academic_year,
            TermExam.school_id == user.school_id,
        ).order_by(TermExam.term, TermExam.exam_type)
    )).scalars().all()

    # Get all scores for this learner
    exam_ids = [e.id for e in exams]
    if not exam_ids:
        raise HTTPException(status_code=404, detail="No term exams found for this learner in this academic year")

    scores = (await db.execute(
        select(LearnerExamScore).where(
            LearnerExamScore.learner_id == learner_id,
            LearnerExamScore.term_exam_id.in_(exam_ids),
        )
    )).scalars().all()
    score_map = {str(s.term_exam_id): s for s in scores}

    # Build subject reports
    subjects: list[SubjectReport] = []
    exam_type_scores: dict[str, dict[str, list[float]]] = {}  # {term_key: {exam_type: [scores]}}

    for exam in exams:
        la = (await db.execute(
            select(LearningArea).where(LearningArea.id == exam.learning_area_id)
        )).scalar_one_or_none()
        subject_name = la.name if la else "Unknown"

        score = score_map.get(str(exam.id))
        marks = score.marks if score else None
        pct = round((marks / exam.max_marks) * 100, 1) if marks is not None else None

        subjects.append(SubjectReport(
            subject_name=subject_name,
            term=exam.term,
            exam_type=exam.exam_type,
            marks=marks,
            max_marks=exam.max_marks,
            percentage=pct,
            grade=score.grade if score else None,
        ))

        term_key = str(exam.term)
        if term_key not in exam_type_scores:
            exam_type_scores[term_key] = {}
        if exam.exam_type not in exam_type_scores[term_key]:
            exam_type_scores[term_key][exam.exam_type] = []
        if marks is not None:
            exam_type_scores[term_key][exam.exam_type].append((marks / exam.max_marks) * 100)

    # Compute term averages (average of all exam types across subjects for each term)
    term_averages: dict[str, float] = {}
    all_pcts = []
    for term_key, exam_types in exam_type_scores.items():
        term_pcts = []
        for etype, pcts in exam_types.items():
            term_pcts.extend(pcts)
        if term_pcts:
            avg = round(sum(term_pcts) / len(term_pcts), 1)
            term_averages[term_key] = avg
            all_pcts.extend(term_pcts)

    overall_average = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else 0.0

    return LearnerReportCard(
        learner_id=str(learner.id),
        learner_name=learner.full_name,
        admission_no=learner.admission_no,
        class_name=cls.name if cls else "",
        class_id=str(learner.class_id),
        academic_year=academic_year,
        subjects=subjects,
        term_averages=term_averages,
        overall_average=overall_average,
    )


# ---------------------------------------------------------------------------
# 4. Class Analytics
# ---------------------------------------------------------------------------

@router.get("/analytics/class/{class_id}")
async def class_analytics(
    class_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    academic_year: str = Query(...),
) -> ClassAnalytics:
    await _resolve_class(db, user, class_id)

    cls = (await db.execute(
        select(SchoolClass).where(SchoolClass.id == class_id)
    )).scalar_one_or_none()

    exams = (await db.execute(
        select(TermExam).where(
            TermExam.class_id == class_id,
            TermExam.academic_year == academic_year,
            TermExam.school_id == user.school_id,
        ).order_by(TermExam.term, TermExam.exam_type)
    )).scalars().all()

    if not exams:
        raise HTTPException(status_code=404, detail="No term exams found")

    # Get all learners
    learners = (await db.execute(
        select(Learner).where(
            Learner.class_id == class_id,
            Learner.school_id == user.school_id,
            Learner.deleted_at.is_(None),
        ).order_by(Learner.full_name)
    )).scalars().all()

    # Get all scores for these exams
    exam_ids = [e.id for e in exams]
    all_scores = (await db.execute(
        select(LearnerExamScore).where(LearnerExamScore.term_exam_id.in_(exam_ids))
    )).scalars().all()

    # Build analytics
    subjects_set: set[str] = set()
    exam_types_set: set[str] = set()
    terms_set: set[int] = set()
    subject_averages: dict[str, dict[str, list[float]]] = {}

    for exam in exams:
        la = (await db.execute(
            select(LearningArea).where(LearningArea.id == exam.learning_area_id)
        )).scalar_one_or_none()
        subject_name = la.name if la else "Unknown"
        subjects_set.add(subject_name)
        exam_types_set.add(exam.exam_type)
        terms_set.add(exam.term)

        exam_scores = [s for s in all_scores if s.term_exam_id == exam.id]
        pcts = [(s.marks / exam.max_marks) * 100 for s in exam_scores if s.marks is not None]

        if subject_name not in subject_averages:
            subject_averages[subject_name] = {}
        if exam.exam_type not in subject_averages[subject_name]:
            subject_averages[subject_name][exam.exam_type] = []
        subject_averages[subject_name][exam.exam_type].extend(pcts)

    # Compute averages
    subject_avgs_final: dict[str, dict[str, float]] = {}
    all_pcts = []
    for subj, exam_types in subject_averages.items():
        subject_avgs_final[subj] = {}
        for etype, pcts in exam_types.items():
            if pcts:
                avg = round(sum(pcts) / len(pcts), 1)
                subject_avgs_final[subj][etype] = avg
                all_pcts.extend(pcts)

    class_average = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else 0.0

    # Top/bottom learners by overall average
    learner_avgs: list[dict] = []
    for l in learners:
        l_scores = [s for s in all_scores if s.learner_id == l.id]
        if l_scores:
            l_pcts = []
            for s in l_scores:
                exam = next((e for e in exams if e.id == s.term_exam_id), None)
                if exam and s.marks is not None:
                    l_pcts.append((s.marks / exam.max_marks) * 100)
            avg = round(sum(l_pcts) / len(l_pcts), 1) if l_pcts else 0
            learner_avgs.append({"name": l.full_name, "average": avg})

    learner_avgs.sort(key=lambda x: x["average"], reverse=True)
    top_learners = learner_avgs[:5]
    bottom_learners = learner_avgs[-5:] if len(learner_avgs) > 5 else learner_avgs

    return ClassAnalytics(
        class_id=str(class_id),
        class_name=cls.name if cls else "",
        academic_year=academic_year,
        subjects=sorted(subjects_set),
        exam_types=sorted(exam_types_set),
        terms=sorted(terms_set),
        subject_averages=subject_avgs_final,
        class_average=class_average,
        top_learners=top_learners,
        bottom_learners=list(reversed(bottom_learners)),
        total_learners=len(learners),
    )


# ---------------------------------------------------------------------------
# 5. CSV Export
# Moved to app.routers.jobs for async processing.
# Use POST /api/v1/jobs/term-exams/export/class/{class_id}/csv
# Then GET /api/v1/jobs/{job_id}/download
# ---------------------------------------------------------------------------
