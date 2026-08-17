"""Pluggable AI provider interface."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class GeneratedAssessment:
    rubric: dict
    items: list[dict]
    provider: str
    model: str


class AIProvider(Protocol):
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
    ) -> GeneratedAssessment: ...


def build_system_prompt() -> str:
    return (
        "You design rubric-aligned formative assessments for Kenyan CBC teachers.\n"
        "- Use Kenyan context (names like Achieng, Baraka, Wanjiku; places like Nairobi, Kisumu; "
        "currency in KES).\n"
        "- Use the official 4-level vocabulary: "
        "'Below expectation', 'Approaching expectation', 'Meeting expectation', 'Exceeding expectation'.\n"
        "- Output valid JSON only — no prose.\n"
    )


def build_user_prompt(
    *,
    learning_area: str,
    strand: str,
    sub_strand: str,
    grade_level: str,
    teacher_prompt: str | None,
    item_count: int,
    include_diagrams: bool = False,
) -> str:
    extra = f"\nTeacher guidance: {teacher_prompt}" if teacher_prompt else ""
    diagram_instruction = (
        "\nFor each item, also provide a 'diagram_description' field: a short, practical description of a diagram, chart, flowchart, or picture that would help learners answer the question (e.g. 'A bar chart showing rainfall in mm for 4 months'). Keep descriptions simple and age-appropriate."
        if include_diagrams
        else ""
    )
    return (
        f"Generate a formative assessment.\n"
        f"Learning area: {learning_area}\n"
        f"Strand: {strand}\n"
        f"Sub-strand: {sub_strand}\n"
        f"Grade level: {grade_level}\n"
        f"Item count: {item_count}{extra}\n\n"
        "Return JSON with this shape:\n"
        "{\n"
        '  "rubric": {\n'
        '    "levels": [\n'
        '      {"level": 1, "label": "Below expectation", "descriptor": "..."},\n'
        '      {"level": 2, "label": "Approaching expectation", "descriptor": "..."},\n'
        '      {"level": 3, "label": "Meeting expectation", "descriptor": "..."},\n'
        '      {"level": 4, "label": "Exceeding expectation", "descriptor": "..."}\n'
        "    ],\n"
        '    "criteria": [{"id": "accuracy", "label": "Accuracy of response"}]\n'
        "  },\n"
        '  "items": [\n'
        '    {"id": "itm_01", "criterion": "accuracy", "stem": "...", "answer_guide": "...", "max_level": 4, "diagram_description": "..."}\n'
        "  ]\n"
        "}"
        f"{diagram_instruction}\n"
        "If a diagram is not applicable for an item, use an empty string for diagram_description."
    )
