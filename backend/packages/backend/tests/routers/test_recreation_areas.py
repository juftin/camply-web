"""
Tests for the ``/api/rec-area`` endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestGetRecreationArea:
    """Tests for GET /api/rec-area/{provider}/{id}."""

    def test_get_rec_area_found(self, test_client: TestClient) -> None:
        """A known recreation area should be returned correctly."""
        response = test_client.get("/api/rec-area/1/rec_area_1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "rec_area_1"
        assert data["provider_id"] == 1
        assert data["name"] == "Test Recreation Area"
        assert data["country"] == "US"
        assert data["state"] == "CA"

    def test_get_rec_area_not_found(self, test_client: TestClient) -> None:
        """A non-existent recreation area raises ValueError."""
        with pytest.raises(ValueError, match="Recreation Area not found"):
            test_client.get("/api/rec-area/1/nonexistent")

    def test_get_rec_area_wrong_provider(
        self, test_client: TestClient
    ) -> None:
        """Wrong provider ID raises ValueError."""
        with pytest.raises(ValueError, match="Recreation Area not found"):
            test_client.get("/api/rec-area/99/rec_area_1")


class TestListRecreationAreaCampgrounds:
    """Tests for GET /api/rec-area/{provider}/{id}/campgrounds."""

    def test_list_campgrounds(self, test_client: TestClient) -> None:
        """Campgrounds for a recreation area should be listed."""
        response = test_client.get("/api/rec-area/1/rec_area_1/campgrounds")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        ids = [c["id"] for c in data]
        assert "cg_1" in ids
        assert "cg_non_reservable" in ids

    def test_list_campgrounds_empty(self, test_client: TestClient) -> None:
        """An empty recreation area returns an empty list."""
        response = test_client.get(
            "/api/rec-area/1/nonexistent_rec_area/campgrounds"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
