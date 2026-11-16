"""
Tests for the ``/api/provider`` endpoints.
"""

from fastapi.testclient import TestClient

from camply.providers import PROVIDERS
from camply.providers.base import ProviderFilterCapabilities


class TestListProviders:
    """Tests for GET /api/providers (list all providers)."""

    def test_list_providers(self, test_client: TestClient) -> None:
        """All providers should be returned with filter capabilities."""
        response = test_client.get("/api/providers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        names = [p["name"] for p in data]
        assert "Recreation.gov" in names
        assert "Disabled Provider" in names
        rec_gov = next(p for p in data if p["id"] == 1)
        assert rec_gov["filter_capabilities"] == {
            "preferred_types": True,
            "require_electric": True,
            "require_accessible": True,
            "min_rv_length": True,
        }

    def test_list_providers_reflects_custom_capabilities(
        self, test_client: TestClient, monkeypatch
    ) -> None:
        """Provider capability overrides propagate to both list and detail routes."""
        rec_cls = PROVIDERS[1]
        monkeypatch.setattr(
            rec_cls,
            "filter_capabilities",
            ProviderFilterCapabilities(min_rv_length=False, require_accessible=False),
        )
        list_resp = test_client.get("/api/providers")
        assert list_resp.status_code == 200
        rec_gov = next(p for p in list_resp.json() if p["id"] == 1)
        assert rec_gov["filter_capabilities"] == {
            "preferred_types": True,
            "require_electric": True,
            "require_accessible": False,
            "min_rv_length": False,
        }

        detail_resp = test_client.get("/api/provider/1")
        assert detail_resp.status_code == 200
        assert (
            detail_resp.json()["filter_capabilities"] == rec_gov["filter_capabilities"]
        )


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
