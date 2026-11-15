"""Exercise saved weekday preferences through the public scan endpoints."""

import asyncio
import datetime
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from camply.db.models import Campground, ScanResult, UniqueTarget, User, UserScan
from camply.server.app import app
from camply.server.auth import CurrentUser, resolve_current_user
from tests.server.conftest import maker, seed_data


@pytest.fixture
def weekday_scan_payload() -> dict[str, Any]:
    """Prepare an isolated campground and a future seasonal search window."""
    campground_id = f"weekdays-{uuid.uuid4().hex}"
    seed_data(
        add_rows=[
            Campground(id=campground_id, provider_id=1, name="Synthetic Weekday Camp")
        ]
    )
    return {
        "provider_id": 1,
        "campground_id": campground_id,
        "start_date": "2099-07-01",
        "end_date": "2099-09-01",
    }


@pytest.mark.parametrize("selection", [None, [], [-1], [7], [True], ["4"], [4.5]])
def test_invalid_day_values_reject_create_and_edit(
    test_client: TestClient, weekday_scan_payload: dict[str, Any], selection: Any
) -> None:
    """Malformed selections never silently become unrestricted searches."""
    response = test_client.post(
        "/api/scans", json={**weekday_scan_payload, "allowed_weekdays": selection}
    )
    assert response.status_code == 422, response.text
    created = test_client.post("/api/scans", json=weekday_scan_payload)
    assert created.status_code == 201, created.text
    path = f"/api/scans/{created.json()['id']}"
    response = test_client.patch(
        path, json={"allowed_weekdays": selection, "require_electric": True}
    )
    assert response.status_code == 422, response.text
    assert test_client.get(path).json()["require_electric"] is False


