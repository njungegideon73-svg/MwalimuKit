"""Input sanitization utilities for XSS prevention.

Strips HTML tags and dangerous characters from free-text fields before they
are persisted.  Uses a deny-list approach for common XSS vectors; for
rich-text fields the front-end already sanitizes via a dedicated editor,
but plain-text fields that may surface in reports (learner names, notes)
should always pass through :func:`sanitize_text`.
"""
from __future__ import annotations

import html
import re

_SCRIPT_TAG_RE = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_EVENT_HANDLER_RE = re.compile(r"\bon\w+\s*=", re.IGNORECASE)
_JS_URL_RE = re.compile(r"javascript:", re.IGNORECASE)
_VB_URL_RE = re.compile(r"vbscript:", re.IGNORECASE)
_DATA_URL_RE = re.compile(r"data:text/html", re.IGNORECASE)

_MAX_LENGTH = 5000


def sanitize_text(value: str | None, max_length: int = _MAX_LENGTH) -> str | None:
    """Return a plain-text, HTML-escaped representation of *value*.

    - HTML tags are removed (not escaped-then-rendered).
    - Dangerous event-handler attributes and javascript:/vbscript:/data: URLs
      are neutralized.
    - The result is HTML-escaped so it is safe to embed in PDF or HTML output.
    - Truncates to *max_length* characters.
    """
    if value is None:
        return None

    # Strip script blocks entirely first (inner HTML could survive tag removal).
    cleaned = _SCRIPT_TAG_RE.sub("", value)
    # Remove any remaining HTML tags.
    cleaned = _HTML_TAG_RE.sub("", cleaned)
    # Neutralize dangerous URL schemes and inline event handlers.
    cleaned = _EVENT_HANDLER_RE.sub("", cleaned)
    cleaned = _JS_URL_RE.sub("", cleaned)
    cleaned = _VB_URL_RE.sub("", cleaned)
    cleaned = _DATA_URL_RE.sub("", cleaned)

    # HTML-escape the final string so angle brackets/quotes become entities.
    cleaned = html.escape(cleaned, quote=True)

    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


def sanitize_dict(data: dict, fields: list[str] | None = None) -> dict:
    """Sanitize string values in *data*.

    If *fields* is provided, only those keys are sanitized; otherwise every
    ``str`` value in the top-level dict is sanitized.
    """
    result = dict(data)
    keys = fields if fields is not None else list(result.keys())
    for k in keys:
        v = result.get(k)
        if isinstance(v, str):
            result[k] = sanitize_text(v) or ""
    return result
