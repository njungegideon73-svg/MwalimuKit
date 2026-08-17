"""Term exam + learner score schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TermExamIn(BaseModel):
    class_id: str
    learning_area_id: str
    term: int = Field(ge=1, le=3)
    exam_type: str = Field(pattern=r"^(opener|midterm|endterm)$")
    academic_year: str = Field(min_length=4, max_length=10)
    max_marks: int = Field(default=100, ge=1, le=1000)


class TermExamOut(BaseModel):
    id: str
    school_id: str
    class_id: str
    class_name: str
    learning_area_id: str
    learning_area_name: str
    term: int
    exam_type: str
    academic_year: str
    max_marks: int
    created_at: str


class LearnerScoreIn(BaseModel):
    learner_id: str
    marks: int = Field(ge=0)
    grade: str | None = None
    comment: str | None = None


class MarksEntryPayload(BaseModel):
    scores: list[LearnerScoreIn]


class LearnerScoreOut(BaseModel):
    id: str
    learner_id: str
    learner_name: str
    admission_no: str | None
    marks: int
    grade: str | None
    comment: str | None


class SubjectReport(BaseModel):
    subject_name: str
    term: int
    exam_type: str
    marks: int | None
    max_marks: int
    percentage: float | None
    grade: str | None


class LearnerReportCard(BaseModel):
    learner_id: str
    learner_name: str
    admission_no: str | None
    class_name: str
    class_id: str
    academic_year: str
    subjects: list[SubjectReport]
    term_averages: dict[str, float]  # e.g. {"1": 75.5, "2": 80.0}
    overall_average: float


class ClassAnalytics(BaseModel):
    class_id: str
    class_name: str
    academic_year: str
    subjects: list[str]
    exam_types: list[str]
    terms: list[int]
    subject_averages: dict[str, dict[str, float]]  # {subject: {exam_type: avg}}
    class_average: float
    top_learners: list[dict]
    bottom_learners: list[dict]
    total_learners: int
