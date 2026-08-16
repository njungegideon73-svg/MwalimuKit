"""OpenAI-backed provider."""
from __future__ import annotations

import json

from openai import AsyncOpenAI

from app.ai.provider import (
    GeneratedAssessment, build_system_prompt, build_user_prompt,
)


class OpenAIProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "openai"

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
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        text = resp.choices[0].message.content or "{}"
        data = json.loads(text)
        return GeneratedAssessment(
            rubric=data.get("rubric", {}),
            items=data.get("items", []),
            provider=self.name,
            model=self._model,
        )
