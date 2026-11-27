"""
Authentication utilities for camply-backend.

The instance owner chooses automatic admin login, in-app cookie sessions, or
Auth0 bearer tokens. The environment does not override this choice.
"""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Optional

import httpx2
import jwt
import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt import PyJWKClient
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.models import AccessRequest, User, UserSession
from camply.db.models.access_request import AccessRequestStatus
from camply.server.config import AuthMode, backend_config
from camply.server.dependencies import SessionDep
from camply.server.metrics import USERS_CREATED_TOTAL
from camply.server.services.users import flush_new_user

logger = structlog.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bearer authentication for Auth0 JWTs
# ---------------------------------------------------------------------------

bearer_scheme = HTTPBearer(auto_error=False)
NATIVE_SESSION_AUDIENCE = "camply-native-session"
NATIVE_SESSION_TOKEN_HEADER = "X-Camply-Session-Token"

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
        _jwks_client_cache[domain] = PyJWKClient(jwks_url, timeout=10.0)
    return _jwks_client_cache[domain]


async def _verify_auth0_token(token: str) -> dict:
    """
    Validate an Auth0 RS256 JWT and return its payload.

    Parameters
    ----------
    token : str
        Bearer token presented by the client.

    Returns
    -------
    dict
        Verified claims; ``exp`` and a nonempty string ``sub`` are guaranteed.

    Raises
    ------
    HTTPException
        401 when the credentials are invalid, expired, or unverifiable; 503
        when the JWKS endpoint is unreachable or returns unusable data, so
        clients can retry instead of treating a valid session as rejected.
    """
    try:
        jwks_client = _get_jwks_client()
        signing_key = await asyncio.to_thread(
            jwks_client.get_signing_key_from_jwt, token
        )
    except (jwt.PyJWKClientConnectionError, jwt.PyJWKSetError, json.JSONDecodeError):
        logger.warning("auth0_jwks_unavailable", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify credentials right now. Please retry shortly.",
        ) from None
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
            options={"require": ["exp", "sub", "iss", "aud"]},
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
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )
    return payload


# ---------------------------------------------------------------------------
# Auth0 userinfo fetching & caching
# ---------------------------------------------------------------------------


@dataclass
class _UserInfoCacheEntry:
    """In-memory cache entry for Auth0 /userinfo claims."""

    claims: dict[str, Any]
    expires_at: float


_userinfo_cache: dict[str, _UserInfoCacheEntry] = {}
_USERINFO_CACHE_TTL: float = 600.0  # 10 minutes
_USERINFO_MAX_ENTRIES: int = 1000
_userinfo_transport: httpx2.AsyncBaseTransport | None = None


def _cache_userinfo(token_hash: str, claims: dict[str, Any]) -> None:
    """
    Store claims in the in-memory userinfo cache with bounded size and TTL.

    Parameters
    ----------
    token_hash : str
        SHA-256 digest of the bearer token.
    claims : dict[str, Any]
        User profile claims from /userinfo.
    """
    now = time.monotonic()
    if len(_userinfo_cache) >= _USERINFO_MAX_ENTRIES:
        expired = [k for k, v in _userinfo_cache.items() if v.expires_at <= now]
        for k in expired:
            del _userinfo_cache[k]
        while len(_userinfo_cache) >= _USERINFO_MAX_ENTRIES:
            del _userinfo_cache[next(iter(_userinfo_cache))]
    _userinfo_cache[token_hash] = _UserInfoCacheEntry(
        claims=claims, expires_at=now + _USERINFO_CACHE_TTL
    )


def _get_cached_userinfo(token_hash: str) -> dict[str, Any] | None:
    """
    Retrieve claims from userinfo cache if present and unexpired.

    Parameters
    ----------
    token_hash : str
        SHA-256 digest of the bearer token.

    Returns
    -------
    dict[str, Any] | None
        Cached claims if available and valid, otherwise None.
    """
    entry = _userinfo_cache.get(token_hash)
    if entry is None:
        return None
    if time.monotonic() > entry.expires_at:
        del _userinfo_cache[token_hash]
        return None
    return entry.claims


