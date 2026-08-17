"""Import every model module here so Alembic can find them."""
from app.models.school import School
from app.models.user import User
from app.models.curriculum import LearningArea, Strand, SubStrand
from app.models.assessment import Assessment
from app.models.school_class import SchoolClass
from app.models.learner import Learner
from app.models.run import AssessmentRun
from app.models.score import Score
from app.models.feature_flag import FeatureFlag
from app.models.prompt_history import PromptHistory

__all__ = [
    "School", "User", "LearningArea", "Strand", "SubStrand", "Assessment",
    "SchoolClass", "Learner", "AssessmentRun", "Score", "FeatureFlag",
    "PromptHistory",
]
