"""Pluggable AI provider interface."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol


# Subject-aware diagram configuration
SUBJECT_DIAGRAM_RULES: dict[str, dict] = {
    "mathematics": {"allowed_types": ["chart", "flowchart"], "probability": 0.4},
    "science": {"allowed_types": ["chart", "flowchart", "diagram"], "probability": 0.5},
    "english": {"allowed_types": [], "probability": 0.0},
    "kiswahili": {"allowed_types": [], "probability": 0.0},
    "social-studies": {"allowed_types": ["chart", "map"], "probability": 0.3},
    "religious-education": {"allowed_types": [], "probability": 0.0},
    "creative-arts": {"allowed_types": ["diagram"], "probability": 0.2},
    "physical-health": {"allowed_types": ["diagram", "flowchart"], "probability": 0.3},
    "home-science": {"allowed_types": ["diagram", "flowchart"], "probability": 0.3},
    "agriculture": {"allowed_types": ["diagram", "flowchart", "chart"], "probability": 0.4},
    "computer-science": {"allowed_types": ["flowchart", "chart"], "probability": 0.4},
}


def _get_diagram_config(learning_area_code: str) -> dict:
    """Get diagram configuration based on learning area code."""
    code_lower = learning_area_code.lower()
    for subject, config in SUBJECT_DIAGRAM_RULES.items():
        if subject in code_lower:
            return config
    # Default: allow charts and flowcharts with 30% probability
    return {"allowed_types": ["chart", "flowchart"], "probability": 0.3}


def _should_include_diagram(learning_area_code: str) -> tuple[bool, str]:
    """Determine if a question should include a diagram and what type."""
    config = _get_diagram_config(learning_area_code)
    if not config["allowed_types"] or random.random() > config["probability"]:
        return False, ""
    diagram_type = random.choice(config["allowed_types"])
    return True, diagram_type


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
    diagram_instruction = ""
    if include_diagrams:
        diagram_instruction = (
            "\nDiagram policy: Not every question needs a diagram. Only include a diagram for questions where a visual aid genuinely improves understanding."
            " Consider the subject context:"
            " - Mathematics: include charts/graphs for data questions, geometry diagrams for shape questions"
            " - Science: include experimental setup diagrams, flowcharts for processes, charts for data"
            " - Social Studies: include maps, charts for demographics, timelines"
            " - Computer Science: include flowcharts, system diagrams"
            " - Creative Arts: include simple visual references"
            " For subjects like English, Kiswahili, or Religious Education, diagrams are rarely needed."
            "\nFor each item that benefits from a diagram, include a 'diagram_type' field:"
            "  - 'chart': for numerical data (bar, line, pie charts). Also include 'diagram_data' as a JSON string with:"
            "    {type: 'bar'|'line'|'pie', labels: [...], values: [...], title: '...'}"
            "  - 'flowchart': for processes or procedures. Include 'diagram_data' as Mermaid.js flowchart code (e.g., 'flowchart TD; A-->B; B-->C')."
            "  - 'diagram': for simple labeled sketches or illustrations. Include 'diagram_data' as a short text description of what the diagram should show."
            "\nIf a diagram is not applicable for an item, omit the diagram fields or set diagram_type to 'none'."
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
        '    {"id": "itm_01", "criterion": "accuracy", "stem": "...", "answer_guide": "...", "max_level": 4, '
        '"diagram_type": "chart"|"flowchart"|"diagram"|"none", "diagram_data": "..."}\n'
        "  ]\n"
        "}"
        f"{diagram_instruction}\n"
    )