async def _fetch_userinfo(token: str) -> dict[str, Any]:
    """
    Fetch user claims from the Auth0 /userinfo endpoint.

    Parameters
    ----------
    token : str
        Bearer access token presented by the client.

    Returns
    -------
    dict[str, Any]
        Userinfo claims dictionary.

    Raises
    ------
    HTTPException
        401 when the token is rejected by userinfo; 503 when the endpoint
        experiences a network or server error.
    """
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    cached = _get_cached_userinfo(token_hash)
    if cached is not None:
        return cached

    domain = backend_config.auth0_domain
    if not domain:
        return {}
    url = f"https://{domain}/userinfo"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx2.AsyncClient(
            timeout=10.0, transport=_userinfo_transport
        ) as client:
            resp = await client.get(url, headers=headers)
    except (httpx2.RequestError, TimeoutError):
        logger.warning("auth0_userinfo_unavailable", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify user profile right now. Please retry shortly.",
        ) from None

    if resp.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token for userinfo",
        )
    if resp.status_code != status.HTTP_200_OK:
        logger.warning(
            "auth0_userinfo_http_error",
            status_code=resp.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify user profile right now. Please retry shortly.",
        )

    try:
        data = resp.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify user profile right now. Please retry shortly.",
        ) from None

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify user profile right now. Please retry shortly.",
        )

    _cache_userinfo(token_hash=token_hash, claims=data)
    return data


async def _resolve_verified_email(payload: dict[str, Any], token: str) -> str | None:
    """
    Extract and verify the user's email from JWT claims or Auth0 /userinfo.

    Parameters
    ----------
    payload : dict[str, Any]
        Decoded JWT claims.
    token : str
        Raw bearer token presented by the client.

    Returns
    -------
    str | None
        Normalized lowercased email address if verified, or None.

    Raises
    ------
    HTTPException
        503 if /userinfo cannot be reached during fallback.
    """
    email_claim = payload.get("email") or payload.get("https://camply/email")
    verified_claim = payload.get("email_verified")
    if verified_claim is None:
        verified_claim = payload.get("https://camply/email_verified")

    # If the token directly contains a verified email, trust it without userinfo call.
    if isinstance(email_claim, str) and email_claim.strip() and verified_claim is True:
        return email_claim.strip().lower()

    # Otherwise, fall back to /userinfo.
    userinfo = await _fetch_userinfo(token=token)
    u_email = userinfo.get("email") or userinfo.get("https://camply/email")
    u_verified = userinfo.get("email_verified")
    if u_verified is None:
        u_verified = userinfo.get("https://camply/email_verified")

    if isinstance(u_email, str) and u_email.strip() and u_verified is True:
        return u_email.strip().lower()

    return None


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
    notification_provider: Literal["pushover", "ntfy"] = "pushover"
    ntfy_topic: str | None = None
    ntfy_server_url: str | None = None
    ntfy_access_token: str | None = Field(default=None, repr=False)
    must_change_password: bool = False
    session_id: uuid.UUID | None = None
    native_session: bool = False


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
        await flush_new_user(session, user)
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


def _as_utc(value: datetime.datetime) -> datetime.datetime:
    """Normalize naive SQLite timestamps to UTC-aware datetimes."""
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc)


def verify_session(request: Request, bearer: str | None = None) -> dict:
    """Validate the session transport and require CSRF proof for cookie mutations."""
    token = bearer if bearer is not None else request.cookies.get("camply_session")
    if not token:
        raise HTTPException(status_code=401, detail="Sign in required")
    required = ["exp", "sub", "credentials", "jti"]
    if bearer is None:
        required.append("csrf")
    try:
        payload = jwt.decode(
            token,
            session_signing_key(),
            algorithms=["HS256"],
            audience=NATIVE_SESSION_AUDIENCE if bearer is not None else None,
            options={"require": required},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=401, detail="Session expired or invalid"
        ) from exc
    jti = payload.get("jti")
    if not isinstance(jti, str):
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    try:
        uuid.UUID(jti)
    except ValueError as exc:
        raise HTTPException(
            status_code=401, detail="Session expired or invalid"
        ) from exc
    if bearer is None and request.method not in {"GET", "HEAD", "OPTIONS"}:
        token = request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(token.encode(), str(payload["csrf"]).encode()):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return payload


# ---------------------------------------------------------------------------
# Auth0 user resolver
# ---------------------------------------------------------------------------


