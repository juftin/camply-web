"""
Authentication utilities for camply-backend.

The instance owner chooses automatic admin login, in-app cookie sessions, or
Auth0 bearer tokens. The environment does not override this choice.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from typing import Annotated, Optional

import jwt
import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt import PyJWKClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import AuthMode, backend_config
from backend.dependencies import SessionDep
from db.models import User

logger = structlog.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bearer authentication for Auth0 JWTs
# ---------------------------------------------------------------------------

bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Auth0 helpers
# ---------------------------------------------------------------------------

_AUTH0_ALGORITHMS = ["RS256"]
_jwks_client_cache: dict[str, PyJWKClient] = {}


def _get_jwks_client() -> PyJWKClient:
    """Return a cached module-level ``PyJWKClient`` for Auth0 JWKS fetching."""
    domain = backend_config.auth0_domain
    assert domain is not None, "auth0_domain must be configured in auth0 mode"
    if domain not in _jwks_client_cache:
        jwks_url = f"https://{domain}/.well-known/jwks.json"
        _jwks_client_cache[domain] = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client_cache[domain]


async def _verify_auth0_token(token: str) -> dict:
    """Validate an Auth0 RS256 JWT and return its payload."""
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unable to resolve signing key: {exc}",
        ) from exc

    try:
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=_AUTH0_ALGORITHMS,
            audience=backend_config.auth0_audience,
            issuer=f"https://{backend_config.auth0_domain}/",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from None
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc
    return payload


# ---------------------------------------------------------------------------
# Current-user model
# ---------------------------------------------------------------------------


class CurrentUser(BaseModel):
    """Authenticated user, populated by the auth dependency."""

    id: uuid.UUID
    email: str
    is_invited: bool
    pushover_token: Optional[str] = None


# ---------------------------------------------------------------------------
# Shared admin resolver
# ---------------------------------------------------------------------------


async def _get_or_create_admin_user(session: AsyncSession) -> User:
    """Return the shared admin identity, creating it on first use."""
    result = await session.execute(
        select(User).where(User.email == backend_config.admin_email)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=backend_config.admin_email,
            is_invited=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


def session_signing_key() -> bytes:
    """Derive the cookie key so changing login credentials invalidates sessions."""
    assert backend_config.session_secret is not None
    assert backend_config.login_password is not None
    credentials = f"{backend_config.login_username}\0{backend_config.login_password}"
    return hmac.new(
        backend_config.session_secret.encode(), credentials.encode(), hashlib.sha256
    ).digest()


def verify_session(request: Request) -> None:
    """Validate the signed session and require CSRF proof for state changes."""
    cookie = request.cookies.get("camply_session")
    if not cookie:
        raise HTTPException(status_code=401, detail="Sign in required")
    try:
        payload = jwt.decode(
            cookie,
            session_signing_key(),
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "csrf"]},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=401, detail="Session expired or invalid"
        ) from exc
    if payload["sub"] != backend_config.admin_email:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        token = request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(token.encode(), str(payload["csrf"]).encode()):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")


# ---------------------------------------------------------------------------
# Main dependency
# ---------------------------------------------------------------------------


async def resolve_current_user(
    request: Request,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
    session: SessionDep,
) -> CurrentUser:
    """
    FastAPI dependency that resolves the current authenticated user.

    **none mode**
        Automatically uses the configured admin identity without credentials.

    **session mode**
        Validates the cookie established through the in-app login form.

    **auth0 mode**
        Validates the bearer JWT, looks up (or creates) the user in the
        database, and returns the DB record.
    """
    if backend_config.auto_login or backend_config.auth_mode == AuthMode.SESSION:
        if backend_config.auth_mode == AuthMode.SESSION:
            verify_session(request)
        user = await _get_or_create_admin_user(session)
        return CurrentUser(
            id=user.id,
            email=user.email,
            is_invited=user.is_invited,
            pushover_token=user.pushover_token,
        )

    # --- Auth0 mode ---
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    payload = await _verify_auth0_token(credentials.credentials)
    auth0_id = payload.get("sub", "")
    email = (payload.get("email") or payload.get("sub") or "").lower()

    # Upsert user by auth0_id — handle concurrent insert race
    result = await session.execute(select(User).where(User.auth0_id == auth0_id))
    auth0_user: User | None = result.scalar_one_or_none()
    if auth0_user is None:
        auth0_user = User(
            auth0_id=auth0_id,
            email=email,
            is_invited=False,
        )
        session.add(auth0_user)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            result = await session.execute(
                select(User).where(User.auth0_id == auth0_id)
            )
            auth0_user = result.scalar_one()
        else:
            await session.refresh(auth0_user)

    return CurrentUser(
        id=auth0_user.id,
        email=auth0_user.email,
        is_invited=auth0_user.is_invited,
        pushover_token=auth0_user.pushover_token,
    )


# ---------------------------------------------------------------------------
# Optional invitation guard
# ---------------------------------------------------------------------------


def require_invitation(current_user: CurrentUserDep) -> None:
    """Deny scan access to uninvited users when invite-only access is enabled."""
    if backend_config.invite_only and not current_user.is_invited:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ERR_INVITE_REQUIRED",
                "message": "An invitation is required. Please request access.",
            },
        )


# ---------------------------------------------------------------------------
# Annotated type for FastAPI injection
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[CurrentUser, Depends(resolve_current_user)]
