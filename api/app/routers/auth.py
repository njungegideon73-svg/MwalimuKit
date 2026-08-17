"""Auth router."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.rate_limit import rate_limit_login
from app.schemas.auth import LoginRequest, RefreshRequest, SignupRequest, TokenPair
from app.services.auth import login as svc_login
from app.services.auth import refresh_tokens as svc_refresh
from app.services.auth import signup as svc_signup


router = APIRouter()


@router.post("/signup", response_model=TokenPair)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        return await svc_signup(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_login),
) -> TokenPair:
    try:
        return await svc_login(db, email=payload.email, password=payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        return await svc_refresh(db, payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None
