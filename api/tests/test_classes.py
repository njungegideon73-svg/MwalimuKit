"""Class endpoint tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_class(client: AsyncClient, auth_headers: dict, test_learning_area):
    resp = await client.post(
        "/api/v1/classes",
        json={
            "name": "Grade 2 Red",
            "grade_level": "Grade 2",
            "learning_area_codes": [test_learning_area.code],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Grade 2 Red"
    assert data["grade_level"] == "Grade 2"


@pytest.mark.asyncio
async def test_list_classes(client: AsyncClient, auth_headers: dict, test_class):
    resp = await client.get("/api/v1/classes", headers=auth_headers)
    assert resp.status_code == 200
    classes = resp.json()
    assert len(classes) >= 1
    assert any(c["name"] == "Grade 1 Blue" for c in classes)
