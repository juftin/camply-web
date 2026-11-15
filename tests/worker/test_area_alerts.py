"""Area notification coalescing, durable outbox delivery, retries, and revalidation."""

import datetime as dt
import uuid
from unittest.mock import AsyncMock

import httpx2
import pytest
from sqlalchemy import select, update

from camply.db.coverage import definition_hash, reconcile_coverage
from camply.db.models import (
    Campground,
    NotificationOutbox,
    RecreationArea,
    ScanResult,
    UniqueTarget,
    User,
    UserScan,
)
from camply.worker.engine.area_alerts import (
    current_area_payload,
    enqueue_area,
    summary,
)
from camply.worker.notifications.base import NotificationDTO
from camply.worker.outbox import deliver_next, recover_deliveries


async def _seed_area_scan(
    database: object,
) -> tuple[User, UserScan, list[UniqueTarget]]:
    """Create one active ntfy area scan covering two live campgrounds."""
    start = dt.date(2027, 7, 1)
    end = dt.date(2027, 7, 5)
    async with database.get_session() as session:  # type: ignore[attr-defined]
        user = await session.scalar(select(User))
        assert user is not None
        user.notification_provider = "ntfy"
        user.ntfy_topic = "area-alerts-topic"
        session.add(RecreationArea(id="area", provider_id=1, name="Summary Basin"))
        await session.flush()
        park = await session.get(Campground, ("park", 1))
        assert park is not None
        park.recreation_area_id = "area"
        cg2 = Campground(
            id="second", provider_id=1, name="Second Basin", recreation_area_id="area"
        )
        session.add(cg2)
        await session.flush()
        scan = UserScan(
            user_id=user.id,
            provider_id=1,
            destination_type="recreation_area",
            recreation_area_id="area",
            destination_name="Summary Basin",
            coverage_mode="all",
            selected_campgrounds=[],
            start_date=start,
            end_date=end,
            min_stay_length=1,
            coverage=[],
            definition_hash=definition_hash(
                provider_id=1,
                destination_type="recreation_area",
                destination_id="area",
                start_date=start,
                end_date=end,
                coverage_mode="all",
            ),
        )
        session.add(scan)
        await session.flush()
        await session.refresh(scan, ["coverage"])
        await reconcile_coverage(session, scan)
        await session.flush()
        targets = [link.target for link in scan.coverage]
        targets.sort(key=lambda t: t.campground_id)
        for target in targets:
            session.add(
                ScanResult(
                    target_id=target.id,
                    campsite_id="001",
                    campsite_name=f"Site 1 ({target.campground_id})",
                    campsite_type="TENT",
                    is_electric=False,
                    is_accessible=False,
                    available_dates=["2027-07-01", "2027-07-02"],
                )
            )
        await session.commit()
        return user, scan, targets


def _opening(
    campground_name: str, *, target_id: str, campground_id: str
) -> NotificationDTO:
    """Build one synthetic campsite opening DTO with area attribution metadata."""
    return NotificationDTO(
        title=f"Campsite Available: {campground_name}",
        message="Site 001 is available.",
        booking_url=f"https://example.test/cg/{campground_id}",
        park_name=campground_name,
        campsite_name="Site 001",
        start_date=dt.date(2027, 7, 1),
        end_date=dt.date(2027, 7, 5),
        metadata={
            "target_id": target_id,
            "provider_id": 1,
            "campground_id": campground_id,
            "campsite_id": "001",
            "campsite_type": "TENT",
            "is_electric": False,
            "is_accessible": False,
            "available_dates": ["2027-07-01", "2027-07-02"],
        },
    )


