"""Auth router."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.core.metrics import inc_counter
from app.core.rate_limit import (
    LOCKOUT_MAX_FAILURES,
    clear_login_failures,
    is_locked_out,
    rate_limit_login,
    rate_limit_password_change,
    rate_limit_password_reset,
    rate_limit_password_reset_request,
    rate_limit_refresh,
    rate_limit_signup,
    register_login_failure,
)
from app.core.sanitization import sanitize_text
from app.core.security import decode_token, verify_password
from app.core.sessions import list_sessions, revoke_all_sessions, revoke_session
from app.core.tenant import set_auth_email
from app.models.school import School
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangeSchoolCodeRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    TokenPair,
)
from app.schemas.password_reset import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
)
from app.services.auth import login as svc_login
from app.services.auth import pair_for_user
from app.services.auth import refresh_tokens as svc_refresh
from app.services.auth import signup as svc_signup
from app.services.password_reset import (
    generate_reset_token,
    reset_password as svc_reset_password,
    store_reset_token,
)
from app.utils.activity_logger import log_activity
from app.core.logging import get_logger

logger = get_logger()


router = APIRouter()


@router.post("/signup", response_model=TokenPair)
async def signup(
    payload: SignupRequest,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_signup),
) -> TokenPair:
    # Seed the email GUC so RLS on the users table permits the existence check.
    set_auth_email(payload.email)
    try:
        user_agent = request.headers.get("user-agent", "")
        return await svc_signup(db, payload, user_agent=user_agent)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_login),
) -> TokenPair:
    ip = request.client.host if request.client else "unknown"

    # Seed the email GUC so RLS on the users table permits the lookup.
    set_auth_email(payload.email)

    if await is_locked_out(payload.email, ip):
        inc_counter("mwalimukit_login_failures_total", {"reason": "locked"})
        raise HTTPException(
            status_code=429,
            detail="Account temporarily locked due to repeated failed logins. Try again later.",
        )

    try:
        user_agent = request.headers.get("user-agent", "")
        result = await svc_login(db, email=payload.email, password=payload.password, user_agent=user_agent)
    except ValueError:
        count = await register_login_failure(payload.email, ip)
        inc_counter("mwalimukit_login_failures_total", {"reason": "bad_credentials"})
        from app.core.logging import get_logger

        get_logger().warning(
            "security.login_failed",
            email=payload.email,
            ip=ip,
            failures=count,
            locked=count >= LOCKOUT_MAX_FAILURES,
        )
        if count >= LOCKOUT_MAX_FAILURES:
            raise HTTPException(
                status_code=429,
                detail="Too many failed attempts. Account temporarily locked.",
            ) from None
        raise HTTPException(status_code=401, detail="Invalid email or password.") from None

    await clear_login_failures(payload.email, ip)
    user = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if user:
        user.last_login_at = datetime.now(tz=timezone.utc)
        await db.commit()
        await log_activity(
            db,
            user_id=user.id,
            school_id=user.school_id,
            action="auth.login",
            details={"email": user.email, "ip": ip},
        )
    return result


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_refresh),
) -> TokenPair:
    try:
        user_agent = request.headers.get("user-agent", "")
        return await svc_refresh(db, payload.refresh_token, user_agent=user_agent)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None


@router.post("/logout")
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Revoke the supplied refresh token. Safe to call with an expired or
    invalid token — always returns success so clients can't probe tokens."""
    try:
        token_payload = decode_token(payload.refresh_token)
    except Exception:
        return {"ok": True}

    if token_payload.get("type") == "refresh":
        jti = token_payload.get("jti")
        if jti:
            from app.services.auth import _revoke_refresh

            await _revoke_refresh(jti)
    return {"ok": True}


@router.post("/change-password", response_model=TokenPair)
async def change_password(
    payload: ChangePasswordRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_password_change),
) -> TokenPair:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    from app.core.security import hash_password

    user.password_hash = hash_password(payload.new_password)
    # Invalidate every existing session (all devices); the fresh pair below
    # keeps the current device signed in.
    user.token_version += 1
    await db.commit()
    await db.refresh(user)

    # Revoke all server-side sessions; a new one is created by pair_for_user.
    await revoke_all_sessions(str(user.id))

    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="auth.password_changed",
        details={"email": user.email},
    )
    from app.core.logging import get_logger

    get_logger().info("security.password_changed", user_id=str(user.id))
    return pair_for_user(user)


@router.post("/change-school-code")
async def change_school_code(
    payload: ChangeSchoolCodeRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_password_change),
) -> dict:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Password is incorrect")

    school = (
        await db.execute(select(School).where(School.code == payload.new_school_code))
    ).scalar_one_or_none()
    if school is None:
        raise HTTPException(status_code=400, detail="School code not found")

    user.school_id = school.id
    user.token_version += 1  # role/tenant changed → drop other sessions
    await db.commit()
    await revoke_all_sessions(str(user.id))
    return {"changed": True, "school_id": str(school.id)}


