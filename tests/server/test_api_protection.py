"""Exercise API protection at the real backend entry point."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from camply.notifications.ntfy import NtfyProvider
from camply.server import api_protection
from camply.server.app import app
from camply.server.config import AuthMode, BackendConfig, backend_config
from camply.server.rate_limits import MemoryRateLimits, RateLimitUnavailable

GATEWAY_SECRET = "synthetic-credential-for-api-protection-tests"
GATEWAY_HEADERS = {
    "X-Camply-Proxy-Secret": GATEWAY_SECRET,
    "X-Camply-Client-IP": "192.0.2.1",
}


def test_protected_settings_require_valid_gateway_secret_and_shared_storage() -> None:
    """Reject incomplete hosted configuration before the server starts."""
    for secret in (None, "short", "non-ASCII-œ" * 10, " embedded space " * 4):
        with pytest.raises(ValidationError, match="CAMPLY_API_PROXY_SECRET") as exc:
            BackendConfig(api_proxy_required=True, api_proxy_secret=secret)
        if secret:
            assert secret not in str(exc.value)
    auth = {
        "auth_mode": AuthMode.AUTH0,
        "auth0_domain": "auth.example.test",
        "auth0_audience": "https://api.example.test",
        "auth0_client_id": "synthetic",
    }
    config = BackendConfig(
        api_proxy_required=True, api_proxy_secret=GATEWAY_SECRET, **auth
    )
    assert config.rate_limit_storage == "valkey"
    with pytest.raises(ValidationError, match="Valkey"):
        BackendConfig(
            api_proxy_required=True,
            api_proxy_secret=GATEWAY_SECRET,
            api_rate_limit_storage="memory",
            **auth,
        )
    with pytest.raises(ValidationError, match="CAMPLY_AUTH_MODE"):
        BackendConfig(api_proxy_required=True, api_proxy_secret=GATEWAY_SECRET)


@pytest.fixture
def protected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable gateway enforcement with this test's in-process quota store."""
    monkeypatch.setattr(backend_config, "api_proxy_required", True)
    monkeypatch.setattr(backend_config, "api_proxy_secret", GATEWAY_SECRET)


@pytest.mark.usefixtures("protected")
def test_gateway_gate_covers_api_and_keeps_exact_probes(
    test_client: TestClient,
) -> None:
    """Untrusted requests cannot reach API paths, even on preflight or redirects."""
    for path in (
        "/api",
        "/api/",
        "/api/docs",
        "/api/openapi.json",
        "/api/not-real",
        "/api/ping/",
        "/api/%68ealth/",
    ):
        response = test_client.get(path, follow_redirects=False)
        assert response.status_code == 403
        assert response.headers["Cache-Control"] == "no-store"
    for path in ("/api/ping", "/api/health"):
        assert test_client.get(path).status_code == 200
        assert test_client.head(path).status_code != 403
        assert test_client.post(path).status_code == 403
    assert (
        test_client.options(
            "/api/providers",
            headers={
                "Origin": "https://camply.rocks",
                "Access-Control-Request-Method": "GET",
            },
        ).status_code
        == 403
    )
    assert test_client.get("/api/docs", headers=GATEWAY_HEADERS).status_code == 200
    assert test_client.get("/api/not-real", headers=GATEWAY_HEADERS).status_code == 404