@pytest.mark.anyio
async def test_area_summary_vs_direct_and_window_coalescing(local_data: tuple) -> None:
    """Coalesce same-window observations, split expired windows, and keep direct separate."""
    database, _, _ = local_data
    _, scan, targets = await _seed_area_scan(database)
    o1 = _opening(
        "Park", target_id=str(targets[0].id), campground_id=targets[0].campground_id
    )
    o2 = _opening(
        "Second Basin",
        target_id=str(targets[1].id),
        campground_id=targets[1].campground_id,
    )

    agg = summary([o1, o2], scan, app_url="https://camply.test/")
    assert agg.metadata["new_campsite_count"] == 2
    assert "2 new campsites: Summary Basin" == agg.title
    assert "2 campgrounds" in agg.message
    assert agg.booking_url == f"https://camply.test/dashboard/scans/{scan.id}#results"

    base_now = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=30)
    window_start = dt.datetime.fromtimestamp(
        int(base_now.timestamp()) // 5 * 5 + 1, dt.timezone.utc
    )
    async with database.get_session() as session:
        await enqueue_area(
            session, scan, targets[0], [o1], channel="ntfy", now=window_start
        )
        await enqueue_area(
            session,
            scan,
            targets[1],
            [o2],
            channel="ntfy",
            now=window_start + dt.timedelta(seconds=2),
        )
        await session.commit()

    async with database.get_session() as session:
        rows = (
            await session.scalars(
                select(NotificationOutbox).where(
                    NotificationOutbox.payload_kind == "area"
                )
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].delivery_key == "area-summary"
        assert rows[0].payload_version == 2
        assert len(rows[0].payload["candidates"]) == 2

        # Appending in a subsequent window creates a distinct outbox row without mutating sealed rows.
        await enqueue_area(
            session,
            scan,
            targets[0],
            [o1],
            channel="ntfy",
            now=window_start + dt.timedelta(seconds=6),
        )
        # Direct mode enqueues immediate individual rows.
        await enqueue_area(
            session,
            scan,
            targets[0],
            [o1],
            channel="ntfy",
            now=window_start,
            direct=True,
        )
        await session.commit()

    async with database.get_session() as session:
        rows = (
            await session.scalars(
                select(NotificationOutbox).where(
                    NotificationOutbox.payload_kind == "area"
                )
            )
        ).all()
        assert len(rows) == 3
        direct_rows = [row for row in rows if row.payload.get("direct") is True]
        assert len(direct_rows) == 1
        assert direct_rows[0].delivery_key == f"1:{targets[0].campground_id}:001"


@pytest.mark.anyio
async def test_area_outbox_claim_retry_crash_recovery_and_sealed_append(
    local_data: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Transient errors retry, expired sending leases recover, and claimed windows stay sealed."""
    from camply.notifications.ntfy import NtfyProvider

    database, _, _ = local_data
    _, scan, targets = await _seed_area_scan(database)
    o1 = _opening(
        "Park", target_id=str(targets[0].id), campground_id=targets[0].campground_id
    )
    o2 = _opening(
        "Second Basin",
        target_id=str(targets[1].id),
        campground_id=targets[1].campground_id,
    )

    due_now = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=10)
    async with database.get_session() as session:
        await enqueue_area(session, scan, targets[0], [o1], channel="ntfy", now=due_now)
        # Enqueuing into an already-sealed past window moves forward cleanly without crashing.
        await enqueue_area(
            session,
            scan,
            targets[1],
            [o2],
            channel="ntfy",
            now=due_now,
        )
        await session.commit()

    failing_send = AsyncMock(side_effect=httpx2.ConnectError("transient failure"))
    monkeypatch.setattr(NtfyProvider, "send_accepted", failing_send)
    retry_res = await deliver_next(database, area_only=True)
    assert retry_res is not None
    assert retry_res["outcome"] == "retry"
    assert retry_res["entity_type"] == "scan"
    assert retry_res["entity_id"] == str(scan.id)

    # Simulate worker crash leaving the row claimed in 'sending' with an expired 45s lease.
    async with database.get_session() as session:
        await session.execute(
            update(NotificationOutbox)
            .where(NotificationOutbox.scan_id == scan.id)
            .values(
                status="sending",
                next_attempt_at=dt.datetime.now(dt.timezone.utc)
                - dt.timedelta(seconds=5),
            )
        )
        await session.commit()

    await recover_deliveries(database)
    async with database.get_session() as session:
        recovered_row = await session.scalar(
            select(NotificationOutbox).where(NotificationOutbox.scan_id == scan.id)
        )
        assert recovered_row is not None
        assert recovered_row.status == "retry"
        await session.execute(
            update(NotificationOutbox)
            .where(NotificationOutbox.scan_id == scan.id)
            .values(
                next_attempt_at=dt.datetime.now(dt.timezone.utc)
                - dt.timedelta(seconds=1)
            )
        )
        await session.commit()

    ok_send = AsyncMock(return_value=True)
    monkeypatch.setattr(NtfyProvider, "send_accepted", ok_send)
    started = dt.datetime.now(dt.timezone.utc)
    delivered = await deliver_next(database, area_only=True)
    elapsed_s = (dt.datetime.now(dt.timezone.utc) - started).total_seconds()
    assert delivered is not None
    assert delivered["outcome"] == "success"
    assert elapsed_s < 60
    ok_send.assert_awaited_once()


@pytest.mark.anyio
async def test_area_outbox_pre_send_revalidation_filters_and_skips(
    local_data: tuple,
) -> None:
    """Revalidation drops disabled/unmatched sites and skips edited, paused, or suspended scans."""
    database, _, _ = local_data
    user, scan, targets = await _seed_area_scan(database)
    o1 = _opening(
        "Park", target_id=str(targets[0].id), campground_id=targets[0].campground_id
    )
    o2 = _opening(
        "Second Basin",
        target_id=str(targets[1].id),
        campground_id=targets[1].campground_id,
    )

    past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=10)
    row_id = uuid.uuid4()
    async with database.get_session() as session:
        session.add(
            NotificationOutbox(
                id=row_id,
                detection_id=uuid.uuid4(),
                user_id=user.id,
                scan_id=scan.id,
                target_id=None,
                delivery_key="area-summary",
                channel="ntfy",
                payload_kind="area",
                scan_revision=scan.definition_revision,
                payload_version=1,
                payload={
                    "candidates": [
                        o1.model_dump(mode="json"),
                        o2.model_dump(mode="json"),
                    ],
                    "direct": False,
                },
                status="pending",
                attempt_count=0,
                created_at=past,
                next_attempt_at=past,
            )
        )
        # Disable second campground before delivery: only Park should survive revalidation.
        cg2 = await session.get(Campground, (targets[1].campground_id, 1))
        assert cg2 is not None
        cg2.enabled = False
        await session.commit()

        row = await session.get(NotificationOutbox, row_id)
        assert row is not None
        filtered = await current_area_payload(
            session, row, today=dt.date(2027, 7, 1), app_url="https://camply.test"
        )
        assert filtered is not None
        assert filtered.metadata["new_campsite_count"] == 1

        # Revision mismatch invalidates stale payload completely.
        row.scan_revision = scan.definition_revision - 1
        assert (
            await current_area_payload(
                session, row, today=dt.date(2027, 7, 1), app_url="https://camply.test"
            )
            is None
        )
        row.scan_revision = scan.definition_revision

        # Paused scan causes deliver_next to mark skipped without calling sender.
        db_scan = await session.get(UserScan, scan.id)
        assert db_scan is not None
        db_scan.is_active = False
        await session.commit()

    send = AsyncMock(return_value=True)
    res = await deliver_next(database, send=send, area_only=True)
    assert res is not None
    assert res["outcome"] == "skipped"
    send.assert_not_awaited()
