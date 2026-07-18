"""
Tests for the ``/api/me`` endpoint and auth resolution.

These use FastAPI's synchronous ``TestClient`` which wraps async endpoints.
The default DB is an SQLite file configured by the environment.
"""

import base64
import uuid
from typing import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.auth import AuthMode

# Default Basic Auth credentials matching config defaults
_BASIC_AUTH = {"Authorization": f"Basic {base64.b64encode(b'admin:camply').decode()}"}

# ---------------------------------------------------------------------------
# Helpers — synthetic JWT payload used when mocking token verification
# ---------------------------------------------------------------------------

_FAKE_AUTH0_SUB = "auth0|63abc123def456"
_FAKE_AUTH0_EMAIL = "testuser@example.com"


def _fake_auth0_payload() -> dict:
    return {
        "sub": _FAKE_AUTH0_SUB,
        "email": _FAKE_AUTH0_EMAIL,
        "iss": "https://camply-test.us.auth0.com/",
        "aud": "https://api.camply.juftin.dev",
    }


# ---------------------------------------------------------------------------
# Fixtures — switch to Auth0 mode and optionally mock token verification
# ---------------------------------------------------------------------------


@pytest.fixture
def auth0_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Override ``CAMPLY_AUTH_MODE`` to ``auth0`` for the test scope."""
    monkeypatch.setattr(
        "backend.auth.backend_config.auth_mode",
        AuthMode.AUTH0,
    )


@pytest.fixture
def mock_auth0_verify() -> Generator[dict, None, None]:
    """Mock ``_verify_auth0_token`` so tests don't need real Auth0 keys."""
    payload = _fake_auth0_payload()
    patcher = patch(
        "backend.auth._verify_auth0_token",
        new=AsyncMock(return_value=payload),
    )
    patcher.start()
    try:
        yield payload
    finally:
        patcher.stop()


# ===========================================================================
# Basic-mode tests (default)
# ===========================================================================


class TestBasicAuth:
    """Tests for Basic auth credential validation."""

    def test_missing_credentials_returns_401(self, test_client: TestClient) -> None:
        """A request without Basic auth should return 401."""
        response = test_client.get("/api/me")
        assert response.status_code == 401

    def test_invalid_credentials_returns_401(self, test_client: TestClient) -> None:
        """Invalid username/password should return 401."""
        response = test_client.get(
            "/api/me",
            headers={
                "Authorization": f"Basic {base64.b64encode(b'wrong:creds').decode()}"
            },
        )
        assert response.status_code == 401


