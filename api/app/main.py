"""FastAPI application entrypoint."""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    admin, assessments, auth, billing, classes, curriculum, feature_flags,
    health, history, learners, news, reports, runs, scores, schools,
    super_admin, school_admin, term_exams,
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
        allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS", "HEAD"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
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
        log.info("mwalimukit.api.startup", env=settings.env, version="0.1.0", cors_origins=settings.cors_origins)

    app.include_router(health.router, tags=["health"])
    app.include_router(feature_flags.router, prefix="/api/v1", tags=["feature-flags"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(schools.router, prefix="/api/v1/schools", tags=["schools"])
    app.include_router(curriculum.router, prefix="/api/v1/curriculum", tags=["curriculum"])
    app.include_router(assessments.router, prefix="/api/v1/assessments", tags=["assessments"])
    app.include_router(history.router, prefix="/api/v1/history", tags=["history"])
    app.include_router(classes.router, prefix="/api/v1/classes", tags=["classes"])
    app.include_router(learners.router, prefix="/api/v1/learners", tags=["learners"])
    app.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])
    app.include_router(scores.router, prefix="/api/v1/scores", tags=["scores"])
    app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
    app.include_router(news.router, prefix="/api/v1/news", tags=["news"])
    app.include_router(term_exams.router, prefix="/api/v1/term-exams", tags=["term-exams"])
    app.include_router(super_admin.router, prefix="/api/v1/super-admin", tags=["super-admin"])
    app.include_router(school_admin.router, prefix="/api/v1/school-admin", tags=["school-admin"])

    return app


app = create_app()
