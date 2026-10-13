"""In-app shared-account login and cookie-session logout."""

import re
import secrets
import time

import jwt
from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import func, select

from backend.auth import (
    CurrentUserDep,
    _get_or_create_admin_user,
    hash_password,
    session_signing_key,
    verify_password,
)
from backend.config import AuthMode, backend_config
from backend.dependencies import SessionDep
from backend.schemas import (
    ChangePasswordRequest,
    MeResponse,
    SessionLoginRequest,
)
from db.models import User as UserDB

session_router = APIRouter(tags=["auth"])


def require_session_mode() -> None:
    """Expose password-session operations only when the owner enables them."""
    if backend_config.auth_mode != AuthMode.SESSION:
        raise HTTPException(status_code=404, detail="Password login is not enabled")


def require_trusted_origin(request: Request) -> None:
    """Reject browser login requests originating from an untrusted website."""
    origin = request.headers.get("Origin")
    same_origin = f"{request.url.scheme}://{request.url.netloc}"
    if (
        origin
        and origin != same_origin
        and origin not in backend_config.cors_origins
        and not (
            backend_config.cors_origin_regex
            and re.fullmatch(backend_config.cors_origin_regex, origin)
        )
    ):
        raise HTTPException(status_code=403, detail="Untrusted login origin")


@session_router.post("/login")
async def login(
    body: SessionLoginRequest, request: Request, response: Response, session: SessionDep
) -> MeResponse:
    """Validate credentials and establish an expiring signed session."""
    require_session_mode()
    require_trusted_origin(request)

    user: UserDB | None = None
    if (
        backend_config.login_username
        and backend_config.login_password
        and secrets.compare_digest(
            body.username.encode(), backend_config.login_username.encode()
        )
        and secrets.compare_digest(
            body.password.encode(), backend_config.login_password.encode()
        )
    ):
        user = await _get_or_create_admin_user(session)
    else:
        stmt = select(UserDB).where(func.lower(UserDB.email) == body.username.lower())
        db_user = (await session.execute(stmt)).scalar_one_or_none()
        if (
            db_user is not None
            and db_user.password_hash is not None
            and verify_password(body.password, db_user.password_hash)
        ):
            user = db_user

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    csrf = secrets.token_urlsafe(32)
    cookie = jwt.encode(
        {
            "sub": user.email,
            "csrf": csrf,
            "exp": int(time.time()) + backend_config.session_max_age,
        },
        session_signing_key(),
        algorithm="HS256",
    )
    response.set_cookie(
        key="camply_session",
        value=cookie,
        max_age=backend_config.session_max_age,
        httponly=True,
        secure=backend_config.session_cookie_secure,
        samesite="strict",
    )
    response.set_cookie(
        key="camply_csrf",
        value=csrf,
        max_age=backend_config.session_max_age,
        secure=backend_config.session_cookie_secure,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    return MeResponse.model_validate(user, from_attributes=True)


@session_router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> MeResponse:
    """Change user password and clear must_change_password flag."""
    require_session_mode()
    stmt = select(UserDB).where(UserDB.id == current_user.id)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    password_verified = False
    if user.password_hash is not None:
        password_verified = verify_password(body.current_password, user.password_hash)
    elif (
        user.email == backend_config.admin_email
        and backend_config.login_password is not None
    ):
        password_verified = secrets.compare_digest(
            body.current_password.encode(), backend_config.login_password.encode()
        )

    if not password_verified:
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    await session.commit()
    await session.refresh(user)

    return MeResponse.model_validate(user, from_attributes=True)


@session_router.post("/logout", status_code=204)
async def logout(current_user: CurrentUserDep) -> Response:
    """Clear the session and CSRF cookies after an authenticated logout."""
    require_session_mode()
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        key="camply_session",
        httponly=True,
        secure=backend_config.session_cookie_secure,
        samesite="strict",
    )
    response.delete_cookie(
        key="camply_csrf",
        secure=backend_config.session_cookie_secure,
        samesite="strict",
    )
    return response
