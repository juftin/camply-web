"""
Tests for the ``/api/campground`` endpoints.

Relies on seed data from conftest (Provider id=1, RecreationArea rec_area_1,
Campgrounds cg_1 and cg_non_reservable).
"""

import pytest
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
        """A non-existent campground raises ValueError."""
        with pytest.raises(ValueError, match="Campground not found"):
            test_client.get("/api/campground/1/nonexistent")

    def test_non_reservable_campground_excluded(
        self, test_client: TestClient
    ) -> None:
        """Non-reservable campgrounds raise ValueError because they're filtered."""
        with pytest.raises(ValueError, match="Campground not found"):
            test_client.get("/api/campground/1/cg_non_reservable")

    def test_wrong_provider_returns_not_found(
        self, test_client: TestClient
    ) -> None:
        """Querying with a wrong provider ID raises ValueError."""
        with pytest.raises(ValueError, match="Campground not found"):
            test_client.get("/api/campground/99/cg_1")
