"""Healthcheck."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "mwalimukit-api", "version": "0.1.0"}
