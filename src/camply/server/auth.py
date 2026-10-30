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
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.models import User
from camply.server.config import AuthMode, backend_config
from camply.server.dependencies import SessionDep
from camply.server.metrics import USERS_CREATED_TOTAL

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
# Password hashing helpers
# ---------------------------------------------------------------------------


PASSWORD_HASH_ALGORITHM: str = "pbkdf2_sha256"
# Identifier used in serialized password hashes.

PASSWORD_HASH_ROUNDS: int = 100_000
# PBKDF2 HMAC SHA-256 derivation rounds.

PASSWORD_HASH_PARTS: int = 3
# Expected number of components in a serialized password hash.


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using PBKDF2-HMAC-SHA256 with a random salt.

    Parameters
    ----------
    password : str
        Plaintext password to hash.

    Returns
    -------
    str
        Formatted string containing algorithm, salt, and derived hash.
    """
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_HASH_ROUNDS
    ).hex()
    return f"{PASSWORD_HASH_ALGORITHM}${salt}${key}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored PBKDF2 hash.

    Parameters
    ----------
    password : str
        Candidate plaintext password.
    hashed : str
        Stored password hash.

    Returns
    -------
    bool
        True if the password matches the hash, False otherwise.
    """
    parts = hashed.split("$")
    if len(parts) != PASSWORD_HASH_PARTS or parts[0] != PASSWORD_HASH_ALGORITHM:
        return False
    salt = parts[1]
    expected_key = parts[2]
    candidate_key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_HASH_ROUNDS
    ).hex()
    return secrets.compare_digest(candidate_key, expected_key)


# ---------------------------------------------------------------------------
# Current-user model
# ---------------------------------------------------------------------------


class CurrentUser(BaseModel):
    """Authenticated user, populated by the auth dependency."""

    id: uuid.UUID
    email: str
    is_invited: bool
    is_admin: bool = False
    scanning_enabled: bool = True
    pushover_token: Optional[str] = None
    must_change_password: bool = False


# ---------------------------------------------------------------------------
# Shared admin resolver
# ---------------------------------------------------------------------------


async def _get_or_create_admin_user(session: AsyncSession) -> User:
    """Return the configured account, restoring admin rights only for automatic login."""
    result = await session.execute(
        select(User).where(User.email == backend_config.admin_email)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=backend_config.admin_email,
            is_invited=True,
            is_admin=True,
            scanning_enabled=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        try:
            USERS_CREATED_TOTAL.inc()
        except Exception:
            pass
    elif backend_config.auto_login and not user.is_admin:
        user.is_admin = True
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


def session_credential_version(user: User) -> str:
    """Bind a cookie to the current salted password hash without exposing that hash."""
    return hmac.new(
        session_signing_key(), (user.password_hash or "").encode(), hashlib.sha256
    ).hexdigest()


def verify_session(request: Request) -> dict:
    """Validate the signed session and require CSRF proof for state changes."""
    cookie = request.cookies.get("camply_session")
    if not cookie:
        raise HTTPException(status_code=401, detail="Sign in required")
    try:
        payload = jwt.decode(
            cookie,
            session_signing_key(),
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "csrf", "credentials"]},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=401, detail="Session expired or invalid"
        ) from exc
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        token = request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(token.encode(), str(payload["csrf"]).encode()):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return payload


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
            payload = verify_session(request)
            sub = str(payload.get("sub", ""))
            stmt = select(User).where(func.lower(User.email) == sub.lower())
            result = await session.execute(stmt)
            db_user = result.scalar_one_or_none()
            if db_user is None:
                raise HTTPException(
                    status_code=401, detail="Session expired or invalid"
                )
            user = db_user
            if not secrets.compare_digest(
                str(payload["credentials"]), session_credential_version(user)
            ):
                raise HTTPException(
                    status_code=401, detail="Session expired or invalid"
                )
        else:
            user = await _get_or_create_admin_user(session)
        return CurrentUser(
            id=user.id,
            email=user.email,
            is_invited=user.is_invited,
            is_admin=user.is_admin,
            scanning_enabled=user.scanning_enabled,
            pushover_token=user.pushover_token,
            must_change_password=(
                backend_config.auth_mode == AuthMode.SESSION
                and user.must_change_password
            ),
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
            is_admin=False,
            scanning_enabled=True,
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
            try:
                USERS_CREATED_TOTAL.inc()
            except Exception:
                pass

    return CurrentUser(
        id=auth0_user.id,
        email=auth0_user.email,
        is_invited=auth0_user.is_invited,
        is_admin=auth0_user.is_admin,
        scanning_enabled=auth0_user.scanning_enabled,
        pushover_token=auth0_user.pushover_token,
        must_change_password=False,
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
# Password change guard
# ---------------------------------------------------------------------------


def require_password_not_expired(current_user: CurrentUserDep) -> None:
    """Deny operations when the user must change their password on first sign in."""
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ERR_PASSWORD_CHANGE_REQUIRED",
                "message": "Password change required before proceeding.",
            },
        )


# ---------------------------------------------------------------------------
# Admin guard
# ---------------------------------------------------------------------------


def require_admin(current_user: CurrentUserDep) -> CurrentUser:
    """Raise 403 if the authenticated user is not an administrator."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ERR_ADMIN_REQUIRED",
                "message": "Administrator access required.",
            },
        )
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ERR_PASSWORD_CHANGE_REQUIRED",
                "message": "Password change required before proceeding.",
            },
        )
    return current_user


# ---------------------------------------------------------------------------
# Annotated types for FastAPI injection
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[CurrentUser, Depends(resolve_current_user)]
AdminUserDep = Annotated[CurrentUser, Depends(require_admin)]
