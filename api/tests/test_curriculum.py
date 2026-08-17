"""Tests for the curriculum router."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_catalogue(client: AsyncClient, auth_headers: dict, test_learning_area, test_strand, test_sub_strand):
    resp = await client.get("/api/v1/curriculum/catalogue", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "learning_areas" in data
    assert "strands" in data
    assert "sub_strands" in data
    assert len(data["learning_areas"]) >= 1
    la = data["learning_areas"][0]
    assert "code" in la
    assert "name" in la
    assert "level" in la


@pytest.mark.asyncio
async def test_get_catalogue_unauthorized(client: AsyncClient):
    resp = await client.get("/api/v1/curriculum/catalogue")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_catalogue_strands_reference_valid_learning_areas(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.get("/api/v1/curriculum/catalogue", headers=auth_headers)
    data = resp.json()
    la_codes = {la["code"] for la in data["learning_areas"]}
    for strand in data["strands"]:
        assert strand["learning_area_code"] in la_codes


@pytest.mark.asyncio
async def test_catalogue_sub_strands_reference_valid_strands(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.get("/api/v1/curriculum/catalogue", headers=auth_headers)
    data = resp.json()
    strand_codes = {s["code"] for s in data["strands"]}
    for ss in data["sub_strands"]:
        assert ss["strand_code"] in strand_codes
