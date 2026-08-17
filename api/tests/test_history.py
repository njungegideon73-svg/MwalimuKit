"""Tests for AI prompt history endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_prompt_history_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_save_prompt_history(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/history",
        json={
            "learning_area_code": "LP-MATH",
            "strand_code": "LP-MATH-NUM",
            "sub_strand_codes": ["LP-MATH-NUM-1.1"],
            "grade_level": "Grade 1",
            "teacher_prompt": "Generate a counting test",
            "item_count": 5,
            "provider": "openai",
            "model": "gpt-4o",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["learning_area_code"] == "LP-MATH"
    assert data["provider"] == "openai"


@pytest.mark.asyncio
async def test_list_prompt_history_after_save(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/history",
        json={
            "learning_area_code": "LP-MATH",
            "strand_code": "LP-MATH-NUM",
            "grade_level": "Grade 1",
            "provider": "openai",
            "model": "gpt-4o",
        },
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/history", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_prompt_history_feedback(client: AsyncClient, auth_headers: dict):
    save_resp = await client.post(
        "/api/v1/history",
        json={
            "learning_area_code": "LP-MATH",
            "strand_code": "LP-MATH-NUM",
            "grade_level": "Grade 1",
            "provider": "openai",
            "model": "gpt-4o",
        },
        headers=auth_headers,
    )
    item_id = save_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/history/{item_id}/feedback",
        json={"feedback": "Good output"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["feedback"] == "Good output"
