"""Regression coverage for editing subscriptions without mutating shared targets."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from camply.db.models import Campground, ScanResult, UniqueTarget, User, UserScan
from camply.server.app import app
from camply.server.auth import CurrentUser, resolve_current_user
from tests.server.conftest import maker, seed_data


@pytest.fixture
def scan(test_client: TestClient) -> dict[str, Any]:
    """Create an isolated subscription using synthetic campground metadata."""
    campground_id = f"edit-{uuid.uuid4().hex}"
    seed_data(
        add_rows=[
            Campground(
                id=campground_id,
                provider_id=1,
                recreation_area_id="rec_area_1",
                name="Editing Campground",
                reservable=True,
                enabled=True,
            )
        ]
    )
    response = test_client.post(
        "/api/scans",
        json={
            "provider_id": 1,
            "campground_id": campground_id,
            "start_date": "2027-07-01",
            "end_date": "2027-07-05",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_edit_campground_dates_and_filters(
    test_client: TestClient, scan: dict[str, Any]
) -> None:
    """PATCH saves all editable fields while preserving identity and pause state."""
    path = f"/api/scans/{scan['id']}"
    assert test_client.patch(path, json={"is_active": False}).status_code == 200
    changes = {
        "provider_id": 1,
        "campground_id": "cg_1",
        "start_date": "2027-08-01",
        "end_date": "2027-08-09",
        "min_stay_length": 3,
        "preferred_types": ["RV", "CABIN"],
        "require_electric": True,
    }
    response = test_client.patch(path, json=changes)
    assert response.status_code == 200, response.text
    saved = test_client.get(path).json()
    for field, value in changes.items():
        assert saved[field] == value
    assert saved["id"] == scan["id"]
    assert saved["created_at"] == scan["created_at"]
    assert saved["is_active"] is False
    assert saved["campground_name"] == "Test Campground"


@pytest.mark.parametrize(
    "changes",
    [
        {"start_date": "2027-07-05"},
        {"end_date": "2027-06-30"},
        {"start_date": "2027-09-02", "end_date": "2027-09-01"},
        {"min_stay_length": 0},
    ],
)
def test_invalid_edit_is_atomic(
    test_client: TestClient, scan: dict[str, Any], changes: dict[str, Any]
) -> None:
    """Invalid merged dates or filters leave the saved subscription untouched."""
    path = f"/api/scans/{scan['id']}"
    before = test_client.get(path).json()
    response = test_client.patch(path, json={"require_electric": True, **changes})
    assert response.status_code == 422
    assert test_client.get(path).json() == before


def test_edit_unknown_campground_is_atomic(
    test_client: TestClient, scan: dict[str, Any]
) -> None:
    """A nonexistent campground rejects the entire edit."""
    path = f"/api/scans/{scan['id']}"
    before = test_client.get(path).json()
    response = test_client.patch(
        path, json={"campground_id": "missing-edit-campground", "is_active": False}
    )
    assert response.status_code == 404
    assert test_client.get(path).json() == before


def test_edit_duplicate_subscription_is_atomic(
    test_client: TestClient, scan: dict[str, Any]
) -> None:
    """Editing onto another subscription returns a conflict without saving filters."""
    response = test_client.post(
        "/api/scans",
        json={
            "provider_id": scan["provider_id"],
            "campground_id": scan["campground_id"],
            "start_date": "2027-07-10",
            "end_date": "2027-07-15",
        },
    )
    assert response.status_code == 201
    path = f"/api/scans/{scan['id']}"
    before = test_client.get(path).json()
    response = test_client.patch(
        path,
        json={
            "start_date": "2027-07-10",
            "end_date": "2027-07-15",
            "require_electric": True,
        },
    )
    assert response.status_code == 409
    assert test_client.get(path).json() == before


@pytest.mark.asyncio
async def test_edit_isolates_shared_target_and_reuses_existing_target(
    test_client: TestClient, scan: dict[str, Any]
) -> None:
    """Partial edits relink only the owner, retaining other users' cached results."""
    async with maker() as session:
        original = await session.get(UserScan, uuid.UUID(scan["id"]))
        assert original is not None
        old_target_id = original.target_id
        user = User(email=f"edit-{uuid.uuid4().hex}@example.test", is_invited=True)
        session.add(user)
        await session.flush()
        shared_scan = UserScan(user_id=user.id, target_id=old_target_id)
        result = ScanResult(
            target_id=old_target_id,
            campsite_id="synthetic-site",
            available_dates=["2027-07-02"],
        )
        session.add_all([shared_scan, result])
        await session.commit()

    path = f"/api/scans/{scan['id']}"
    response = test_client.patch(path, json={"end_date": "2027-07-08"})
    assert response.status_code == 200
    assert response.json()["end_date"] == "2027-07-08"
    assert response.json()["start_date"] == "2027-07-01"
    assert test_client.get(path).json()["results"] == []

    async with maker() as session:
        other = await session.get(UserScan, shared_scan.id)
        target = await session.get(UniqueTarget, old_target_id)
        assert other is not None and other.target_id == old_target_id
        assert target is not None and target.end_date.isoformat() == "2027-07-05"
        assert await session.get(ScanResult, result.id) is not None

    response = test_client.patch(path, json={"end_date": "2027-07-05"})
    assert response.status_code == 200
    assert response.json()["found_count"] == 1
    async with maker() as session:
        restored = await session.get(UserScan, uuid.UUID(scan["id"]))
        assert restored is not None and restored.target_id == old_target_id
        targets = await session.scalars(
            select(UniqueTarget).where(
                UniqueTarget.campground_id == scan["campground_id"]
            )
        )
        assert len(targets.all()) == 2

    assert test_client.delete(path).status_code == 204
    async with maker() as session:
        assert await session.get(UserScan, shared_scan.id) is not None
        assert await session.get(ScanResult, result.id) is not None


