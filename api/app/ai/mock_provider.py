"""Deterministic stub provider."""
from __future__ import annotations

import random

from app.ai.provider import GeneratedAssessment, _should_include_diagram


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
        include_diagrams: bool = False,
    ) -> GeneratedAssessment:
        items: list[dict] = []
        for i in range(1, item_count + 1):
            diagram_type = "none"
            diagram_data = ""
            if include_diagrams:
                should_have, dtype = _should_include_diagram(learning_area)
                if should_have and dtype:
                    diagram_type = dtype
                    if dtype == "chart":
                        diagram_data = '{"type": "bar", "labels": ["A", "B", "C"], "values": [10, 20, 15], "title": "Sample Data"}'
                    elif dtype == "flowchart":
                        diagram_data = "flowchart TD\n    A[Start] --> B[Process]\n    B --> C[End]"
                    elif dtype == "diagram":
                        diagram_data = f"A labeled diagram showing key parts of {sub_strand}"
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
                    "diagram_description": diagram_data if diagram_type == "diagram" else "",
                    "diagram_type": diagram_type,
                    "diagram_data": diagram_data,
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
