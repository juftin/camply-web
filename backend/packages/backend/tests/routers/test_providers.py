"""
Tests for the ``/api/provider`` endpoints.
"""

from fastapi.testclient import TestClient


class TestListProviders:
    """Tests for GET /api/provider (list all providers)."""

    def test_list_providers(self, test_client: TestClient) -> None:
        """All providers should be returned."""
        response = test_client.get("/api/provider")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        names = [p["name"] for p in data]
        assert "Recreation.gov" in names
        assert "Disabled Provider" in names


class TestGetProvider:
    """Tests for GET /api/provider/{id}."""

    def test_get_provider_found(self, test_client: TestClient) -> None:
        """A known provider should be returned correctly."""
        response = test_client.get("/api/provider/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Recreation.gov"
        assert data["url"] == "https://recreation.gov"
        assert data["enabled"] is True

    def test_get_provider_not_found(self, test_client: TestClient) -> None:
        """A non-existent provider returns 404."""
        response = test_client.get("/api/provider/999")
        assert response.status_code == 404
        assert "Provider not found" in response.text
