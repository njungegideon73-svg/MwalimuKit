"""Learner endpoint tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_add_learner(client: AsyncClient, auth_headers: dict, test_class):
    resp = await client.post(
        "/api/v1/learners",
        json={
            "class_id": str(test_class.id),
            "full_name": "Baraka Mwangi",
            "admission_no": "ADM002",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Baraka Mwangi"
    assert data["admission_no"] == "ADM002"


@pytest.mark.asyncio
async def test_bulk_add_learners(client: AsyncClient, auth_headers: dict, test_class):
    resp = await client.post(
        "/api/v1/learners/bulk",
        json={
            "class_id": str(test_class.id),
            "lines": ["Wanjiku Kamau,ADM003", "Otieno Odhiambo,ADM004", "Amina Hassan"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    learners = resp.json()
    assert len(learners) == 3


@pytest.mark.asyncio
async def test_list_learners_for_class(
    client: AsyncClient, auth_headers: dict, test_class, test_learner
):
    resp = await client.get(
        f"/api/v1/learners/by-class/{test_class.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    learners = resp.json()
    assert len(learners) >= 1
    assert any(l["full_name"] == "Achieng Omondi" for l in learners)


@pytest.mark.asyncio
async def test_update_learner(client: AsyncClient, auth_headers: dict, test_learner):
    resp = await client.patch(
        f"/api/v1/learners/{test_learner.id}",
        json={"full_name": "Achieng Updated", "admission_no": "ADM999"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Achieng Updated"
    assert data["admission_no"] == "ADM999"


@pytest.mark.asyncio
async def test_delete_learner(client: AsyncClient, auth_headers: dict, test_learner):
    resp = await client.delete(
        f"/api/v1/learners/{test_learner.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Verify soft deleted - should not appear in list
    list_resp = await client.get(
        f"/api/v1/learners/by-class/{test_learner.class_id}", headers=auth_headers
    )
    learners = list_resp.json()
    assert not any(l["id"] == str(test_learner.id) for l in learners)


@pytest.mark.asyncio
async def test_delete_nonexistent_learner(client: AsyncClient, auth_headers: dict):
    from uuid import uuid4
    resp = await client.delete(
        f"/api/v1/learners/{uuid4()}", headers=auth_headers
    )
    assert resp.status_code == 404
