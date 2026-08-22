"""Centralised structured logging configuration.

Includes a redaction processor that scrubs fields whose names match
common secret patterns (passwords, tokens, SSNs, credit-card numbers)
before they reach the log sink.
"""
from __future__ import annotations

import logging
import re
import sys

import structlog

#: Field-name fragments that trigger redaction in log records.
_SENSITIVE_KEY_PATTERNS = re.compile(
    r"(password|passwd|pwd|secret|token|access_token|refresh_token|"
    r"credit_card|cc_number|ssn|api_key|apikey|private_key|jwt|"
    r"authorization|auth_header)",
    re.IGNORECASE,
)

#: Regex patterns that trigger value-level redaction.
_SENSITIVE_VALUE_PATTERNS = [
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[REDACTED_CREDIT_CARD]"),
    (re.compile(r"\bssn\b", re.IGNORECASE), "[REDACTED_SSN]"),
]


class _RedactionProcessor:
    """structlog processor that recursively redacts sensitive keys."""

    def __call__(self, logger, method_name, event_dict):
        return _redact_dict(event_dict)


def _redact_dict(d: dict) -> dict:
    if not isinstance(d, dict):
        return d
    result = {}
    for k, v in d.items():
        key_str = str(k)
        if _SENSITIVE_KEY_PATTERNS.search(key_str):
            if isinstance(v, str):
                result[k] = _redact_value(key_str, v)
            else:
                result[k] = "[REDACTED]"
        elif isinstance(v, dict):
            result[k] = _redact_dict(v)
        elif isinstance(v, str):
            result[k] = _redact_value(key_str, v)
        else:
            result[k] = v
    return result


def _redact_value(key: str, value: str) -> str:
    for pattern, replacement in _SENSITIVE_VALUE_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structlog for JSON output on stdout. Idempotent."""
    if getattr(configure_logging, "_configured", False):
        return

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _RedactionProcessor(),
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,  # allow reconfiguration in tests
    )
    configure_logging._configured = True  # type: ignore[attr-defined]


def get_logger():
    return structlog.get_logger()
