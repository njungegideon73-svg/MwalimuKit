"""Deterministic stub provider."""
from __future__ import annotations

from app.ai.provider import GeneratedAssessment


class MockProvider:
    name = "mock"
    model = "mock-v1"

    async def generate_assessment(
        self,
        *,
        learning_area: str,
        strand: str,
        sub_strand: str,
        grade_level: str,
        teacher_prompt: str | None = None,
        item_count: int = 5,
    ) -> GeneratedAssessment:
        items: list[dict] = []
        for i in range(1, item_count + 1):
            items.append(
                {
                    "id": f"itm_{i:02d}",
                    "criterion": "accuracy",
                    "stem": (
                        f"[Mock draft {i}] A short, age-appropriate question for "
                        f"{grade_level} learners on '{sub_strand}' in {learning_area} ({strand}). "
                        "Replace with your own item."
                    ),
                    "answer_guide": "Edit me.",
                    "max_level": 4,
                }
            )
        rubric = {
            "levels": [
                {"level": 1, "label": "Below expectation",       "descriptor": "Needs significant support."},
                {"level": 2, "label": "Approaching expectation", "descriptor": "Responds with some guidance."},
                {"level": 3, "label": "Meeting expectation",     "descriptor": "Responds correctly with reasoning."},
                {"level": 4, "label": "Exceeding expectation",    "descriptor": "Responds confidently and extends ideas."},
            ],
            "criteria": [
                {"id": "accuracy",  "label": "Accuracy of response"},
                {"id": "reasoning", "label": "Reasoning / justification"},
            ],
        }
        return GeneratedAssessment(rubric=rubric, items=items, provider=self.name, model=self.model)
