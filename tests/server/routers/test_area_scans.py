"""Area subscriptions resolve complete catalog coverage and retain fixed choices."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from camply.db.models import Campground
from tests.server.conftest import maker, seed_data


def test_area_all_and_fixed_selection(
    test_client: TestClient, area_catalog: tuple
) -> None:
    """All mode includes 125 members while selected mode isolates a fixed subset."""
    area, members = area_catalog
    seed_data([area, *members])
    common = {
        "provider_id": 1,
        "destination_type": "recreation_area",
        "recreation_area_id": area.id,
        "start_date": "2027-07-01",
        "end_date": "2027-07-04",
    }
    response = test_client.post("/api/scans", json={**common, "coverage_mode": "all"})
    assert response.status_code == 201, response.text
    all_scan = response.json()
    assert all_scan["eligible_campground_count"] == 125
    assert all_scan["campground_id"] is None
    detail = test_client.get(f"/api/scans/{all_scan['id']}").json()
    assert len(detail["campgrounds"]) == 125
    selected = test_client.post(
        "/api/scans",
        json={
            **common,
            "coverage_mode": "selected",
            "campground_ids": [members[2].id, members[0].id, members[0].id],
        },
    )
    assert selected.status_code == 201, selected.text
    selected_id = selected.json()["id"]
    assert selected.json()["eligible_campground_count"] == 2
    duplicate = test_client.post(
        "/api/scans",
        json={
            **common,
            "coverage_mode": "selected",
            "campground_ids": [members[0].id, members[2].id],
        },
    )
    assert duplicate.status_code == 409
    assert (
        test_client.post(
            "/api/scans",
            json={**common, "coverage_mode": "selected", "campground_ids": ["cg_1"]},
        ).status_code
        == 422
    )
    choices = test_client.get(
        f"/api/rec-area/1/{area.id}/monitoring-campgrounds?limit=100&offset=100"
    ).json()
    assert choices["eligible_total"] == 125
    assert len(choices["items"]) == 25

    async def disable() -> None:
        """Simulate a complete catalog publication disabling a selected member."""
        async with maker() as session:
            member = await session.get(Campground, (members[2].id, 1))
            member.enabled = False
            await session.commit()

    asyncio.run(disable())
    detail = test_client.get(f"/api/scans/{selected_id}").json()
    assert detail["eligible_campground_count"] == 1
    assert detail["unavailable_selection_count"] == 1
    edited = test_client.patch(
        f"/api/scans/{selected_id}", json={"require_electric": True}
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["campground_ids"] == [members[0].id, members[2].id]
    assert test_client.delete(f"/api/scans/{selected_id}").status_code == 204
    assert test_client.delete(f"/api/scans/{all_scan['id']}").status_code == 204


def test_area_invalid_shapes(test_client: TestClient) -> None:
    """Conflicting destination fields and empty subsets fail before any writes."""
    common = {
        "provider_id": 1,
        "destination_type": "recreation_area",
        "recreation_area_id": "rec_area_1",
        "start_date": "2027-07-01",
        "end_date": "2027-07-04",
    }
    for extra in [
        {"coverage_mode": "selected", "campground_ids": []},
        {"coverage_mode": "selected", "campground_ids": ["does-not-exist"]},
        {"coverage_mode": "all", "campground_id": "cg_1"},
        {"coverage_mode": "all", "campground_ids": ["cg_1"]},
    ]:
        assert (
            test_client.post("/api/scans", json={**common, **extra}).status_code == 422
        )


def test_area_scan_editing_conflicts_outbox_invalidation_and_suspension(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mode switches, optimistic locking, outbox invalidation, and suspension work for areas."""
    import datetime as dt
    import uuid

    from camply.db.models import NotificationOutbox, RecreationArea, UserScan

    uid = uuid.uuid4().hex[:8]
    area = RecreationArea(id=f"area-edit-{uid}", provider_id=1, name="Editable Area")
    members = [
        Campground(
            id=f"edit-{uid}-{index:03}",
            provider_id=1,
            recreation_area_id=area.id,
            name=f"Edit Campground {index:03}",
            enabled=True,
            reservable=True,
        )
        for index in range(4)
    ]
    seed_data([area, *members])
    created = test_client.post(
        "/api/scans",
        json={
            "provider_id": 1,
            "destination_type": "recreation_area",
            "recreation_area_id": area.id,
            "coverage_mode": "all",
            "start_date": "2027-07-01",
            "end_date": "2027-07-05",
        },
    )
    assert created.status_code == 201, created.text
    scan = created.json()
    scan_id = scan["id"]

    # Switching from 'all' to 'selected' requires explicit campground_ids.
    assert (
        test_client.patch(
            f"/api/scans/{scan_id}", json={"coverage_mode": "selected"}
        ).status_code
        == 422
    )

    to_selected = test_client.patch(
        f"/api/scans/{scan_id}",
        json={
            "coverage_mode": "selected",
            "campground_ids": [members[0].id, members[1].id],
            "row_version": scan["row_version"],
        },
    )
    assert to_selected.status_code == 200, to_selected.text
    selected_scan = to_selected.json()
    assert selected_scan["coverage_mode"] == "selected"
    assert selected_scan["eligible_campground_count"] == 2
    assert selected_scan["row_version"] > scan["row_version"]

    # Stale row_version triggers 409 conflict.
    stale = test_client.patch(
        f"/api/scans/{scan_id}",
        json={"min_stay_length": 2, "row_version": scan["row_version"]},
    )
    assert stale.status_code == 409

    # Pending notification outbox entries are invalidated when scan definition changes.
    outbox_id = uuid.uuid4()

    async def seed_outbox() -> None:
        async with maker() as session:
            db_scan = await session.get(UserScan, uuid.UUID(scan_id))
            assert db_scan is not None
            session.add(
                NotificationOutbox(
                    id=outbox_id,
                    detection_id=uuid.uuid4(),
                    delivery_key=f"summary:{scan_id}",
                    channel="ntfy",
                    payload_kind="area",
                    scan_id=db_scan.id,
                    user_id=db_scan.user_id,
                    scan_revision=db_scan.definition_revision,
                    payload={"title": "Old", "message": "Stale"},
                    status="pending",
                    attempt_count=0,
                    next_attempt_at=dt.datetime.now(dt.timezone.utc),
                    created_at=dt.datetime.now(dt.timezone.utc),
                )
            )
            await session.commit()

    asyncio.run(seed_outbox())
    back_to_all = test_client.patch(
        f"/api/scans/{scan_id}",
        json={"coverage_mode": "all", "row_version": selected_scan["row_version"]},
    )
    assert back_to_all.status_code == 200, back_to_all.text
    assert back_to_all.json()["eligible_campground_count"] == 4

    async def read_outbox() -> NotificationOutbox | None:
        async with maker() as session:
            return await session.get(NotificationOutbox, outbox_id)

    row = asyncio.run(read_outbox())
    assert row is not None
    assert row.status == "skipped"
    assert row.error_category == "scan_edited"

    # Destination replacement requires complete destination fields.
    assert (
        test_client.patch(
            f"/api/scans/{scan_id}",
            json={"destination_type": "campground", "campground_id": "cg_1"},
        ).status_code
        == 422
    )
    replaced = test_client.patch(
        f"/api/scans/{scan_id}",
        json={
            "provider_id": 1,
            "destination_type": "campground",
            "campground_id": "cg_1",
        },
    )
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["destination_type"] == "campground"
    assert test_client.delete(f"/api/scans/{scan_id}").status_code == 204