def test_other_user_cannot_edit_or_delete(
    test_client: TestClient, scan: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Subscription management never exposes or mutates another user's scan."""
    overrides = app.dependency_overrides.copy()
    overrides[resolve_current_user] = lambda: CurrentUser(
        id=uuid.uuid4(),
        email="other-edit-user@example.test",
        is_invited=True,
        is_admin=False,
        scanning_enabled=True,
    )
    monkeypatch.setattr(app, "dependency_overrides", overrides)
    path = f"/api/scans/{scan['id']}"
    assert test_client.patch(path, json={"end_date": "2027-07-09"}).status_code == 404
    assert test_client.delete(path).status_code == 404


@pytest.mark.asyncio
async def test_suspended_user_can_edit_without_resuming(
    test_client: TestClient, scan: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Suspended owners can change targets while activation remains forbidden."""
    async with maker() as session:
        owner = User(
            email=f"suspended-edit-{uuid.uuid4().hex}@example.test",
            is_invited=True,
            scanning_enabled=False,
        )
        session.add(owner)
        await session.flush()
        subscription = await session.get(UserScan, uuid.UUID(scan["id"]))
        assert subscription is not None
        subscription.user_id = owner.id
        subscription.is_active = False
        await session.commit()
    overrides = app.dependency_overrides.copy()
    overrides[resolve_current_user] = lambda: CurrentUser(
        id=owner.id,
        email=owner.email,
        is_invited=True,
        is_admin=False,
        scanning_enabled=False,
    )
    monkeypatch.setattr(app, "dependency_overrides", overrides)
    path = f"/api/scans/{scan['id']}"
    response = test_client.patch(path, json={"end_date": "2027-07-12"})
    assert response.status_code == 200
    assert response.json()["end_date"] == "2027-07-12"
    assert response.json()["is_active"] is False
    response = test_client.patch(
        path, json={"end_date": "2027-07-13", "is_active": True}
    )
    assert response.status_code == 403
    assert test_client.get(path).json()["end_date"] == "2027-07-12"


@pytest.mark.asyncio
async def test_edit_min_rv_length_omission_vs_null_clear_and_outbox_invalidation(
    test_client: TestClient, scan: dict[str, Any]
) -> None:
    """PATCH preserves min_rv_length when omitted, clears it on null, validates bounds, and skips pending outbox rows."""
    import datetime as dt

    from camply.db.models import NotificationOutbox

    path = f"/api/scans/{scan['id']}"
    set_resp = test_client.patch(path, json={"min_rv_length": 32})
    assert set_resp.status_code == 200
    assert set_resp.json()["min_rv_length"] == 32

    # Omission keeps 32
    omit_resp = test_client.patch(path, json={"require_electric": True})
    assert omit_resp.status_code == 200
    assert omit_resp.json()["min_rv_length"] == 32

    # Out-of-bounds values fail atomically
    for bad in (0, -1, 201):
        bad_resp = test_client.patch(
            path, json={"min_rv_length": bad, "require_electric": False}
        )
        assert bad_resp.status_code == 422
    assert test_client.get(path).json()["min_rv_length"] == 32

    # Seed pending outbox row and verify editing min_rv_length to None clears it & invalidates outbox
    outbox_id = uuid.uuid4()
    past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=5)
    async with maker() as session:
        sub = await session.get(UserScan, uuid.UUID(scan["id"]))
        assert sub is not None
        session.add(
            NotificationOutbox(
                id=outbox_id,
                detection_id=uuid.uuid4(),
                user_id=sub.user_id,
                scan_id=sub.id,
                target_id=sub.target_id,
                delivery_key="summary",
                channel="pushover",
                payload_kind="target",
                scan_revision=sub.definition_revision,
                payload_version=1,
                payload={},
                status="pending",
                attempt_count=0,
                created_at=past,
                next_attempt_at=past,
            )
        )
        await session.commit()

    clear_resp = test_client.patch(path, json={"min_rv_length": None})
    assert clear_resp.status_code == 200
    assert clear_resp.json()["min_rv_length"] is None
    async with maker() as session:
        row = await session.get(NotificationOutbox, outbox_id)
        assert row is not None
        assert row.status == "skipped"
        assert row.error_category == "scan_edited"
