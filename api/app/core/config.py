"""Centralised settings, loaded from environment variables."""
from __future__ import annotations

import json
from functools import lru_cache

from pydantic import Field, field_validator
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
    jwt_issuer: str = Field(default="mwalimukit.api", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="mwalimukit.web", alias="JWT_AUDIENCE")
    refresh_token_rotation: bool = Field(default=True, alias="REFRESH_TOKEN_ROTATION")
    max_body_bytes: int = Field(default=1_048_576, alias="API_MAX_BODY_BYTES")

    ai_provider: str = Field(default="mock", alias="AI_PROVIDER")
    ai_api_key: str = Field(default="", alias="AI_API_KEY")
    ai_model: str = Field(default="gpt-4o-mini", alias="AI_MODEL")

    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    cache_ttl_seconds: int = Field(default=300, alias="CACHE_TTL_SECONDS")

    # Rate limiting settings (generous defaults for development/testing)
    rate_limit_login_max: int = Field(default=100, alias="RATE_LIMIT_LOGIN_MAX")
    rate_limit_login_window: int = Field(default=60, alias="RATE_LIMIT_LOGIN_WINDOW")
    rate_limit_signup_max: int = Field(default=100, alias="RATE_LIMIT_SIGNUP_MAX")
    rate_limit_signup_window: int = Field(default=60, alias="RATE_LIMIT_SIGNUP_WINDOW")

    feature_paywall_enabled: bool = Field(default=False, alias="FEATURE_PAYWALL_ENABLED")
    feature_ai_generation_enabled: bool = Field(default=True, alias="FEATURE_AI_GENERATION_ENABLED")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return [
                    "http://localhost:5173",
                    "http://localhost:3000",
                    "https://mwalimukit.vercel.app",
                ]
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://mwalimukit.vercel.app",
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
