"""Centralised settings, loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = Field(default="development", alias="API_ENV")
    api_port: int = Field(default=8000, alias="API_PORT")
    secret_key: str = Field(default="dev-secret-change-me", alias="API_SECRET_KEY")
    cors_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://mwalimukit.vercel.app",
    ], alias="API_CORS_ORIGINS")

    database_url: str = Field(default="postgresql+psycopg://mwalimu:mwalimu@db:5432/mwalimukit", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    ai_provider: str = Field(default="mock", alias="AI_PROVIDER")
    ai_api_key: str = Field(default="", alias="AI_API_KEY")
    ai_model: str = Field(default="gpt-4o-mini", alias="AI_MODEL")

    feature_paywall_enabled: bool = Field(default=False, alias="FEATURE_PAYWALL_ENABLED")
    feature_ai_generation_enabled: bool = Field(default=True, alias="FEATURE_AI_GENERATION_ENABLED")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
