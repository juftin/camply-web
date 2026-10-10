"""In-app shared-account login and cookie-session logout."""

import re
import secrets
import time

import jwt
from fastapi import APIRouter, HTTPException, Request, Response

from backend.auth import (
    CurrentUserDep,
    _get_or_create_admin_user,
    session_signing_key,
)
from backend.config import AuthMode, backend_config
from backend.dependencies import SessionDep
from backend.schemas import MeResponse, SessionLoginRequest

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
    """Validate shared credentials and establish an expiring signed session."""
    require_session_mode()
    require_trusted_origin(request)
    username_matches = secrets.compare_digest(
        body.username.encode(), (backend_config.login_username or "").encode()
    )
    password_matches = secrets.compare_digest(
        body.password.encode(), (backend_config.login_password or "").encode()
    )
    if not username_matches or not password_matches:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user = await _get_or_create_admin_user(session)
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