def test_suspended_owner_area_scan_editing(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Suspended owners can edit paused area scan dates, but cannot reactivate."""
    import uuid

    from camply.db.models import RecreationArea, User, UserScan
    from camply.server.app import app
    from camply.server.auth import CurrentUser, resolve_current_user

    uid = uuid.uuid4().hex[:8]
    area = RecreationArea(id=f"area-susp-{uid}", provider_id=1, name="Suspended Area")
    cg = Campground(
        id=f"susp-{uid}",
        provider_id=1,
        recreation_area_id=area.id,
        name="Suspended Campground",
        enabled=True,
        reservable=True,
    )
    seed_data([area, cg])
    area_res = test_client.post(
        "/api/scans",
        json={
            "provider_id": 1,
            "destination_type": "recreation_area",
            "recreation_area_id": area.id,
            "coverage_mode": "selected",
            "campground_ids": [cg.id],
            "start_date": "2027-08-01",
            "end_date": "2027-08-05",
        },
    )
    assert area_res.status_code == 201
    susp_id = area_res.json()["id"]

    async def make_suspended_owner() -> User:
        async with maker() as session:
            owner = User(
                email=f"susp-area-{uuid.uuid4().hex}@example.test",
                is_invited=True,
                scanning_enabled=False,
            )
            session.add(owner)
            await session.flush()
            db_scan = await session.get(UserScan, uuid.UUID(susp_id))
            assert db_scan is not None
            db_scan.user_id = owner.id
            db_scan.is_active = False
            await session.commit()
            return owner

    owner = asyncio.run(make_suspended_owner())
    overrides = app.dependency_overrides.copy()
    overrides[resolve_current_user] = lambda: CurrentUser(
        id=owner.id,
        email=owner.email,
        is_invited=True,
        is_admin=False,
        scanning_enabled=False,
    )
    monkeypatch.setattr(app, "dependency_overrides", overrides)
    edit_susp = test_client.patch(
        f"/api/scans/{susp_id}", json={"end_date": "2027-08-07"}
    )
    assert edit_susp.status_code == 200
    assert edit_susp.json()["end_date"] == "2027-08-07"
    assert edit_susp.json()["is_active"] is False
    assert (
        test_client.patch(f"/api/scans/{susp_id}", json={"is_active": True}).status_code
        == 403
    )
