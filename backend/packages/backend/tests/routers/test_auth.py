"""
Tests for the ``/api/me`` endpoint and auth resolution.

These use FastAPI's synchronous ``TestClient`` which wraps async endpoints.
The default DB is an SQLite file configured by the environment.
"""

from fastapi.testclient import TestClient


class TestMeEndpoint:
    """Tests for GET/PATCH /api/me."""

    def test_get_me_local_mode(self, test_client: TestClient) -> None:
        """Local mode should return the admin user."""
        response = test_client.get("/api/me")
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
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pushover_token"] == "test_token_abc123"

    def test_patch_me_clear_pushover(self, test_client: TestClient) -> None:
        """PATCH /api/me with null should clear the token."""
        # First set a token
        set_resp = test_client.patch(
            "/api/me", json={"pushover_token": "temp_token"}
        )
        assert set_resp.status_code == 200
        assert set_resp.json()["pushover_token"] == "temp_token"

        # Then clear it
        clear_resp = test_client.patch("/api/me", json={"pushover_token": None})
        assert clear_resp.status_code == 200
        assert clear_resp.json()["pushover_token"] is None


class TestProvidersEndpoint:
    """Tests for GET /api/providers."""

    def test_list_providers(self, test_client: TestClient) -> None:
        """Should return a list of providers."""
        response = test_client.get("/api/providers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
