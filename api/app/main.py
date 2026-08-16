"""FastAPI application entrypoint."""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    auth, assessments, classes, curriculum, feature_flags, health,
    learners, runs, scores, schools,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="MwalimuKit API",
        version="0.1.0",
        description="Backend for the MwalimuKit CBC assessment platform.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _log_startup() -> None:
        structlog.configure(
            processors=[structlog.processors.add_log_level, structlog.processors.JSONRenderer()],
            wrapper_class=structlog.make_filtering_bound_logger(20),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        log = structlog.get_logger()
        log.info("mwalimukit.api.startup", env=settings.env, version="0.1.0")

    app.include_router(health.router, tags=["health"])
    app.include_router(feature_flags.router, prefix="/api/v1", tags=["feature-flags"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(schools.router, prefix="/api/v1/schools", tags=["schools"])
    app.include_router(curriculum.router, prefix="/api/v1/curriculum", tags=["curriculum"])
    app.include_router(assessments.router, prefix="/api/v1/assessments", tags=["assessments"])
    app.include_router(classes.router, prefix="/api/v1/classes", tags=["classes"])
    app.include_router(learners.router, prefix="/api/v1/learners", tags=["learners"])
    app.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])
    app.include_router(scores.router, prefix="/api/v1/scores", tags=["scores"])

    return app


app = create_app()
