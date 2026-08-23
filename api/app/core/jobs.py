"""Background job configuration (Dramatiq + Redis)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, Retries, TimeLimit

from app.core.config import settings

broker = RedisBroker(url=settings.redis_url)
broker.add_middleware(Retries(max_retries=5))
broker.add_middleware(AgeLimit(max_age=3600000))
broker.add_middleware(TimeLimit(time_limit=300000))
dramatiq.set_broker(broker)

RESULT_TTL = 86400


def job_expires_at() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=RESULT_TTL)
