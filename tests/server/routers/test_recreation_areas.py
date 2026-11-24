"""
Tests for the ``/api/rec-area`` endpoints.
"""

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
        """A non-existent recreation area returns 404."""
        response = test_client.get("/api/rec-area/1/nonexistent")
        assert response.status_code == 404

    def test_get_rec_area_wrong_provider(self, test_client: TestClient) -> None:
        """Wrong provider ID returns 404."""
        response = test_client.get("/api/rec-area/99/rec_area_1")
        assert response.status_code == 404


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
        response = test_client.get("/api/rec-area/1/nonexistent_rec_area/campgrounds")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestMonitoringCampgrounds:
    """Tests for GET /api/rec-area/{provider}/{id}/monitoring-campgrounds."""

    def test_monitoring_campgrounds_search_pagination_and_exclusions(
        self, test_client: TestClient
    ) -> None:
        """Excludes unbookable members, filters by query, and pages beyond 100 items."""
        import uuid

        from camply.db.models import Campground, RecreationArea
        from tests.server.conftest import seed_data

        uid = uuid.uuid4().hex[:8]
        area = RecreationArea(id=f"area-mon-{uid}", provider_id=1, name="Paged Area")
        members = [
            Campground(
                id=f"mon-{uid}-{index:03}",
                provider_id=1,
                recreation_area_id=area.id,
                name=f"Paged Campground {index:03}",
                enabled=True,
                reservable=True,
            )
            for index in range(125)
        ]
        disabled = Campground(
            id=f"{area.id}-disabled",
            provider_id=1,
            recreation_area_id=area.id,
            name="Disabled Pines",
            enabled=False,
            reservable=True,
        )
        non_reservable = Campground(
            id=f"{area.id}-nonres",
            provider_id=1,
            recreation_area_id=area.id,
            name="NonReservable Pines",
            enabled=True,
            reservable=False,
        )
        searchable = Campground(
            id=f"{area.id}-pine",
            provider_id=1,
            recreation_area_id=area.id,
            name="Whispering Pines",
            enabled=True,
            reservable=True,
        )
        seed_data([area, *members, disabled, non_reservable, searchable])

        first_page = test_client.get(
            f"/api/rec-area/1/{area.id}/monitoring-campgrounds?limit=100&offset=0"
        )
        assert first_page.status_code == 200
        payload = first_page.json()
        assert payload["eligible_total"] == 126
        assert payload["total"] == 126
        assert payload["has_more"] is True
        assert len(payload["items"]) == 100
        assert isinstance(payload["catalog_revision"], int)

        second_page = test_client.get(
            f"/api/rec-area/1/{area.id}/monitoring-campgrounds?limit=100&offset=100"
        )
        assert second_page.status_code == 200
        second = second_page.json()
        assert second["has_more"] is False
        assert len(second["items"]) == 26
        returned_ids = {item["id"] for item in payload["items"] + second["items"]}
        assert disabled.id not in returned_ids
        assert non_reservable.id not in returned_ids

        filtered = test_client.get(
            f"/api/rec-area/1/{area.id}/monitoring-campgrounds?query=%20whispering%20"
        )
        assert filtered.status_code == 200
        f_data = filtered.json()
        assert f_data["eligible_total"] == 126
        assert f_data["total"] == 1
        assert [item["id"] for item in f_data["items"]] == [searchable.id]

    def test_monitoring_campgrounds_errors_and_invalid_bounds(
        self, test_client: TestClient
    ) -> None:
        """Missing areas, disabled areas, and invalid paging bounds are rejected."""
        from camply.db.models import RecreationArea
        from tests.server.conftest import seed_data

        seed_data(
            [
                RecreationArea(
                    id="disabled_area",
                    provider_id=1,
                    name="Closed Area",
                    enabled=False,
                )
            ]
        )
        assert (
            test_client.get(
                "/api/rec-area/1/missing/monitoring-campgrounds"
            ).status_code
            == 404
        )
        assert (
            test_client.get(
                "/api/rec-area/1/disabled_area/monitoring-campgrounds"
            ).status_code
            == 422
        )
        for qs in ("limit=0", "limit=101", "offset=-1"):
            assert (
                test_client.get(
                    f"/api/rec-area/1/rec_area_1/monitoring-campgrounds?{qs}"
                ).status_code
                == 422
            )
