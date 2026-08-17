"""Feature flags endpoint tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_default_flags(client: AsyncClient):
    resp = await client.get("/api/v1/feature-flags")
    assert resp.status_code == 200
    data = resp.json()
    assert data["paywall_enabled"] is False
    assert data["ai_generation_enabled"] is True
    assert data["max_classes"] is None
    assert data["max_learners_per_class"] is None
