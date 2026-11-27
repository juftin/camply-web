"""Protect data and expensive work at the API boundary."""

import hmac
from ipaddress import IPv4Address, IPv6Address, IPv6Network, ip_address
from uuid import UUID

from fastapi import HTTPException, Request
from starlette._utils import get_route_path
from starlette.datastructures import Headers
from starlette.requests import ClientDisconnect
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from camply.server.config import BackendConfig
from camply.server.rate_limits import Policy, RateLimits, RateLimitUnavailable

PROXY_SECRET_HEADER = "x-camply-proxy-secret"
PROXY_CLIENT_IP_HEADER = "x-camply-client-ip"
_PRIVATE_HEADERS = {PROXY_SECRET_HEADER.encode(), PROXY_CLIENT_IP_HEADER.encode()}
_PROBES = {"/api/ping", "/api/health"}
_READ_METHODS = {"GET", "HEAD"}
_WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
_PRIVATE_RESOURCES = {"admin", "change-password", "logout", "me", "scans"}
_DISCOVERY_RESOURCES = {"campground", "provider", "providers", "rec-area", "search"}
MAX_BODY_BYTES = 128 * 1024

GENERAL = Policy("general", 240, 60)
DISCOVERY = Policy("discovery", 120, 60)
PRE_AUTH = Policy("pre-auth", 240, 60)
LOGIN = Policy("login", 10, 300)
REQUEST_ACCESS = Policy("request-access", 5, 3600)
WRITE = Policy("write", 30, 60)
TEST_NOTIFICATION = Policy("test-notification", 3, 600)
PROVIDER_SYNC = Policy("provider-sync", 3, 600)


def ip_policy(method: str, path: str) -> Policy:
    """Group API requests by operation without using caller-controlled keys."""
    path = path.rstrip("/")
    resource = path.removeprefix("/api/").partition("/")[0]
    if method == "POST":
        if path == "/api/login":
            return LOGIN
        if path == "/api/request-access":
            return REQUEST_ACCESS
    if resource in _PRIVATE_RESOURCES:
        return PRE_AUTH
    if resource in _DISCOVERY_RESOURCES and method in _READ_METHODS:
        return DISCOVERY
    return GENERAL


def _canonical_ip(value: str) -> IPv4Address | IPv6Address | None:
    """Accept one IP literal and normalize IPv4-mapped IPv6."""
    if "%" in value:
        return None
    try:
        address = ip_address(value)
    except ValueError:
        return None
    if isinstance(address, IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def _client_ip(
    request: Request, headers: Headers, config: BackendConfig
) -> IPv4Address | IPv6Address | None:
    if not config.api_proxy_required:
        return _canonical_ip(request.client.host) if request.client else None
    secrets = headers.getlist(PROXY_SECRET_HEADER)
    addresses = headers.getlist(PROXY_CLIENT_IP_HEADER)
    expected = (config.api_proxy_secret or "").encode()
    if (
        expected
        and len(secrets) == len(addresses) == 1
        and hmac.compare_digest(expected, secrets[0].encode("latin-1"))
    ):
        if address := _canonical_ip(addresses[0]):
            return address
    raise HTTPException(
        status_code=403,
        detail="API access denied",
        headers={"Cache-Control": "no-store"},
    )


async def _enforce_quota(store: RateLimits, policy: Policy, subject: str) -> None:
    try:
        wait = await store.consume(policy, subject)
    except RateLimitUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="API temporarily unavailable",
            headers={"Retry-After": "5", "Cache-Control": "no-store"},
        ) from exc
    if wait:
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": str(wait), "Cache-Control": "no-store"},
        )


async def enforce_account_quota(
    request: Request, user_id: UUID, *, is_admin: bool
) -> None:
    """Bound authenticated writes and side effects by verified account ID."""
    if request.method not in _WRITE_METHODS:
        return
    path = get_route_path(request.scope).rstrip("/")
    if path.startswith("/api/admin/") and not is_admin:
        return
    policy = WRITE
    if request.method == "POST":
        if path == "/api/me/notifications/test":
            policy = TEST_NOTIFICATION
        elif path == "/api/admin/operations/sync-providers":
            policy = PROVIDER_SYNC
    await _enforce_quota(request.app.state.api_rate_limits, policy, str(user_id))


async def _read_body(request: Request) -> bytes:
    """Check the declared size and actual body before any application parsing."""
    try:
        declared_size = int(request.headers.get("content-length", "0"))
    except ValueError:
        declared_size = 0
    too_large = HTTPException(
        status_code=413,
        detail="Request body exceeds 128 KiB",
        headers={"Cache-Control": "no-store"},
    )
    if declared_size > MAX_BODY_BYTES:
        raise too_large
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            raise too_large
        body.extend(chunk)
    return bytes(body)


class ApiProtectionMiddleware:
    """Authenticate hosted transport, limit request rate, and bound API bodies."""

    def __init__(self, app: ASGIApp, config: BackendConfig) -> None:
        self.app = app
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        scope["headers"] = [
            (key, value) for key, value in headers.raw if key not in _PRIVATE_HEADERS
        ]
        path = get_route_path(scope)
        method = scope["method"]
        if (path != "/api" and not path.startswith("/api/")) or (
            path in _PROBES and method in _READ_METHODS
        ):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        try:
            address = _client_ip(request, headers, self.config)
            request.state.camply_client_ip = (
                str(address) if address is not None else None
            )
            subject = (
                str(IPv6Network((address, 64), strict=False))
                if isinstance(address, IPv6Address)
                else str(address or "unknown")
            )
            await _enforce_quota(
                request.app.state.api_rate_limits, ip_policy(method, path), subject
            )
            body: bytes | None = await _read_body(request)
        except ClientDisconnect:
            return
        except HTTPException as exc:
            response = JSONResponse(
                {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
            )
            await response(scope, receive, send)
            return

        async def replay_body() -> Message:
            nonlocal body
            if body is None:
                return await receive()
            message: Message = {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }
            body = None
            return message

        await self.app(scope, replay_body, send)
