"""
Tests for the ``/api/scans`` CRUD endpoints.

Each test uses unique data to remain independent of other tests.
"""

import uuid
from itertools import count

import pytest
from fastapi.testclient import TestClient

from camply.db.models import Campground, Provider, RecreationArea
from camply.providers import PROVIDERS
from camply.providers.base import ProviderFilterCapabilities
from tests.server import conftest

API_SCANS = "/api/scans"
API_SEARCH = "/api/search"
API_ME = "/api/me"

# Sequentially-unique IDs to keep tests isolated from shared DB state
_next_counter = count(1)


def _next() -> str:
    return f"seed-{next(_next_counter)}"


# ---------------------------------------------------------------------------
# Seed data — runs once before any tests in this module
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def _seed_data():
    """Seed recreation areas and campgrounds into the shared DB.

    Provider id=1 is already seeded by conftest.
    """
    conftest.seed_data(
        add_rows=[
            Provider(
                id=3,
                name="Florida State Parks",
                url="https://reserve.floridastateparks.org/Web",
                enabled=True,
            ),
            RecreationArea(
                id="rec-yosemite",
                provider_id=1,
                name="Yosemite National Park",
                country="US",
                state="CA",
                reservable=True,
                enabled=True,
            ),
            RecreationArea(
                id="rec-florida",
                provider_id=3,
                name="Florida Park",
                country="US",
                state="FL",
                reservable=True,
                enabled=True,
            ),
        ]
    )


def _seed_campground(cg_id: str, name: str = "Test Campground"):
    """Seed a single campground into the shared DB."""
    conftest.seed_data(
        add_rows=[
            Campground(
                id=cg_id,
                provider_id=1,
                recreation_area_id="rec-yosemite",
                name=name,
                country="US",
                state="CA",
                reservable=True,
                enabled=True,
            ),
        ],
    )


