"""In-app password login, credential rotation, session management, and logout."""

import datetime
import re
import secrets
import time
import uuid
from typing import Annotated, Any, Literal

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.models import User as UserDB
from camply.db.models import UserSession
from camply.server.auth import (
    NATIVE_SESSION_AUDIENCE,
    NATIVE_SESSION_TOKEN_HEADER,
    CurrentUserDep,
    _get_or_create_admin_user,
    hash_password,
    require_password_not_expired,
    session_credential_version,
    session_signing_key,
    verify_password,
)
from camply.server.config import NATIVE_WEBVIEW_ORIGINS, AuthMode, backend_config
from camply.server.dependencies import SessionDep
from camply.server.routers.me import build_me_response, get_invitation_status
from camply.server.schemas import (
    ChangePasswordRequest,
    MeResponse,
    SessionLoginRequest,
    UserSessionItem,
    UserSessionListResponse,
)

session_router = APIRouter(tags=["auth"])

_SESSION_PRUNE_GRACE_DAYS: int = 7
_MAX_USER_AGENT_LENGTH: int = 512
_MAX_IP_ADDRESS_LENGTH: int = 64
_SESSION_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "headers": {
            NATIVE_SESSION_TOKEN_HEADER: {
                "description": "Bearer credential issued for a native password session.",
                "schema": {"type": "string"},
            }
        }
    }
}


def _extract_client_ip(request: Request) -> str | None:
    """Derive client IP from the first X-Forwarded-For hop or request peer."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first_hop = forwarded_for.split(",", 1)[0].strip()
        if first_hop:
            return first_hop[:_MAX_IP_ADDRESS_LENGTH]
    if request.client and request.client.host:
        return request.client.host[:_MAX_IP_ADDRESS_LENGTH]
    return None


async def _create_user_session(
    session: AsyncSession, user: UserDB, request: Request
) -> UserSession:
    """Persist a new server-side session and prune long-expired rows for this user."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    prune_cutoff = now - datetime.timedelta(days=_SESSION_PRUNE_GRACE_DAYS)
    await session.execute(
        delete(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.expires_at < prune_cutoff,
        )
    )
    raw_user_agent = request.headers.get("User-Agent")
    user_agent = raw_user_agent[:_MAX_USER_AGENT_LENGTH] if raw_user_agent else None
    db_session = UserSession(
        user_id=user.id,
        user_agent=user_agent,
        ip_address=_extract_client_ip(request),
        created_at=now,
        expires_at=now + datetime.timedelta(seconds=backend_config.session_max_age),
    )
    session.add(db_session)
    await session.flush()
    return db_session