def test_saved_days_round_trip_omit_and_reset(
    test_client: TestClient, weekday_scan_payload: dict[str, Any]
) -> None:
    """Create/edit normalize dates independently and omitted preferences stay saved."""
    response = test_client.post(
        "/api/scans",
        json={
            **weekday_scan_payload,
            "allowed_weekdays": [5, 4, 5],
            "min_stay_length": 2,
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["allowed_weekdays"] == [4, 5]
    path = f"/api/scans/{created['id']}"
    assert test_client.get(path).json()["allowed_weekdays"] == [4, 5]
    listed = test_client.get("/api/scans?limit=200").json()["scans"]
    assert next(scan for scan in listed if scan["id"] == created["id"])[
        "allowed_weekdays"
    ] == [4, 5]
    unchanged = test_client.patch(
        path, json={"is_active": False, "require_electric": True}
    ).json()
    assert unchanged["allowed_weekdays"] == [4, 5]
    assert unchanged["start_date"] == created["start_date"]
    assert unchanged["end_date"] == created["end_date"]
    assert unchanged["created_at"] == created["created_at"]
    reset = test_client.patch(path, json={"allowed_weekdays": list(range(7))}).json()
    assert reset["allowed_weekdays"] == list(range(7))
    assert reset["is_active"] is False

    async def stored_preference() -> None:
        """Unrestricted selections use the same storage sentinel as old scans."""
        async with maker() as session:
            scan = await session.get(UserScan, uuid.UUID(created["id"]))
            assert scan is not None
            assert scan.allowed_weekdays is None

    asyncio.run(stored_preference())


@pytest.mark.parametrize(
    "criteria",
    [
        {"allowed_weekdays": [4, 5], "min_stay_length": 3},
        {"allowed_weekdays": [0, 2], "min_stay_length": 2},
        {
            "start_date": "2099-07-01",
            "end_date": "2099-07-02",
            "allowed_weekdays": [(datetime.date(2099, 7, 1).weekday() + 1) % 7],
        },
        {"start_date": "2000-01-01", "end_date": "2000-01-03"},
    ],
)
def test_impossible_create_does_not_create_target(
    test_client: TestClient,
    weekday_scan_payload: dict[str, Any],
    criteria: dict[str, Any],
) -> None:
    """Calendar impossibility is rejected before creating shared search state."""
    response = test_client.post("/api/scans", json={**weekday_scan_payload, **criteria})
    assert response.status_code == 422, response.text
    assert "selected nights" in response.json()["detail"]

    async def count_targets() -> None:
        """Failed validation leaves no shared target for this synthetic campground."""
        async with maker() as session:
            assert (
                await session.scalar(
                    select(func.count(UniqueTarget.id)).where(
                        UniqueTarget.campground_id
                        == weekday_scan_payload["campground_id"]
                    )
                )
                == 0
            )

    asyncio.run(count_targets())


def test_merged_weekday_edit_is_atomic(
    test_client: TestClient, weekday_scan_payload: dict[str, Any]
) -> None:
    """An impossible merged edit leaves both preferences and targets untouched."""
    created = test_client.post(
        "/api/scans",
        json={**weekday_scan_payload, "allowed_weekdays": [4, 5], "min_stay_length": 2},
    ).json()
    path = f"/api/scans/{created['id']}"
    before = test_client.get(path).json()
    response = test_client.patch(
        path, json={"min_stay_length": 3, "end_date": "2099-10-01", "is_active": False}
    )
    assert response.status_code == 422, response.text
    assert test_client.get(path).json() == before
    response = test_client.patch(
        path, json={"min_stay_length": 3, "allowed_weekdays": [4, 5, 6]}
    )
    assert response.status_code == 200, response.text
    assert response.json()["allowed_weekdays"] == [4, 5, 6]


def test_expired_scan_management_and_legacy_defaults(
    test_client: TestClient, weekday_scan_payload: dict[str, Any]
) -> None:
    """Existing old scans remain readable and pausable after calendar expiration."""
    created = test_client.post("/api/scans", json=weekday_scan_payload).json()
    assert created["allowed_weekdays"] == list(range(7))
    path = f"/api/scans/{created['id']}"

    async def expire_target() -> None:
        """Represent a subscription that has aged past its booking dates."""
        async with maker() as session:
            scan = await session.get(UserScan, uuid.UUID(created["id"]))
            assert scan is not None
            target = await session.get(UniqueTarget, scan.target_id)
            assert target is not None
            target.start_date = datetime.date(2000, 1, 1)
            target.end_date = datetime.date(2000, 1, 3)
            await session.commit()

    asyncio.run(expire_target())
    assert test_client.get(path).json()["allowed_weekdays"] == list(range(7))
    assert test_client.patch(path, json={"is_active": False}).status_code == 200
    assert test_client.patch(path, json={"is_active": True}).status_code == 200
    assert test_client.patch(path, json={"require_electric": True}).status_code == 200
    assert test_client.patch(path, json={"min_stay_length": 2}).status_code == 422


def test_shared_target_results_follow_each_subscriber(
    test_client: TestClient,
    weekday_scan_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Responses and counts narrow shared raw observations for the current owner."""
    created = test_client.post(
        "/api/scans",
        json={**weekday_scan_payload, "allowed_weekdays": [4, 5], "min_stay_length": 2},
    ).json()
    other = User(
        id=uuid.uuid4(),
        email=f"weekday-{uuid.uuid4().hex}@example.test",
        is_invited=True,
    )
    seed_data(add_rows=[other])
    dates = [datetime.date(2099, 7, day).isoformat() for day in range(1, 15)]

    async def seed_snapshot() -> uuid.UUID:
        """Persist a single provider observation for all matching subscribers."""
        async with maker() as session:
            scan = await session.get(UserScan, uuid.UUID(created["id"]))
            assert scan is not None
            session.add(
                ScanResult(
                    target_id=scan.target_id, campsite_id="one", available_dates=dates
                )
            )
            await session.commit()
            return scan.target_id

    target_id = asyncio.run(seed_snapshot())
    detail = test_client.get(f"/api/scans/{created['id']}").json()
    assert detail["found_count"] == 1
    assert detail["results"][0]["available_dates"] == [
        night
        for night in dates
        if datetime.date.fromisoformat(night).weekday() in [4, 5]
    ]

    overrides = app.dependency_overrides.copy()
    overrides[resolve_current_user] = lambda: CurrentUser(
        id=other.id,
        email=other.email,
        is_invited=True,
        is_admin=False,
        scanning_enabled=True,
    )
    monkeypatch.setattr(app, "dependency_overrides", overrides)
    response = test_client.post(
        "/api/scans", json={**weekday_scan_payload, "allowed_weekdays": [0, 2]}
    )
    assert response.status_code == 201, response.text
    other_id = response.json()["id"]
    detail = test_client.get(f"/api/scans/{other_id}").json()
    assert detail["results"][0]["available_dates"] == [
        night
        for night in dates
        if datetime.date.fromisoformat(night).weekday() in [0, 2]
    ]
    listed = test_client.get("/api/scans").json()["scans"]
    assert listed[0]["found_count"] == detail["found_count"] == 1

    async def verify_shared_target() -> None:
        """Different preferences do not create additional poll targets or alter data."""
        async with maker() as session:
            scan = await session.get(UserScan, uuid.UUID(other_id))
            assert scan is not None and scan.target_id == target_id
            assert (
                await session.scalar(
                    select(func.count(UniqueTarget.id)).where(
                        UniqueTarget.campground_id
                        == weekday_scan_payload["campground_id"]
                    )
                )
                == 1
            )
            snapshot = await session.scalar(
                select(ScanResult).where(ScanResult.target_id == target_id)
            )
            assert snapshot is not None and snapshot.available_dates == dates

    asyncio.run(verify_shared_target())


def test_one_seasonal_scan_finds_every_complete_weekend(
    test_client: TestClient, weekday_scan_payload: dict[str, Any]
) -> None:
    """One summer scan returns all full weekends and no midweek or isolated nights."""
    start = datetime.date(2027, 6, 1)
    end = datetime.date(2027, 9, 1)
    dates = [
        start + datetime.timedelta(days=offset) for offset in range((end - start).days)
    ]
    created = test_client.post(
        "/api/scans",
        json={
            **weekday_scan_payload,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "allowed_weekdays": [4, 5],
            "min_stay_length": 2,
        },
    )
    assert created.status_code == 201, created.text
    scan_id = created.json()["id"]

    async def seed_seasonal_openings() -> None:
        """Supply complete stays, isolated Fridays, and midweek openings at distinct sites."""
        async with maker() as session:
            scan = await session.get(UserScan, uuid.UUID(scan_id))
            assert scan is not None
            for site_id, available in (
                ("complete", dates),
                ("isolated", [night for night in dates if night.weekday() == 4]),
                ("midweek", [night for night in dates if night.weekday() < 4]),
            ):
                session.add(
                    ScanResult(
                        target_id=scan.target_id,
                        campsite_id=site_id,
                        available_dates=[night.isoformat() for night in available],
                    )
                )
            await session.commit()

    asyncio.run(seed_seasonal_openings())
    detail = test_client.get(f"/api/scans/{scan_id}").json()
    assert detail["found_count"] == 1
    assert [result["campsite_id"] for result in detail["results"]] == ["complete"]
    expected = [night.isoformat() for night in dates if night.weekday() in [4, 5]]
    assert detail["results"][0]["available_dates"] == expected
    assert len(expected) == 26
    listed = test_client.get("/api/scans?limit=200").json()["scans"]
    assert next(scan for scan in listed if scan["id"] == scan_id)["found_count"] == 1