def _create_scan(
    test_client: TestClient,
    cg_id: str,
    **overrides,
) -> dict:
    """Helper: POST /api/scans and return the JSON response dict."""
    payload = {
        "provider_id": 1,
        "campground_id": cg_id,
        "start_date": "2027-07-01",
        "end_date": "2027-07-05",
        "min_stay_length": 1,
        "preferred_types": [],
        "require_electric": False,
        **overrides,
    }
    resp = test_client.post(API_SCANS, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateScan:
    """Tests for POST /api/scans."""

    def test_create_scan(self, test_client: TestClient) -> None:
        cg_id = _next()
        _seed_campground(cg_id, "Lower Pines")

        data = _create_scan(
            test_client,
            cg_id,
            min_stay_length=2,
            preferred_types=["TENT"],
            require_electric=True,
        )

        assert data["campground_name"] == "Lower Pines"
        assert data["start_date"] == "2027-07-01"
        assert data["end_date"] == "2027-07-05"
        assert data["min_stay_length"] == 2
        assert data["preferred_types"] == ["TENT"]
        assert data["require_electric"] is True
        assert data["min_rv_length"] is None
        assert data["is_active"] is True
        assert data["found_count"] == 0
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.parametrize("bad_length", [0, -5, 201])
    def test_create_scan_rejects_out_of_range_rv_length(
        self, test_client: TestClient, bad_length: int
    ) -> None:
        cg_id = _next()
        _seed_campground(cg_id)
        resp = test_client.post(
            API_SCANS,
            json={
                "provider_id": 1,
                "campground_id": cg_id,
                "start_date": "2027-07-01",
                "end_date": "2027-07-05",
                "min_rv_length": bad_length,
            },
        )
        assert resp.status_code == 422

    def test_create_scan_with_valid_min_rv_length(
        self, test_client: TestClient
    ) -> None:
        cg_id = _next()
        _seed_campground(cg_id)
        data = _create_scan(
            test_client, cg_id, min_rv_length=28, require_accessible=True
        )
        assert data["min_rv_length"] == 28
        assert data["require_accessible"] is True
        patched = test_client.patch(
            f"{API_SCANS}/{data['id']}", json={"require_accessible": False}
        )
        assert patched.status_code == 200
        assert patched.json()["require_accessible"] is False
        assert patched.json()["min_rv_length"] == 28

    def test_create_scan_duplicate(self, test_client: TestClient) -> None:
        cg_id = _next()
        _seed_campground(cg_id)

        _create_scan(test_client, cg_id)

        resp2 = test_client.post(
            API_SCANS,
            json={
                "provider_id": 1,
                "campground_id": cg_id,
                "start_date": "2027-07-01",
                "end_date": "2027-07-05",
            },
        )
        assert resp2.status_code == 409, resp2.text
        assert "already exists" in resp2.text.lower()

    def test_create_scan_nonexistent_campground(self, test_client: TestClient) -> None:
        response = test_client.post(
            API_SCANS,
            json={
                "provider_id": 1,
                "campground_id": "not-a-real-cg",
                "start_date": "2027-07-01",
                "end_date": "2027-07-05",
            },
        )
        assert response.status_code == 404, response.text


class TestListScans:
    """Tests for GET /api/scans."""

    def test_list_scans_returns_paginated(self, test_client: TestClient) -> None:
        """GET /api/scans returns a paginated list."""
        response = test_client.get(API_SCANS)
        assert response.status_code == 200
        data = response.json()
        assert "scans" in data
        assert "total" in data
        assert isinstance(data["scans"], list)
        assert isinstance(data["total"], int)

    def test_list_scans(self, test_client: TestClient) -> None:
        cg1, cg2 = _next(), _next()
        _seed_campground(cg1, "List Camp A")
        _seed_campground(cg2, "List Camp B")
        _create_scan(test_client, cg1)
        _create_scan(test_client, cg2)

        response = test_client.get(API_SCANS)
        assert response.status_code == 200
        data = response.json()
        # At least 2 scans (our new ones plus any from prior tests)
        assert data["total"] >= 2
        assert len(data["scans"]) >= 2
        cg_names = {s["campground_name"] for s in data["scans"]}
        assert "List Camp A" in cg_names
        assert "List Camp B" in cg_names

    def test_list_scans_filter_active(self, test_client: TestClient) -> None:
        cg_id = _next()
        _seed_campground(cg_id, "Active Filter Camp")
        _create_scan(test_client, cg_id)

        response = test_client.get(f"{API_SCANS}?is_active=true")
        assert response.status_code == 200
        data = response.json()
        # At least 1 (our new scan, plus any from prior tests)
        assert data["total"] >= 1
        cg_names = {s["campground_name"] for s in data["scans"]}
        assert "Active Filter Camp" in cg_names


class TestGetScan:
    """Tests for GET /api/scans/{id}."""

    def test_get_scan_detail(self, test_client: TestClient) -> None:
        cg_id = _next()
        _seed_campground(cg_id, "Detail Camp")
        created = _create_scan(test_client, cg_id)
        scan_id = created["id"]

        response = test_client.get(f"{API_SCANS}/{scan_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == scan_id
        assert data["campground_name"] == "Detail Camp"
        assert data["results"] == []

    def test_get_scan_not_found(self, test_client: TestClient) -> None:
        response = test_client.get(f"{API_SCANS}/{uuid.uuid4()}")
        assert response.status_code == 404


class TestUpdateScan:
    """Tests for PATCH /api/scans/{id}."""

    def test_update_scan_toggle_active(self, test_client: TestClient) -> None:
        cg_id = _next()
        _seed_campground(cg_id)
        created = _create_scan(test_client, cg_id)
        scan_id = created["id"]

        resp = test_client.patch(f"{API_SCANS}/{scan_id}", json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        resp = test_client.patch(f"{API_SCANS}/{scan_id}", json={"is_active": True})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    def test_update_scan_filters(self, test_client: TestClient) -> None:
        cg_id = _next()
        _seed_campground(cg_id)
        created = _create_scan(test_client, cg_id)
        scan_id = created["id"]

        response = test_client.patch(
            f"{API_SCANS}/{scan_id}",
            json={
                "min_stay_length": 4,
                "preferred_types": ["RV"],
                "require_electric": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["min_stay_length"] == 4
        assert data["preferred_types"] == ["RV"]
        assert data["require_electric"] is True

    def test_update_scan_not_found(self, test_client: TestClient) -> None:
        response = test_client.patch(
            f"{API_SCANS}/{uuid.uuid4()}",
            json={"is_active": False},
        )
        assert response.status_code == 404


class TestDeleteScan:
    """Tests for DELETE /api/scans/{id}."""

    def test_delete_scan(self, test_client: TestClient) -> None:
        cg_id = _next()
        _seed_campground(cg_id)
        created = _create_scan(test_client, cg_id)
        scan_id = created["id"]

        response = test_client.delete(f"{API_SCANS}/{scan_id}")
        assert response.status_code == 204
        assert response.content == b""  # 204 must have no body

        get_resp = test_client.get(f"{API_SCANS}/{scan_id}")
        assert get_resp.status_code == 404

    def test_delete_scan_not_found(self, test_client: TestClient) -> None:
        response = test_client.delete(f"{API_SCANS}/{uuid.uuid4()}")
        assert response.status_code == 404


class TestSearch:
    """Tests for GET /api/search (basic smoke tests).

    Note: the ``Search`` table is a separate materialized view that must
    be populated independently from the ``campgrounds`` table, so these
    tests avoid assuming seeded data will appear in search results.
    """

    def test_search_empty_query(self, test_client: TestClient) -> None:
        """An empty query returns a 200 with an empty list."""
        response = test_client.get(f"{API_SEARCH}?query=")
        assert response.status_code == 200
        assert response.json() == []

    def test_search_returns_list(self, test_client: TestClient) -> None:
        """A query returns a 200 with a list."""
        response = test_client.get(f"{API_SEARCH}?query=test")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestMe:
    """Tests for GET /api/me."""

    def test_me_endpoint(self, test_client: TestClient) -> None:
        response = test_client.get(API_ME)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@camply.local"
        assert data["is_invited"] is True


class TestProviderFilterGating:
    """Tests for per-provider filter capability validation on /api/scans."""

    def test_create_scan_rejects_unsupported_filter(
        self, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /api/scans returns 422 when a filter is unsupported by the provider."""
        cg_id = _next()
        _seed_campground(cg_id)
        monkeypatch.setattr(
            PROVIDERS[1],
            "filter_capabilities",
            ProviderFilterCapabilities(min_rv_length=False),
        )
        rejected = test_client.post(
            API_SCANS,
            json={
                "provider_id": 1,
                "campground_id": cg_id,
                "start_date": "2027-07-01",
                "end_date": "2027-07-05",
                "min_rv_length": 28,
            },
        )
        assert rejected.status_code == 422
        assert "minimum RV / trailer length" in rejected.json()["detail"]

        allowed = test_client.post(
            API_SCANS,
            json={
                "provider_id": 1,
                "campground_id": cg_id,
                "start_date": "2027-07-01",
                "end_date": "2027-07-05",
            },
        )
        assert allowed.status_code == 201

    def test_update_scan_rejects_unsupported_filter_but_allows_pause(
        self, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PATCH validates modified filters while still allowing pause on legacy scans."""
        cg_id = _next()
        _seed_campground(cg_id)
        created = test_client.post(
            API_SCANS,
            json={
                "provider_id": 1,
                "campground_id": cg_id,
                "start_date": "2027-07-01",
                "end_date": "2027-07-05",
                "min_rv_length": 30,
            },
        )
        assert created.status_code == 201
        scan_id = created.json()["id"]

        monkeypatch.setattr(
            PROVIDERS[1],
            "filter_capabilities",
            ProviderFilterCapabilities(min_rv_length=False, require_electric=False),
        )

        # Pausing or extending dates on a legacy scan without modifying filters succeeds
        paused = test_client.patch(
            f"{API_SCANS}/{scan_id}",
            json={"is_active": False},
        )
        assert paused.status_code == 200

        extended = test_client.patch(
            f"{API_SCANS}/{scan_id}",
            json={"end_date": "2027-07-06"},
        )
        assert extended.status_code == 200
        assert extended.json()["end_date"] == "2027-07-06"

        # Trying to enable an unsupported filter (alone or with dates) fails with 422
        rejected = test_client.patch(
            f"{API_SCANS}/{scan_id}",
            json={"end_date": "2027-07-07", "require_electric": True},
        )
        assert rejected.status_code == 422
        assert "electric hookup" in rejected.json()["detail"]

        # Clearing the unsupported filter succeeds
        cleared = test_client.patch(
            f"{API_SCANS}/{scan_id}",
            json={"min_rv_length": None, "require_electric": False},
        )
        assert cleared.status_code == 200
        assert cleared.json()["min_rv_length"] is None

    def test_switch_provider_validates_carried_over_filters(
        self, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Switching provider_id rejects unsupported carried-over filters until cleared."""
        cg1 = _next()
        cg3 = _next()
        _seed_campground(cg1)
        conftest.seed_data(
            add_rows=[
                Campground(
                    id=cg3,
                    provider_id=3,
                    recreation_area_id="rec-florida",
                    name="Florida Camp",
                    country="US",
                    state="FL",
                    reservable=True,
                    enabled=True,
                )
            ]
        )
        created = test_client.post(
            API_SCANS,
            json={
                "provider_id": 1,
                "campground_id": cg1,
                "start_date": "2027-07-01",
                "end_date": "2027-07-05",
                "preferred_types": ["RV"],
                "require_accessible": True,
                "min_rv_length": 25,
            },
        )
        assert created.status_code == 201
        scan_id = created.json()["id"]

        monkeypatch.setattr(
            PROVIDERS[3],
            "filter_capabilities",
            ProviderFilterCapabilities(
                preferred_types=False,
                require_accessible=False,
                min_rv_length=False,
            ),
        )
        rejected = test_client.patch(
            f"{API_SCANS}/{scan_id}",
            json={"provider_id": 3, "campground_id": cg3},
        )
        assert rejected.status_code == 422
        detail = rejected.json()["detail"]
        assert "campsite type" in detail
        assert "ADA accessibility" in detail
        assert "minimum RV / trailer length" in detail

        switched = test_client.patch(
            f"{API_SCANS}/{scan_id}",
            json={
                "provider_id": 3,
                "campground_id": cg3,
                "preferred_types": [],
                "require_accessible": False,
                "min_rv_length": None,
            },
        )
        assert switched.status_code == 200
        assert switched.json()["provider_id"] == 3

    def test_recreation_area_scan_filter_gating(
        self, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Recreation-area scans enforce provider capabilities on POST and PATCH."""
        cg_id = _next()
        _seed_campground(cg_id)
        monkeypatch.setattr(
            PROVIDERS[1],
            "filter_capabilities",
            ProviderFilterCapabilities(preferred_types=False, require_accessible=False),
        )
        rejected = test_client.post(
            API_SCANS,
            json={
                "provider_id": 1,
                "destination_type": "recreation_area",
                "recreation_area_id": "rec-yosemite",
                "coverage_mode": "selected",
                "campground_ids": [cg_id],
                "start_date": "2027-07-01",
                "end_date": "2027-07-05",
                "preferred_types": ["RV"],
            },
        )
        assert rejected.status_code == 422
        assert "campsite type" in rejected.json()["detail"]

        # Seed a legacy recreation-area scan with require_accessible=True before restriction
        monkeypatch.setattr(
            PROVIDERS[1],
            "filter_capabilities",
            ProviderFilterCapabilities(),
        )
        created = test_client.post(
            API_SCANS,
            json={
                "provider_id": 1,
                "destination_type": "recreation_area",
                "recreation_area_id": "rec-yosemite",
                "coverage_mode": "selected",
                "campground_ids": [cg_id],
                "start_date": "2027-07-01",
                "end_date": "2027-07-05",
                "require_accessible": True,
            },
        )
        assert created.status_code == 201
        scan_id = created.json()["id"]

        monkeypatch.setattr(
            PROVIDERS[1],
            "filter_capabilities",
            ProviderFilterCapabilities(require_accessible=False),
        )
        # Updating coverage_mode on legacy scan without touching filters succeeds
        coverage_patch = test_client.patch(
            f"{API_SCANS}/{scan_id}",
            json={"coverage_mode": "all"},
        )
        assert coverage_patch.status_code == 200
        assert coverage_patch.json()["coverage_mode"] == "all"

        # Enabling another unsupported filter or re-asserting it fails
        bad_patch = test_client.patch(
            f"{API_SCANS}/{scan_id}",
            json={
                "coverage_mode": "selected",
                "campground_ids": [cg_id],
                "require_accessible": True,
            },
        )
        assert bad_patch.status_code == 422
        assert "ADA accessibility" in bad_patch.json()["detail"]