def _issue_password_session(
    response: Response, user: UserDB, session_id: uuid.UUID, *, native: bool
) -> None:
    """Issue a bounded credential for the selected password-session transport."""
    claims = {
        "sub": user.email,
        "jti": str(session_id),
        "credentials": session_credential_version(user),
        "exp": int(time.time()) + backend_config.session_max_age,
    }
    response.headers["Cache-Control"] = "no-store"
    if native:
        response.headers[NATIVE_SESSION_TOKEN_HEADER] = jwt.encode(
            {**claims, "aud": NATIVE_SESSION_AUDIENCE},
            session_signing_key(),
            algorithm="HS256",
        )
        return

    csrf = secrets.token_urlsafe(32)
    cookie = jwt.encode(
        {**claims, "csrf": csrf}, session_signing_key(), algorithm="HS256"
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


def _clear_session_cookies(response: Response) -> None:
    """Delete both session and CSRF cookies from the client."""
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


@session_router.post("/login", responses=_SESSION_RESPONSE)
async def login(
    body: SessionLoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    transport: Annotated[
        Literal["bearer"] | None, Header(alias="X-Camply-Session-Transport")
    ] = None,
) -> MeResponse:
    """Validate credentials and establish an expiring signed session."""
    require_session_mode()
    if transport == "bearer":
        if request.headers.get("Origin") not in NATIVE_WEBVIEW_ORIGINS:
            raise HTTPException(status_code=403, detail="Untrusted native login origin")
    else:
        require_trusted_origin(request)

    is_bootstrap_login = secrets.compare_digest(
        body.username.encode(), (backend_config.login_username or "").encode()
    )
    email = backend_config.admin_email if is_bootstrap_login else body.username
    stmt = select(UserDB).where(func.lower(UserDB.email) == email.lower())
    db_user = (await session.execute(stmt)).scalar_one_or_none()
    if db_user is not None and db_user.password_hash is not None:
        password_matches = verify_password(body.password, db_user.password_hash)
    else:
        password_matches = is_bootstrap_login and secrets.compare_digest(
            body.password.encode(), (backend_config.login_password or "").encode()
        )
    if not password_matches:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user = await _get_or_create_admin_user(session) if is_bootstrap_login else db_user
    assert user is not None
    db_session = await _create_user_session(session=session, user=user, request=request)
    session_id = db_session.id
    await session.commit()
    await session.refresh(user)
    invitation_status = await get_invitation_status(
        session=session,
        user_id=user.id,
        email=user.email,
    )
    _issue_password_session(
        response,
        user=user,
        session_id=session_id,
        native=transport == "bearer",
    )
    return build_me_response(user=user, invitation_status=invitation_status)


@session_router.post("/change-password", responses=_SESSION_RESPONSE)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    response: Response,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> MeResponse:
    """Change user password, revoke prior sessions, and refresh this browser's session."""
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

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    await session.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    new_db_session = await _create_user_session(
        session=session, user=user, request=request
    )
    new_session_id = new_db_session.id
    await session.commit()
    await session.refresh(user)
    invitation_status = await get_invitation_status(
        session=session,
        user_id=user.id,
        email=user.email,
    )
    _issue_password_session(
        response,
        user=user,
        session_id=new_session_id,
        native=current_user.native_session,
    )
    return build_me_response(user=user, invitation_status=invitation_status)


@session_router.post("/logout", status_code=204)
async def logout(current_user: CurrentUserDep, session: SessionDep) -> Response:
    """Revoke the current session and clear session and CSRF cookies."""
    require_session_mode()
    if current_user.session_id is not None:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        await session.execute(
            update(UserSession)
            .where(
                UserSession.id == current_user.session_id,
                UserSession.user_id == current_user.id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await session.commit()
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    if not current_user.native_session:
        _clear_session_cookies(response)
    return response


@session_router.get(
    "/me/sessions",
    dependencies=[
        Depends(require_session_mode),
        Depends(require_password_not_expired),
    ],
)
async def list_my_sessions(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> UserSessionListResponse:
    """List active password sessions belonging to the authenticated user."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    stmt = (
        select(UserSession)
        .where(
            UserSession.user_id == current_user.id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .order_by(UserSession.created_at.desc(), UserSession.id.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return UserSessionListResponse(
        items=[
            UserSessionItem(
                id=row.id,
                user_agent=row.user_agent,
                ip_address=row.ip_address,
                created_at=row.created_at,
                expires_at=row.expires_at,
                is_current=(row.id == current_user.session_id),
            )
            for row in rows
        ]
    )


@session_router.delete(
    "/me/sessions/{session_id}",
    status_code=204,
    dependencies=[
        Depends(require_session_mode),
        Depends(require_password_not_expired),
    ],
)
async def revoke_my_session(
    session_id: uuid.UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> Response:
    """Revoke a specific password session owned by the authenticated user."""
    stmt = select(UserSession).where(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id,
    )
    db_session = (await session.execute(stmt)).scalar_one_or_none()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if db_session.revoked_at is None:
        db_session.revoked_at = datetime.datetime.now(tz=datetime.timezone.utc)
        await session.commit()

    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    if session_id == current_user.session_id:
        _clear_session_cookies(response)
    return response
