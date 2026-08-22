"""Sentry error-tracking integration.

Initialised at application startup when ``SENTRY_DSN`` is provided.
When the DSN is absent, all calls are no-ops so the library imposes zero
overhead in local development.
"""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Configure Sentry SDK if a DSN is provided in the environment."""
    dsn = getattr(settings, "sentry_dsn", None)
    if not dsn:
        logger.info("SENTRY_DSN not set — error tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.stdlib import StdlibIntegration
    except ImportError:
        logger.warning("sentry-sdk not installed — install with `pip install sentry-sdk`")
        return

    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )

    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            sentry_logging,
            StdlibIntegration(),
        ],
        environment=settings.env,
        release="mwalimukit-api@0.1.0",
        traces_sample_rate=0.1,
        send_default_pii=False,
        before_send=_strip_sensitive_data,
    )
    logger.info("Sentry error tracking initialised")


def _strip_sensitive_data(event, hint):
    """Remove sensitive fields (passwords, tokens, PII) from error events."""
    exception = event.get("exception", {})
    for value in exception.get("values", []):
        stacktrace = value.get("stacktrace", {})
        for frame in stacktrace.get("frames", []):
            if frame.get("vars"):
                for key in list(frame["vars"].keys()):
                    kl = key.lower()
                    if any(s in kl for s in ("password", "token", "secret", "credit_card", "ssn")):
                        frame["vars"][key] = "[Filtered]"
    return event
