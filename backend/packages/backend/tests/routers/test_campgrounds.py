"""
Tests for the ``/api/campground`` endpoints.

Relies on seed data from conftest (Provider id=1, RecreationArea rec_area_1,
Campgrounds cg_1 and cg_non_reservable).
"""

from fastapi.testclient import TestClient


class TestGetCampground:
    """Tests for GET /api/campground/{provider}/{id}."""

    def test_get_campground_found(self, test_client: TestClient) -> None:
        """A known campground should be returned correctly."""
        response = test_client.get("/api/campground/1/cg_1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "cg_1"
        assert data["provider_id"] == 1
        assert data["name"] == "Test Campground"
        assert data["reservable"] is True
        assert data["enabled"] is True
        assert "url" in data

    def test_get_campground_not_found(self, test_client: TestClient) -> None:
        """A non-existent campground returns 404."""
        response = test_client.get("/api/campground/1/nonexistent")
        assert response.status_code == 404

    def test_non_reservable_campground_excluded(self, test_client: TestClient) -> None:
        """Non-reservable campgrounds should return 404 (filtered out)."""
        response = test_client.get("/api/campground/1/cg_non_reservable")
        assert response.status_code == 404

    def test_wrong_provider_returns_not_found(self, test_client: TestClient) -> None:
        """Querying with a wrong provider ID returns 404."""
        response = test_client.get("/api/campground/99/cg_1")
        assert response.status_code == 404
