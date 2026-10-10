"""Regression tests for owner-selected cookie sessions and automatic login."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.config import AuthMode, BackendConfig, backend_config


@pytest.fixture
def session_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Configure synthetic shared credentials and an HTTP test session."""
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.SESSION)
    monkeypatch.setattr(backend_config, "login_username", "test-admin")
    monkeypatch.setattr(backend_config, "login_password", "synthetic-test-password")
    monkeypatch.setattr(
        backend_config, "session_secret", "synthetic-session-secret-with-32-characters"
    )
    monkeypatch.setattr(backend_config, "session_cookie_secure", False)
    yield


def _login(client: TestClient) -> None:
    """Sign in through JSON credentials and set the session's CSRF header."""
    response = client.post(
        "/api/login",
        json={"username": "test-admin", "password": "synthetic-test-password"},
    )
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = client.cookies["camply_csrf"]


def test_session_login_logout(session_mode: None, test_client: TestClient) -> None:
    """The in-app login persists across requests and logout clears both cookies."""
    assert test_client.get("/api/me").status_code == 401
    _login(test_client)
    assert test_client.get("/api/me").status_code == 200
    response = test_client.post("/api/logout")
    assert response.status_code == 204
    assert test_client.get("/api/me").status_code == 401


def test_session_rejects_invalid_credentials(
    session_mode: None, test_client: TestClient
) -> None:
    """Invalid credentials return an app error with no Basic challenge or cookie."""
    response = test_client.post(
        "/api/login", json={"username": "test-admin", "password": "wrong"}
    )
    assert response.status_code == 401
    assert "www-authenticate" not in response.headers
    assert "camply_session" not in test_client.cookies


def test_session_cookie_flags(
    session_mode: None, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The session cookie is HTTP-only, same-site, bounded, and secure when configured."""
    monkeypatch.setattr(backend_config, "session_cookie_secure", True)
    response = test_client.post(
        "/api/login",
        json={"username": "test-admin", "password": "synthetic-test-password"},
    )
    cookie = response.headers.get_list("set-cookie")[0].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "secure" in cookie
    assert "max-age=" in cookie


def test_session_requires_csrf_for_mutations(
    session_mode: None, test_client: TestClient
) -> None:
    """Cookie-authenticated mutations require the CSRF token from the signed session."""
    _login(test_client)
    del test_client.headers["X-CSRF-Token"]
    assert (
        test_client.patch(
            "/api/me", json={"pushover_token": "synthetic-key"}
        ).status_code
        == 403
    )
    test_client.headers["X-CSRF-Token"] = "wrong-token"
    assert test_client.post("/api/logout").status_code == 403
    test_client.headers["X-CSRF-Token"] = test_client.cookies["camply_csrf"]
    assert (
        test_client.patch(
            "/api/me", json={"pushover_token": "synthetic-key"}
        ).status_code
        == 200
    )


def test_session_tampering_and_expiry(
    session_mode: None, test_client: TestClient
) -> None:
    """Forged and expired session cookies cannot resolve a current user."""
    test_client.cookies.set("camply_session", "forged")
    assert test_client.get("/api/me").status_code == 401
    test_client.cookies.clear()
    with patch("backend.routers.sessions.time.time", return_value=1):
        _login(test_client)
    assert test_client.get("/api/me").status_code == 401


def test_session_invalidates_after_password_change(
    session_mode: None, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing the configured password invalidates existing signed sessions."""
    _login(test_client)
    monkeypatch.setattr(
        backend_config, "login_password", "replacement-synthetic-password"
    )
    assert test_client.get("/api/me").status_code == 401


def test_login_rejects_untrusted_origin(
    session_mode: None, test_client: TestClient
) -> None:
    """A foreign website cannot start a password session in the browser."""
    response = test_client.post(
        "/api/login",
        headers={"Origin": "https://untrusted.example.com"},
        json={"username": "test-admin", "password": "synthetic-test-password"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:5173", "http://100.85.12.34:5173", "https://camply.ts.net"],
)
def test_login_accepts_cors_origins(
    session_mode: None, test_client: TestClient, origin: str
) -> None:
    """Password login accepts the same explicit and regex origins as CORS."""
    response = test_client.post(
        "/api/login",
        headers={"Origin": origin},
        json={"username": "test-admin", "password": "synthetic-test-password"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("environment", ["local", "production"])
def test_explicit_auto_login_ignores_environment(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    """The selected auth mode, rather than environment, controls automatic login."""
    monkeypatch.setattr(backend_config, "environment", environment)
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.NONE)
    assert test_client.get("/api/me").status_code == 200


def test_auth0_in_local_environment_still_requires_login(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Choosing Auth0 is honored even while running in a local environment."""
    monkeypatch.setattr(backend_config, "environment", "local")
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.AUTH0)
    assert test_client.get("/api/me").status_code == 401


@pytest.mark.parametrize(
    "missing", ["login_username", "login_password", "session_secret"]
)
def test_session_requires_complete_configuration(missing: str) -> None:
    """Session mode cannot start with missing shared credentials or signing keys."""
    from pydantic import ValidationError

    values = {
        "auth_mode": "session",
        "login_username": "test-admin",
        "login_password": "synthetic-password",
        "session_secret": "synthetic-secret-with-at-least-32-characters",
        missing: None,
    }
    with pytest.raises(ValidationError):
        BackendConfig.model_validate(values)


def test_password_login_disabled_in_other_modes(test_client: TestClient) -> None:
    """Automatic login does not expose an unused password-login flow."""
    response = test_client.post(
        "/api/login", json={"username": "test-admin", "password": "synthetic-password"}
    )
    assert response.status_code == 404
