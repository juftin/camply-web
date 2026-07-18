"""
Tests for the ``/api/scans`` CRUD endpoints.

Each test uses unique data to remain independent of other tests.
"""

import base64
import uuid
from itertools import count

import conftest
import pytest
from fastapi.testclient import TestClient

from db.models import Campground, RecreationArea

# Default Basic Auth credentials matching config defaults
_BASIC_AUTH = {"Authorization": f"Basic {base64.b64encode(b'admin:camply').decode()}"}

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
            RecreationArea(
                id="rec-yosemite",
                provider_id=1,
                name="Yosemite National Park",
                country="US",
                state="CA",
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
        "start_date": "2026-07-01",
        "end_date": "2026-07-05",
        "min_stay_length": 1,
        "preferred_types": [],
        "require_electric": False,
        **overrides,
    }
    resp = test_client.post(API_SCANS, json=payload, headers=_BASIC_AUTH)
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
        assert data["start_date"] == "2026-07-01"
        assert data["end_date"] == "2026-07-05"
        assert data["min_stay_length"] == 2
        assert data["preferred_types"] == ["TENT"]
        assert data["require_electric"] is True
        assert data["is_active"] is True
        assert data["found_count"] == 0
        assert "id" in data
        assert "created_at" in data

    def test_create_scan_duplicate(self, test_client: TestClient) -> None:
        cg_id = _next()
        _seed_campground(cg_id)

        _create_scan(test_client, cg_id)

        resp2 = test_client.post(
            API_SCANS,
            json={
                "provider_id": 1,
                "campground_id": cg_id,
                "start_date": "2026-07-01",
                "end_date": "2026-07-05",
            },
            headers=_BASIC_AUTH,
        )
        assert resp2.status_code == 409, resp2.text
        assert "already exists" in resp2.text.lower()

    def test_create_scan_nonexistent_campground(self, test_client: TestClient) -> None:
        response = test_client.post(
            API_SCANS,
            json={
                "provider_id": 1,
                "campground_id": "not-a-real-cg",
                "start_date": "2026-07-01",
                "end_date": "2026-07-05",
            },
            headers=_BASIC_AUTH,
        )
        assert response.status_code == 404, response.text


class TestListScans:
    """Tests for GET /api/scans."""

    def test_list_scans_returns_paginated(self, test_client: TestClient) -> None:
        """GET /api/scans returns a paginated list."""
        response = test_client.get(API_SCANS, headers=_BASIC_AUTH)
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

        response = test_client.get(API_SCANS, headers=_BASIC_AUTH)
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

        response = test_client.get(f"{API_SCANS}?is_active=true", headers=_BASIC_AUTH)
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

        response = test_client.get(f"{API_SCANS}/{scan_id}", headers=_BASIC_AUTH)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == scan_id
        assert data["campground_name"] == "Detail Camp"
        assert data["results"] == []

    def test_get_scan_not_found(self, test_client: TestClient) -> None:
        response = test_client.get(f"{API_SCANS}/{uuid.uuid4()}", headers=_BASIC_AUTH)
        assert response.status_code == 404


class TestUpdateScan:
    """Tests for PATCH /api/scans/{id}."""

    def test_update_scan_toggle_active(self, test_client: TestClient) -> None:
        cg_id = _next()
        _seed_campground(cg_id)
        created = _create_scan(test_client, cg_id)
        scan_id = created["id"]

        resp = test_client.patch(
            f"{API_SCANS}/{scan_id}", json={"is_active": False}, headers=_BASIC_AUTH
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        resp = test_client.patch(
            f"{API_SCANS}/{scan_id}", json={"is_active": True}, headers=_BASIC_AUTH
        )
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
            headers=_BASIC_AUTH,
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
            headers=_BASIC_AUTH,
        )
        assert response.status_code == 404


class TestDeleteScan:
    """Tests for DELETE /api/scans/{id}."""

    def test_delete_scan(self, test_client: TestClient) -> None:
        cg_id = _next()
        _seed_campground(cg_id)
        created = _create_scan(test_client, cg_id)
        scan_id = created["id"]

        response = test_client.delete(f"{API_SCANS}/{scan_id}", headers=_BASIC_AUTH)
        assert response.status_code == 204
        assert response.content == b""  # 204 must have no body

        get_resp = test_client.get(f"{API_SCANS}/{scan_id}", headers=_BASIC_AUTH)
        assert get_resp.status_code == 404

    def test_delete_scan_not_found(self, test_client: TestClient) -> None:
        response = test_client.delete(
            f"{API_SCANS}/{uuid.uuid4()}", headers=_BASIC_AUTH
        )
        assert response.status_code == 404


class TestSearch:
    """Tests for GET /api/search (basic smoke tests).

    Note: the ``Search`` table is a separate materialized view that must
    be populated independently from the ``campgrounds`` table, so these
    tests avoid assuming seeded data will appear in search results.
    """

    def test_search_empty_query(self, test_client: TestClient) -> None:
        """An empty query returns a 200 with an empty list."""
        response = test_client.get(f"{API_SEARCH}?query=", headers=_BASIC_AUTH)
        assert response.status_code == 200
        assert response.json() == []

    def test_search_returns_list(self, test_client: TestClient) -> None:
        """A query returns a 200 with a list."""
        response = test_client.get(f"{API_SEARCH}?query=test", headers=_BASIC_AUTH)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestMe:
    """Tests for GET /api/me."""

    def test_me_endpoint(self, test_client: TestClient) -> None:
        response = test_client.get(API_ME, headers=_BASIC_AUTH)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@camply.local"
        assert data["is_early_access_user"] is True
