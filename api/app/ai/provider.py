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
) -> str:
    extra = f"\nTeacher guidance: {teacher_prompt}" if teacher_prompt else ""
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
        '    {"id": "itm_01", "criterion": "accuracy", "stem": "...", "answer_guide": "...", "max_level": 4}\n'
        "  ]\n"
        "}"
    )