@pytest.mark.usefixtures("protected")
def test_gateway_rejects_invalid_and_duplicate_private_headers(
    test_client: TestClient,
) -> None:
    """A valid user agent or browser origin cannot manufacture transport identity."""
    url = "/api/auth-config"
    for headers in (
        {"Origin": "https://camply.rocks", "CF-Connecting-IP": "192.0.2.1"},
        {"X-Camply-Proxy-Secret": "wrong", "X-Camply-Client-IP": "192.0.2.1"},
        {"X-Camply-Proxy-Secret": GATEWAY_SECRET},
        {**GATEWAY_HEADERS, "X-Camply-Client-IP": "192.0.2.1, 192.0.2.2"},
        {**GATEWAY_HEADERS, "X-Camply-Client-IP": "fe80::1%eth0"},
        [*GATEWAY_HEADERS.items(), ("X-Camply-Proxy-Secret", GATEWAY_SECRET)],
        [*GATEWAY_HEADERS.items(), ("X-Camply-Client-IP", "192.0.2.1")],
    ):
        assert test_client.get(url, headers=headers).status_code == 403
    assert test_client.get(url, headers=GATEWAY_HEADERS).status_code == 200


@pytest.mark.usefixtures("protected")
def test_gateway_credential_does_not_authenticate_a_user(
    monkeypatch: pytest.MonkeyPatch, test_client: TestClient
) -> None:
    """A private operation still requires an authenticated user."""
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.SESSION)
    assert test_client.get("/api/me", headers=GATEWAY_HEADERS).status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "count", "window"),
    [
        ("GET", "/api/auth-config", 240, 60),
        ("GET", "/api/search/map", 120, 60),
        ("GET", "/api/campground/1/synthetic", 120, 60),
        ("GET", "/api/rec-area/1/synthetic", 120, 60),
        ("HEAD", "/api/providers", 120, 60),
        ("GET", "/api/me/sessions", 240, 60),
        ("DELETE", "/api/scans/synthetic", 240, 60),
        ("POST", "/api/login/", 10, 300),
        ("POST", "/api/request-access", 5, 3600),
    ],
)
def test_ip_policy_defaults(method: str, path: str, count: int, window: int) -> None:
    """Preserve the documented scope defaults as route parameters change."""
    policy = api_protection.ip_policy(method, path)
    assert (policy.limit, policy.window) == (count, window)


def test_direct_ip_quota_ignores_forwarding_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing forwarding headers cannot reset a direct client's login budget."""
    monkeypatch.setattr(api_protection, "LOGIN", api_protection.Policy("login", 1, 60))
    client = TestClient(app, client=("192.0.2.1", 1))
    assert client.post("/api/login", json={}).status_code == 422
    response = client.post(
        "/api/login/",
        follow_redirects=False,
        headers={
            **GATEWAY_HEADERS,
            "CF-Connecting-IP": "192.0.2.3",
            "Forwarded": "for=192.0.2.3",
            "X-Forwarded-For": "192.0.2.3",
        },
        json={},
    )
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert response.headers["Cache-Control"] == "no-store"
    other = TestClient(app, client=("192.0.2.2", 1))
    assert other.post("/api/login", json={}).status_code == 422
    assert client.get("/api/auth-config").status_code == 200


@pytest.mark.usefixtures("protected")
def test_gateway_quota_uses_validated_client_ip(
    monkeypatch: pytest.MonkeyPatch, test_client: TestClient
) -> None:
    """The same trusted network identity shares a quota across IP spellings."""
    monkeypatch.setattr(
        api_protection, "GENERAL", api_protection.Policy("general", 1, 60)
    )
    assert (
        test_client.get("/api/auth-config", headers=GATEWAY_HEADERS).status_code == 200
    )
    mapped = {**GATEWAY_HEADERS, "X-Camply-Client-IP": "::ffff:192.0.2.1"}
    assert test_client.get("/api/auth-config", headers=mapped).status_code == 429
    other = {**GATEWAY_HEADERS, "X-Camply-Client-IP": "192.0.2.2"}
    assert test_client.get("/api/auth-config", headers=other).status_code == 200