# ── Password Reset ────────────────────────────────────────────────────────────


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_password_reset_request),
) -> ForgotPasswordResponse:
    """Initiate a password reset.

    Always returns the same response whether or not the email exists,
    to prevent user-enumeration attacks.
    """
    set_auth_email(payload.email)
    user = await _find_user_for_reset(db, payload.email)

    if user is not None:
        token = generate_reset_token()
        await store_reset_token(user.email, token)
        # In production, email the link.  For now we log it (never in prod logs).
        reset_link = f"{request.url.scheme}://{request.client.host if request.client else 'localhost'}:5173/reset-password?token={token}&email={user.email}"
        logger.info("security.password_reset_requested", user_id=str(user.id), email=user.email)
        if logger.isEnabledFor(10):  # DEBUG only
            logger.debug("security.password_reset_token", reset_link=reset_link)

    # Always return the same response to prevent enumeration.
    inc_counter("mwalimukit_password_reset_requested_total")
    return ForgotPasswordResponse()


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_password_reset),
) -> dict:
    """Complete a password reset using a token from ``/forgot-password``."""
    # The email is embedded in the token key (pwd_reset:{email}:{token});
    # _find_user_by_reset_token resolves it and sets the auth-email GUC.
    user = await _find_user_by_reset_token(db, payload.token)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    from app.core.security import hash_password

    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1  # Invalidate all existing sessions.
    await db.commit()
    await db.refresh(user)

    await revoke_all_sessions(str(user.id))

    ip = request.client.host if request.client else "unknown"
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="auth.password_reset",
        details={"email": user.email, "ip": ip},
    )
    logger.info("security.password_reset_completed", user_id=str(user.id), email=user.email)
    inc_counter("mwalimukit_password_reset_completed_total")
    return {"ok": True, "detail": "Password has been reset."}


async def _find_user_for_reset(db: AsyncSession, email: str) -> User | None:
    """Find a user by email for the reset flow (RLS-aware)."""
    from app.core.tenant import set_auth_email as _set_email

    _set_email(email)
    result = await db.execute(
        select(User).where(User.email == email, User.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def _find_user_by_reset_token(db: AsyncSession, token: str) -> User | None:
    """Find the user associated with a reset token by scanning active tokens.

    Reset tokens are stored as ``pwd_reset:{email}:{token}``.  We do a Redis
    SCAN to find the matching key without leaking which emails have tokens.
    """
    from app.core.cache import _get_redis, _memory

    redis = await _get_redis()
    target_email: str | None = None

    if redis is not None:
        try:
            pattern = f"{token}*"
            # We look for keys ending in the token; scope prefix is pwd_reset
            async for key in redis.scan_iter(f"*:{token}"):
                # key looks like: pwd_reset:alice@example.com:token
                parts = key.rsplit(":", 2)
                if len(parts) == 3:
                    target_email = parts[1]
                    break
        except Exception:
            pass

    if target_email is None:
        # Check in-process fallback
        for mem_key in list(_memory.keys()):
            if mem_key.endswith(f":{token}"):
                parts = mem_key.rsplit(":", 1)
                # mem_key is like "pwd_reset:alice@example.com:token"
                full_key = parts[0] if parts else mem_key
                # Extract email from the full key
                prefix_removed = full_key[len("pwd_reset:"):]
                target_email = prefix_removed
                break

    if target_email is None:
        return None

    # Set auth email GUC then look up the user.
    set_auth_email(target_email)
    result = await db.execute(
        select(User).where(User.email == target_email, User.is_active.is_(True))
    )
    return result.scalar_one_or_none()


# ── Session Management ────────────────────────────────────────────────


@router.get("/sessions", response_model=list[dict])
async def list_active_sessions(user: CurrentUser) -> list[dict]:
    """List the current user's active server-side sessions."""
    sessions = await list_sessions(str(user.id))
    return sessions


@router.post("/sessions/revoke")
async def revoke_session_endpoint(
    payload: dict,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke a specific session by session_id.

    The current session cannot be revoked (use the client-side logout).
    """
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")
    ok = await revoke_session(str(user.id), str(session_id))
    inc_counter("mwalimukit_session_revoked_total")
    return {"ok": ok}


@router.post("/sessions/revoke-all")
async def revoke_all_sessions_endpoint(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke all other sessions for the current user (force logout elsewhere)."""
    count = await revoke_all_sessions(str(user.id))
    # Bump token_version to invalidate JWTs immediately.
    user.token_version += 1
    await db.commit()
    await db.refresh(user)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="auth.sessions_revoked_all",
        details={"count": count},
    )
    inc_counter("mwalimukit_session_revoked_total", {"scope": "all"})
    return {"ok": True, "revoked": count}
