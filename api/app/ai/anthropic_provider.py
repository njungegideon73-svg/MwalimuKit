"""Anthropic-backed provider."""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic

from app.ai.provider import (
    GeneratedAssessment, build_system_prompt, build_user_prompt,
)


class AnthropicProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

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
        prompt = build_user_prompt(
            learning_area=learning_area,
            strand=strand,
            sub_strand=sub_strand,
            grade_level=grade_level,
            teacher_prompt=teacher_prompt,
            item_count=item_count,
        )
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=build_system_prompt(),
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text if resp.content else "{}"
        data = json.loads(text)
        return GeneratedAssessment(
            rubric=data.get("rubric", {}),
            items=data.get("items", []),
            provider=self.name,
            model=self._model,
        )