async def _match_approved_request_on_email_change(
    session: AsyncSession,
    auth0_user: User,
    previous_email: str,
    new_verified_email: str,
) -> None:
    """
    Apply an unclaimed approved request on verified email change unless revoked.

    Parameters
    ----------
    session : AsyncSession
        Active database session.
    auth0_user : User
        Existing uninvited user whose verified email is updating.
    previous_email : str
        Normalized previous email address before the update.
    new_verified_email : str
        Normalized new verified email address.
    """
    has_rejected_request = await session.scalar(
        select(AccessRequest.id)
        .where(
            AccessRequest.status == AccessRequestStatus.REJECTED.value,
            or_(
                AccessRequest.user_id == auth0_user.id,
                func.lower(AccessRequest.email) == previous_email,
            ),
        )
        .limit(1)
    )
    if has_rejected_request is not None:
        return

    approved_request = (
        await session.execute(
            select(AccessRequest).where(
                func.lower(AccessRequest.email) == new_verified_email.lower(),
                AccessRequest.user_id.is_(None),
                AccessRequest.status == AccessRequestStatus.APPROVED.value,
            )
        )
    ).scalar_one_or_none()
    if approved_request is not None:
        auth0_user.is_invited = True
        approved_request.user_id = auth0_user.id


async def _match_access_request_on_provision(
    session: AsyncSession,
    auth0_user: User,
    verified_email: str,
) -> None:
    """
    Link a newly provisioned user to any matching access request.

    Parameters
    ----------
    session : AsyncSession
        Active database session after flushing the new user.
    auth0_user : User
        Newly flushed user instance with a populated ``id``.
    verified_email : str
        Verified email address from Auth0 claims or userinfo.
    """
    access_request = (
        await session.execute(
            select(AccessRequest).where(
                func.lower(AccessRequest.email) == verified_email.lower()
            )
        )
    ).scalar_one_or_none()
    if access_request is None:
        return

    if access_request.status == AccessRequestStatus.APPROVED.value:
        if access_request.user_id is None:
            auth0_user.is_invited = True
            access_request.user_id = auth0_user.id
    elif (
        access_request.status
        in {
            AccessRequestStatus.PENDING.value,
            AccessRequestStatus.REJECTED.value,
        }
        and access_request.user_id is None
    ):
        access_request.user_id = auth0_user.id


async def _sync_existing_auth0_user_email(
    session: AsyncSession,
    auth0_user: User,
    verified_email: str | None,
) -> User:
    """
    Synchronize verified email changes for an existing Auth0 user.

    Parameters
    ----------
    session : AsyncSession
        Active database session.
    auth0_user : User
        Existing user model instance.
    verified_email : str or None
        Normalized verified email from token or userinfo.

    Returns
    -------
    User
        Updated user instance.

    Raises
    ------
    HTTPException
        409 if the updated email is claimed by another user account.
    """
    if verified_email is None or verified_email == auth0_user.email.lower():
        return auth0_user

    conflict = await session.execute(
        select(User).where(
            func.lower(User.email) == verified_email,
            User.id != auth0_user.id,
        )
    )
    if conflict.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "ERR_EMAIL_CONFLICT",
                "message": "An account with this email address already exists.",
            },
        )
    previous_email = auth0_user.email.lower()
    auth0_user.email = verified_email
    if not auth0_user.is_invited:
        await _match_approved_request_on_email_change(
            session=session,
            auth0_user=auth0_user,
            previous_email=previous_email,
            new_verified_email=verified_email,
        )
    try:
        await session.commit()
        await session.refresh(auth0_user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "ERR_EMAIL_CONFLICT",
                "message": "An account with this email address already exists.",
            },
        ) from None
    return auth0_user


async def _provision_auth0_user(
    session: AsyncSession,
    auth0_id: str,
    verified_email: str | None,
) -> User:
    """
    Provision a new user record for a first-time Auth0 login.

    Parameters
    ----------
    session : AsyncSession
        Active database session.
    auth0_id : str
        Auth0 identity subject identifier.
    verified_email : str or None
        Normalized verified email from token or userinfo.

    Returns
    -------
    User
        Newly provisioned user instance.

    Raises
    ------
    HTTPException
        403 if a verified email is missing;
        409 if the verified email is claimed by an existing account.
    """
    if verified_email is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ERR_VERIFIED_EMAIL_REQUIRED",
                "message": "A verified email address is required to access camply.",
            },
        )

    conflict = await session.execute(
        select(User).where(func.lower(User.email) == verified_email)
    )
    if conflict.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "ERR_EMAIL_CONFLICT",
                "message": "An account with this email address already exists.",
            },
        )

    auth0_user = User(
        auth0_id=auth0_id,
        email=verified_email,
        is_invited=False,
        is_admin=False,
        scanning_enabled=True,
    )
    try:
        await flush_new_user(session, auth0_user)
        await _match_access_request_on_provision(
            session=session,
            auth0_user=auth0_user,
            verified_email=verified_email,
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        result = await session.execute(select(User).where(User.auth0_id == auth0_id))
        winner = result.scalar_one_or_none()
        if winner is not None:
            return winner
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "ERR_EMAIL_CONFLICT",
                "message": "An account with this email address already exists.",
            },
        ) from None
    else:
        await session.refresh(auth0_user)
        try:
            USERS_CREATED_TOTAL.inc()
        except Exception:
            pass
        return auth0_user