class TestMeEndpoint:
    """Tests for GET/PATCH /api/me."""

    def test_get_me_basic_mode(self, test_client: TestClient) -> None:
        """Basic mode with valid credentials should return the admin user."""
        response = test_client.get("/api/me", headers=_BASIC_AUTH)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["email"] == "admin@camply.local"
        assert data["is_early_access_user"] is True

    def test_patch_me_pushover_token(self, test_client: TestClient) -> None:
        """PATCH /api/me should update pushover_token."""
        response = test_client.patch(
            "/api/me",
            json={"pushover_token": "test_token_abc123"},
            headers=_BASIC_AUTH,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pushover_token"] == "test_token_abc123"

    def test_patch_me_clear_pushover(self, test_client: TestClient) -> None:
        """PATCH /api/me with null should clear the token."""
        set_resp = test_client.patch(
            "/api/me",
            json={"pushover_token": "temp_token"},
            headers=_BASIC_AUTH,
        )
        assert set_resp.status_code == 200
        assert set_resp.json()["pushover_token"] == "temp_token"

        clear_resp = test_client.patch(
            "/api/me",
            json={"pushover_token": None},
            headers=_BASIC_AUTH,
        )
        assert clear_resp.status_code == 200
        assert clear_resp.json()["pushover_token"] is None


class TestProvidersEndpoint:
    """Tests for GET /api/providers."""

    def test_list_providers(self, test_client: TestClient) -> None:
        """Should return a list of providers."""
        response = test_client.get("/api/providers", headers=_BASIC_AUTH)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ===========================================================================
# Auth0-mode tests
# ===========================================================================


class TestAuth0Mode:
    """Tests for Auth0 JWT authentication."""

    def test_auth0_missing_header_returns_401(
        self,
        auth0_mode: None,
        test_client: TestClient,
    ) -> None:
        """Auth0 mode without a bearer token should return 401."""
        response = test_client.get("/api/me")
        assert response.status_code == 401
        detail = response.json().get("detail", "")
        assert "Missing Authorization header" in detail

    def test_auth0_invalid_token_returns_401(
        self,
        auth0_mode: None,
        test_client: TestClient,
    ) -> None:
        """An invalid or malformed JWT should return 401."""
        response = test_client.get(
            "/api/me",
            headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
        )
        assert response.status_code == 401

    def test_auth0_valid_token_returns_user(
        self,
        auth0_mode: None,
        mock_auth0_verify: dict,
        test_client: TestClient,
    ) -> None:
        """A valid (mocked) Auth0 JWT should return the user profile."""
        response = test_client.get(
            "/api/me",
            headers={"Authorization": "Bearer valid_mocked_token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == _FAKE_AUTH0_EMAIL
        assert isinstance(uuid.UUID(data["id"]), uuid.UUID)
        # New Auth0 users should not be early-access by default
        assert data["is_early_access_user"] is False

    def test_auth0_upserts_user(
        self,
        auth0_mode: None,
        mock_auth0_verify: dict,
        test_client: TestClient,
    ) -> None:
        """
        Auth0 mode should create a DB user on first login and
        return the same user on subsequent requests (upsert).
        """
        # First call — creates the user
        resp1 = test_client.get(
            "/api/me",
            headers={"Authorization": "Bearer first_token"},
        )
        assert resp1.status_code == 200
        user_id_1 = resp1.json()["id"]
        assert resp1.json()["email"] == _FAKE_AUTH0_EMAIL

        # Second call — should reuse the same user (same auth0_id / sub)
        resp2 = test_client.get(
            "/api/me",
            headers={"Authorization": "Bearer second_token"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["id"] == user_id_1

    def test_auth0_can_update_pushover(
        self,
        auth0_mode: None,
        mock_auth0_verify: dict,
        test_client: TestClient,
    ) -> None:
        """Auth0-mode users should be able to set pushover_token."""
        response = test_client.patch(
            "/api/me",
            headers={"Authorization": "Bearer test_token"},
            json={"pushover_token": "po_token_abc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pushover_token"] == "po_token_abc"

    def test_auth0_public_endpoints_still_open(
        self,
        auth0_mode: None,
        test_client: TestClient,
    ) -> None:
        """Public endpoints like health and providers work without auth."""
        assert test_client.get("/api/health").status_code == 200
        assert test_client.get("/api/providers").status_code == 200

    def test_auth0_expired_token_returns_401(
        self,
        auth0_mode: None,
        test_client: TestClient,
    ) -> None:
        """An expired JWT (simulated via mock) should return 401."""
        from fastapi import HTTPException, status

        with patch(
            "backend.auth._verify_auth0_token",
            new=AsyncMock(
                side_effect=HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                )
            ),
        ):
            response = test_client.get(
                "/api/me",
                headers={"Authorization": "Bearer expired_token"},
            )
        assert response.status_code == 401
        detail = response.json().get("detail", "")
        assert "expired" in detail.lower()

    def test_auth0_invalid_token_format_returns_401(
        self,
        auth0_mode: None,
        test_client: TestClient,
    ) -> None:
        """A malformed token that causes a signing key resolution failure should return 401."""
        from fastapi import HTTPException, status

        with patch(
            "backend.auth._verify_auth0_token",
            new=AsyncMock(
                side_effect=HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to resolve signing key",
                )
            ),
        ):
            response = test_client.get(
                "/api/me",
                headers={"Authorization": "Bearer malformed_token"},
            )
        assert response.status_code == 401

    def test_auth0_user_created_via_email_fallback(
        self,
        auth0_mode: None,
        test_client: TestClient,
    ) -> None:
        """When payload has no email, the sub (auth0_id) should be used as email."""
        no_email_sub = "auth0|fallback_only"
        payload_without_email = {
            "sub": no_email_sub,
            "iss": "https://camply-test.us.auth0.com/",
            "aud": "https://api.camply.juftin.dev",
        }

        with patch(
            "backend.auth._verify_auth0_token",
            new=AsyncMock(return_value=payload_without_email),
        ):
            response = test_client.get(
                "/api/me",
                headers={"Authorization": "Bearer no_email_token"},
            )
        assert response.status_code == 200
        data = response.json()
        # Should fall back to sub (lowercased)
        assert no_email_sub.lower() in data["email"]

    def test_auth0_jwks_client_cache_hit(
        self,
        auth0_mode: None,
    ) -> None:
        """Calling _get_jwks_client twice with the same domain returns the cached client."""
        from backend.auth import _get_jwks_client, _jwks_client_cache

        # Clear cache
        _jwks_client_cache.clear()

        from backend.config import backend_config

        original_domain = backend_config.auth0_domain
        try:
            backend_config.auth0_domain = "cache-test.us.auth0.com"

            client1 = _get_jwks_client()
            client2 = _get_jwks_client()

            # Same object (cached)
            assert client1 is client2
            # Cache has one entry
            assert "cache-test.us.auth0.com" in _jwks_client_cache
        finally:
            backend_config.auth0_domain = original_domain
            _jwks_client_cache.clear()

    def test_auth0_jwks_client_cache_hit_with_config_monkeypatch(
        self,
        auth0_mode: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """JWKS client cache uses the domain from backend_config."""
        from backend.auth import _jwks_client_cache

        _jwks_client_cache.clear()
        monkeypatch.setattr(
            "backend.auth.backend_config.auth0_domain",
            "monkey-domain.us.auth0.com",
        )

        from backend.auth import _get_jwks_client

        client = _get_jwks_client()
        assert "monkey-domain.us.auth0.com" in _jwks_client_cache
        assert _jwks_client_cache["monkey-domain.us.auth0.com"] is client

        _jwks_client_cache.clear()
