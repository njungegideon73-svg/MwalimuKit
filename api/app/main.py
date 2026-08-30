"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    BodySizeLimitMiddleware,
    MetricsMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.rate_limit import GlobalThrottleMiddleware
from app.core.sentry import init_sentry
from app.core.tenant import TenantContextMiddleware
from app.routers import (
    admin, assessments, auth, billing, classes, curriculum, feature_flags,
    health, history, jobs, learners, news, reports, runs, scores, schools,
    super_admin, school_admin, term_exams,
)

_DEFAULT_SECRET = "dev-secret-change-me"


def _validate_production_secrets() -> None:
    """Refuse to boot in production with insecure settings."""
    if settings.env != "production":
        return
    if not settings.secret_key or settings.secret_key == _DEFAULT_SECRET:
        raise RuntimeError("API_SECRET_KEY must be set before running in production")
    if len(settings.secret_key) < 32:
        raise RuntimeError("API_SECRET_KEY must be at least 32 characters in production")


def create_app() -> FastAPI:
    configure_logging()
    init_sentry()
    log = get_logger()
    _validate_production_secrets()

    app = FastAPI(
        title="MwalimuKit API",
        version="0.1.0",
        description="Backend for the MwalimuKit CBC assessment platform.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware + handlers (see helper functions below)
    _register_middleware(app)

    @app.on_event("startup")
    async def _log_startup() -> None:
        log.info(
            "mwalimukit.api.startup",
            env=settings.env,
            version="0.1.0",
            cors_origins=settings.cors_origins,
        )

    _register_exception_handlers(app, log)
    _register_metrics_endpoint(app)

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
    app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])

    return app


def _register_middleware(app: FastAPI) -> None:
    """Order (outermost first): Tenant context → CORS → global throttle →
    security headers → body size limit → metrics → request context."""
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GlobalThrottleMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS", "HEAD"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )


def _register_exception_handlers(app: FastAPI, log) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Last-resort handler: never leak stack traces or internals."""
        log.error(
            "api.unhandled_exception",
            method=request.method,
            path=request.url.path,
            error=type(exc).__name__,
            detail=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Log validation failures and strip the echoed input payload
        (it may contain credentials or personal data)."""
        log.info(
            "api.validation_error",
            method=request.method,
            path=request.url.path,
            errors=len(exc.errors()),
        )
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
                    for e in exc.errors()
                ]
            },
        )

    from fastapi.exceptions import HTTPException as FHTTPException

    @app.exception_handler(FHTTPException)
    async def http_exception_handler(request: Request, exc: FHTTPException):
        """Sanitised HTTP error responses: generic message for 5xx-like
        client errors that may leak internals; structured detail for
        well-known 4xx (400, 401, 403, 404, 409, 413, 422, 429)."""
        safe_statuses = {400, 401, 403, 404, 409, 413, 422, 429}
        if exc.status_code in safe_statuses:
            detail = exc.detail
        else:
            detail = "An error occurred while processing your request."
        log.info(
            "api.http_error",
            method=request.method,
            path=request.url.path,
            status=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail},
        )


def _register_metrics_endpoint(app: FastAPI) -> None:
    from app.core.metrics import render_metrics
    from starlette.responses import Response

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=render_metrics(), media_type="text/plain; version=0.0.4")


app = create_app()
