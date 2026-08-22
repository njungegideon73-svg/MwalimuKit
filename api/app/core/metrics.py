"""Minimal, dependency-free Prometheus-style metrics.

Counters and histograms are kept in-process. This covers the single
container deployment the project ships today; swap for
prometheus_client / an OTLP exporter if scraping needs grow.
"""
from __future__ import annotations

import time

from starlette.requests import Request

# Cumulative bucket upper bounds (seconds) for request durations.
DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

_started_at = time.time()

# name -> {(label_key, label_value, ...): value}
_counters: dict[str, dict[tuple, float]] = {}
# name -> {labels: {"buckets": [counts], "sum": float, "count": int}}
_histograms: dict[str, dict[tuple, dict]] = {}


def _labels_key(labels: dict[str, str]) -> tuple:
    return tuple(sorted(labels.items()))


def inc_counter(name: str, labels: dict[str, str] | None = None, value: float = 1.0) -> None:
    key = _labels_key(labels or {})
    _counters.setdefault(name, {})
    _counters[name][key] = _counters[name].get(key, 0) + value


def observe_duration(name: str, seconds: float, labels: dict[str, str] | None = None) -> None:
    key = _labels_key(labels or {})
    hist = _histograms.setdefault(name, {}).setdefault(
        key, {"buckets": [0] * len(DURATION_BUCKETS), "sum": 0.0, "count": 0}
    )
    hist["sum"] += seconds
    hist["count"] += 1
    for i, bound in enumerate(DURATION_BUCKETS):
        if seconds <= bound:
            hist["buckets"][i] += 1


def render_metrics() -> str:
    """Render all collected metrics in Prometheus text exposition format."""
    lines: list[str] = []
    uptime = time.time() - _started_at

    lines.append("# TYPE mwalimukit_uptime_seconds gauge")
    lines.append(f"mwalimukit_uptime_seconds {uptime:.3f}")

    for name, series in _counters.items():
        lines.append(f"# TYPE {name} counter")
        for key, value in series.items():
            label_str = _format_labels(dict(key))
            lines.append(f"{name}{label_str} {value}")

    for name, series in _histograms.items():
        base = name.removesuffix("_seconds")
        lines.append(f"# TYPE {name} histogram")
        for key, hist in series.items():
            base_labels = dict(key)
            cumulative = 0
            for bound, count in zip(DURATION_BUCKETS, hist["buckets"]):
                cumulative += count
                labels = {**base_labels, "le": str(bound)}
                lines.append(f"{name}_bucket{_format_labels(labels)} {cumulative}")
            lines.append(f"{name}_bucket{{le=\"+Inf\"}} {hist['count']}")
            lines.append(f"{name}_sum{base_labels and _format_labels(base_labels)} {hist['sum']:.6f}")
            lines.append(f"{name}_count{base_labels and _format_labels(base_labels)} {hist['count']}")

    return "\n".join(lines) + "\n"


def _format_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    pairs = ",".join(f'{k}="{_escape(v)}"' for k, v in sorted(labels.items()))
    return "{" + pairs + "}"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def normalize_path(request: Request) -> str:
    """Route template for low-cardinality labels (e.g. /api/v1/learners/{learner_id})."""
    route = request.scope.get("route")
    path_format = getattr(route, "path_format", None)
    if path_format:
        # Find the prefix from the app's routers
        app = request.scope.get("app")
        if app:
            for r in getattr(app, "routes", []):
                # Check if this is an _IncludedRouter with a prefix
                include_context = getattr(r, "include_context", None)
                if include_context and hasattr(include_context, "prefix"):
                    prefix = include_context.prefix
                    # Check if the route is part of this router
                    original_router = getattr(r, "original_router", None)
                    if original_router and route in getattr(original_router, "routes", []):
                        return f"{prefix}{path_format}"
        return path_format
    # Fallback before routing matched: mask obvious id segments.
    parts = request.scope.get("path", "").split("/")
    masked = [":id" if _looks_like_id(p) else p for p in parts]
    return "/".join(masked) or "/"


def _looks_like_id(segment: str) -> bool:
    if not segment or len(segment) < 8:
        return False
    hexish = sum(c in "0123456789abcdefABCDEF-" for c in segment)
    return hexish / len(segment) > 0.7


def reset_metrics() -> None:
    """Test helper: wipe all counters/histograms."""
    global _started_at
    _counters.clear()
    _histograms.clear()
    _started_at = time.time()


# ── Business metrics ───────────────────────────────────────────────────────────


def inc_business_counter(name: str, labels: dict[str, str] | None = None) -> None:
    """Increment a business-level counter (users created, assessments generated, etc.)."""
    prefix = f"mwalimukit_business_{name}"
    inc_counter(prefix, labels)


def set_business_gauge(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    """Set a business-level gauge (active users, trial schools, etc.).

    Uses the counter mechanism with a delta to approximate a gauge.
    """
    prefix = f"mwalimukit_business_{name}"
    inc_counter(prefix, labels, value=value)