@pytest.mark.usefixtures("protected")
def test_gateway_ipv6_quota_is_per_network(
    monkeypatch: pytest.MonkeyPatch, test_client: TestClient
) -> None:
    """Changing addresses inside a typical IPv6 client allocation shares quota."""
    monkeypatch.setattr(
        api_protection, "GENERAL", api_protection.Policy("general", 1, 60)
    )
    for address, status in (
        ("2001:db8:0:1::1", 200),
        ("2001:db8:0:1::2", 429),
        ("2001:db8:0:2::1", 200),
    ):
        headers = {**GATEWAY_HEADERS, "X-Camply-Client-IP": address}
        assert (
            test_client.get("/api/auth-config", headers=headers).status_code == status
        )


def test_account_budgets_follow_verified_account_across_networks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Moving networks keeps the account limit and a separate notification quota."""
    monkeypatch.setattr(api_protection, "WRITE", api_protection.Policy("write", 1, 60))
    monkeypatch.setattr(
        api_protection, "TEST_NOTIFICATION", api_protection.Policy("test", 1, 60)
    )
    send_notification = AsyncMock(return_value=True)
    monkeypatch.setattr(NtfyProvider, "send_accepted", send_notification)
    first = TestClient(app, client=("192.0.2.1", 1))
    second = TestClient(app, client=("192.0.2.2", 1))
    assert first.patch("/api/me", json={}).status_code == 200
    assert second.patch("/api/me", json={}).status_code == 429
    assert second.get("/api/me").status_code == 200
    notification = {"notification_provider": "ntfy", "ntfy_topic": "test-quota"}
    assert (
        first.post("/api/me/notifications/test", json=notification).status_code == 200
    )
    assert (
        second.post("/api/me/notifications/test", json=notification).status_code == 429
    )
    send_notification.assert_awaited_once()


def test_provider_sync_budget_precedes_dispatch(
    monkeypatch: pytest.MonkeyPatch, test_client: TestClient
) -> None:
    """A rejected manual sync cannot enqueue more provider work."""
    monkeypatch.setattr(
        api_protection, "PROVIDER_SYNC", api_protection.Policy("provider-sync", 1, 60)
    )
    dispatch = AsyncMock(return_value="synthetic-task")
    monkeypatch.setattr("camply.server.routers.admin.trigger_provider_sync", dispatch)
    endpoint = "/api/admin/operations/sync-providers"
    assert test_client.post(endpoint).status_code == 200
    assert test_client.post(endpoint).status_code == 429
    dispatch.assert_awaited_once()


@pytest.mark.usefixtures("protected")
def test_store_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch, test_client: TestClient
) -> None:
    """Do not execute protected work when counting is unavailable."""

    async def unavailable(*args: object) -> int:
        raise RateLimitUnavailable

    monkeypatch.setattr(MemoryRateLimits, "consume", unavailable)
    response = test_client.get("/api/providers", headers=GATEWAY_HEADERS)
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert response.headers["Cache-Control"] == "no-store"
    assert test_client.get("/api/ping").status_code == 200


def test_declared_and_actual_body_size_are_bounded(test_client: TestClient) -> None:
    """Reject declared oversize before parsing, while ordinary JSON still validates."""
    assert (
        test_client.patch(
            "/api/me", content=b"{}", headers={"Content-Length": "131073"}
        ).status_code
        == 413
    )
    just_fits = b"{}" + b" " * (128 * 1024 - 2)
    assert (
        test_client.patch(
            "/api/me", content=just_fits, headers={"Content-Type": "application/json"}
        ).status_code
        == 200
    )
    response = test_client.patch(
        "/api/me",
        content=just_fits + b" ",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.headers["Cache-Control"] == "no-store"
    assert test_client.patch("/api/me", json=[]).status_code == 422


@pytest.mark.asyncio
async def test_streamed_body_cannot_exceed_limit() -> None:
    """Count bytes across multiple ASGI receives even with no declared size."""

    async def chunks() -> AsyncIterator[bytes]:
        yield b"{}"
        yield b" " * (128 * 1024)

    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.patch(
            "/api/me", content=chunks(), headers={"Content-Type": "application/json"}
        )
    assert response.status_code == 413
