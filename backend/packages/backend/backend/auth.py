"""
Authentication utilities for camply-backend.

Supports two modes:
  * ``AUTH_MODE=local`` — simple email-based identity suitable for self-hosters.
  * ``AUTH_MODE=auth0`` — Auth0 JWT validation for the community SaaS tier.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import AuthMode, backend_config
from backend.dependencies import SessionDep
from db.models import User

logger = structlog.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bearer-token scheme — works for both Auth0 JWTs and local session tokens
# ---------------------------------------------------------------------------

bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Auth0 helpers
# ---------------------------------------------------------------------------

_AUTH0_ALGORITHMS = ["RS256"]


async def _verify_auth0_token(token: str) -> dict:
    """Validate an Auth0 RS256 JWT and return its payload.

    Note: ``PyJWT``'s ``PyJWKClient`` would normally handle caching;
    we keep a simple in-memory cache for clarity.
    """
    import jwt
    from jwt import PyJWKClient

    jwks_url = f"https://{backend_config.auth0_domain}/.well-known/jwks.json"
    try:
        jwks_client = PyJWKClient(jwks_url, cache_keys=True)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
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
    is_early_access_user: bool
    pushover_token: Optional[str] = None


# ---------------------------------------------------------------------------
# Local-mode user resolver
# ---------------------------------------------------------------------------


async def _get_or_create_local_user(session: AsyncSession) -> User:
    """Return the admin user in local mode — create on first call."""
    result = await session.execute(
        select(User).where(User.email == backend_config.admin_email)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=backend_config.admin_email,
            is_early_access_user=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Main dependency
# ---------------------------------------------------------------------------


async def resolve_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
    session: SessionDep,
) -> CurrentUser:
    """
    FastAPI dependency that resolves the current authenticated user.

    **local mode**
        Returns a synthetic user derived from the configured ``ADMIN_EMAIL``.
        No bearer token is required.

    **auth0 mode**
        Validates the bearer JWT, looks up (or creates) the user in the
        database, and returns the DB record.
    """
    if backend_config.auth_mode == AuthMode.LOCAL:
        user = await _get_or_create_local_user(session)
        return CurrentUser(
            id=user.id,
            email=user.email,
            is_early_access_user=user.is_early_access_user,
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

    # Upsert user by auth0_id
    result = await session.execute(
        select(User).where(User.auth0_id == auth0_id)
    )
    auth0_user: User | None = result.scalar_one_or_none()
    if auth0_user is None:
        auth0_user = User(
            auth0_id=auth0_id,
            email=email,
            is_early_access_user=False,
        )
        session.add(auth0_user)
        await session.commit()
        await session.refresh(auth0_user)

    return CurrentUser(
        id=auth0_user.id,
        email=auth0_user.email,
        is_early_access_user=auth0_user.is_early_access_user,
        pushover_token=auth0_user.pushover_token,
    )


# ---------------------------------------------------------------------------
# Annotated type for FastAPI injection
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[CurrentUser, Depends(resolve_current_user)]