async def _resolve_auth0_user(
    credentials: Optional[HTTPAuthorizationCredentials],
    session: AsyncSession,
) -> User:
    """
    Validate bearer token, synchronize email changes, or provision a new user.

    Parameters
    ----------
    credentials : HTTPAuthorizationCredentials or None
        Bearer authorization credentials.
    session : AsyncSession
        Active database session.

    Returns
    -------
    User
        Persisted user record corresponding to the Auth0 identity.

    Raises
    ------
    HTTPException
        401 if missing credentials or invalid token;
        403 if verified email is required for provisioning;
        409 on duplicate email conflict;
        503 if identity provider services are unreachable.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    payload = await _verify_auth0_token(credentials.credentials)
    auth0_id = payload.get("sub", "")
    token = credentials.credentials

    # Look up existing user by auth0_id
    result = await session.execute(select(User).where(User.auth0_id == auth0_id))
    auth0_user: User | None = result.scalar_one_or_none()

    verified_email = await _resolve_verified_email(payload=payload, token=token)

    if auth0_user is not None:
        return await _sync_existing_auth0_user_email(
            session=session,
            auth0_user=auth0_user,
            verified_email=verified_email,
        )

    return await _provision_auth0_user(
        session=session,
        auth0_id=auth0_id,
        verified_email=verified_email,
    )


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
        Validates the browser cookie or native bearer established by password login.

    **auth0 mode**
        Validates the bearer JWT, looks up (or creates) the user in the
        database, and returns the DB record.
    """
    if backend_config.auto_login or backend_config.auth_mode == AuthMode.SESSION:
        session_id: uuid.UUID | None = None
        if backend_config.auth_mode == AuthMode.SESSION:
            payload = verify_session(
                request, credentials.credentials if credentials is not None else None
            )
            sub = str(payload.get("sub", ""))
            jti_uuid = uuid.UUID(str(payload["jti"]))
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
            session_stmt = select(UserSession).where(
                UserSession.id == jti_uuid,
                UserSession.user_id == user.id,
            )
            db_session = (await session.execute(session_stmt)).scalar_one_or_none()
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            if (
                db_session is None
                or db_session.revoked_at is not None
                or _as_utc(db_session.expires_at) <= now
            ):
                raise HTTPException(
                    status_code=401, detail="Session expired or invalid"
                )
            session_id = db_session.id
        else:
            user = await _get_or_create_admin_user(session)
        return CurrentUser(
            id=user.id,
            email=user.email,
            is_invited=user.is_invited,
            is_admin=user.is_admin,
            scanning_enabled=user.scanning_enabled,
            pushover_token=user.pushover_token,
            notification_provider=user.notification_provider,
            ntfy_topic=user.ntfy_topic,
            ntfy_server_url=user.ntfy_server_url,
            ntfy_access_token=user.ntfy_access_token,
            must_change_password=(
                backend_config.auth_mode == AuthMode.SESSION
                and user.must_change_password
            ),
            session_id=session_id,
            native_session=session_id is not None and credentials is not None,
        )

    # --- Auth0 mode ---
    auth0_user = await _resolve_auth0_user(credentials=credentials, session=session)
    return CurrentUser(
        id=auth0_user.id,
        email=auth0_user.email,
        is_invited=auth0_user.is_invited,
        is_admin=auth0_user.is_admin,
        scanning_enabled=auth0_user.scanning_enabled,
        pushover_token=auth0_user.pushover_token,
        notification_provider=auth0_user.notification_provider,
        ntfy_topic=auth0_user.ntfy_topic,
        ntfy_server_url=auth0_user.ntfy_server_url,
        ntfy_access_token=auth0_user.ntfy_access_token,
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
