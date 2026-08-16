"""Feature flag schemas."""
from __future__ import annotations

from pydantic import BaseModel


class FeatureFlagsOut(BaseModel):
    paywall_enabled: bool
    ai_generation_enabled: bool
    max_classes: int | None
    max_learners_per_class: int | None
