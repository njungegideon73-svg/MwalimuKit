"""Pick the AI provider based on settings."""
from __future__ import annotations

from app.ai.mock_provider import MockProvider
from app.ai.provider import AIProvider
from app.core.config import settings


def get_provider() -> AIProvider:
    provider = (settings.ai_provider or "mock").lower()
    if provider == "openai" and settings.ai_api_key:
        from app.ai.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=settings.ai_api_key, model=settings.ai_model)
    if provider == "anthropic" and settings.ai_api_key:
        from app.ai.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=settings.ai_api_key, model=settings.ai_model)
    return MockProvider()
