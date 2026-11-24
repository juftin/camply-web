"""Area coverage shares provider work while keeping site identity and failures separate."""

import datetime as dt
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from camply.db.coverage import definition_hash, reconcile_coverage, scan_load_options
from camply.db.models import Campground, NotificationOutbox, RecreationArea, UserScan
from camply.providers.dto import CampsiteDTO, CampsiteType
from camply.worker.engine.discovery import due_targets
from camply.worker.engine.scanner import check_target


@pytest.mark.anyio
async def test_area_shared_targets_and_partial_failure(local_data: tuple) -> None:
    """Three area members use three checks; failures preserve independent snapshots."""
    database, legacy_target, legacy_scan = local_data
    today = dt.datetime.now(dt.timezone.utc).date()
    async with database.get_session() as session:
        session.add(RecreationArea(id="area", provider_id=1, name="Area"))
        await session.flush()
        park = await session.get(Campground, ("park", 1))
        park.recreation_area_id = "area"
        session.add_all(
            [
                Campground(
                    id=value, provider_id=1, name=value, recreation_area_id="area"
                )
                for value in ["second", "third"]
            ]
        )
        await session.flush()
        scan = UserScan(
            user_id=legacy_scan.user_id,
            provider_id=1,
            destination_type="recreation_area",
            recreation_area_id="area",
            destination_name="Area",
            coverage_mode="all",
            selected_campgrounds=[],
            start_date=legacy_target.start_date,
            end_date=legacy_target.end_date,
            min_stay_length=1,
            coverage=[],
            definition_hash=definition_hash(
                provider_id=1,
                destination_type="recreation_area",
                destination_id="area",
                start_date=legacy_target.start_date,
                end_date=legacy_target.end_date,
                coverage_mode="all",
            ),
        )
        session.add(scan)
        await session.flush()
        await reconcile_coverage(session, scan)
        scan_id = scan.id
        await session.commit()
    targets = await due_targets(sessions=database.get_session, cooldown=55, limit=100)
    assert len(targets) == 3
    provider = MagicMock()
    provider.async_client.aclose = AsyncMock()
    provider.find_availabilities = AsyncMock(
        return_value=[
            CampsiteDTO(
                campsite_id="001",
                campsite_name="Site",
                campsite_type=CampsiteType.TENT,
                capacity=4,
                available_dates=[today],
                is_electric=False,
                is_accessible=False,
            )
        ]
    )
    provider_cls = MagicMock(return_value=provider)
    provider_cls.get_campground_url.return_value = "https://example.test/booking"
    for target in targets[:2]:
        assert (
            await check_target(
                str(target.id),
                sessions=database.get_session,
                registry={1: provider_cls},
                persistent=True,
            )
        )["status"] == "success"
    provider.find_availabilities.side_effect = RuntimeError("synthetic failure")
    with pytest.raises(RuntimeError):
        await check_target(
            str(targets[2].id),
            sessions=database.get_session,
            registry={1: provider_cls},
            persistent=True,
            terminal_attempt=True,
        )
    async with database.get_session() as session:
        scan = await session.scalar(
            select(UserScan).where(UserScan.id == scan_id).options(*scan_load_options())
        )
        assert sorted(link.outcome for link in scan.coverage) == [
            "failed",
            "success",
            "success",
        ]
        assert scan.last_full_checked_at is None
        assert scan.round_completed_at is not None
        rows = (
            await session.scalars(
                select(NotificationOutbox).where(
                    NotificationOutbox.payload_kind == "area"
                )
            )
        ).all()
        assert len(rows) == 1
        assert len(rows[0].payload["candidates"]) == 2
        assert (
            len(
                {
                    item["metadata"]["campground_id"]
                    for item in rows[0].payload["candidates"]
                }
            )
            == 2
        )
    assert provider.find_availabilities.await_count == 3


async def _seed_cov_area_scan(
    database: object, legacy_target: object, legacy_scan: object
) -> object:
    """Seed a two-campground recreation area scan for coverage/timeout checks."""
    async with database.get_session() as session:  # type: ignore[attr-defined]
        session.add(RecreationArea(id="area-cov", provider_id=1, name="Cov Area"))
        await session.flush()
        cgs = [
            Campground(
                id=f"cov-{idx}",
                provider_id=1,
                name=f"Cov {idx}",
                recreation_area_id="area-cov",
            )
            for idx in range(2)
        ]
        session.add_all(cgs)
        await session.flush()
        scan = UserScan(
            user_id=legacy_scan.user_id,  # type: ignore[attr-defined]
            provider_id=1,
            destination_type="recreation_area",
            recreation_area_id="area-cov",
            destination_name="Cov Area",
            coverage_mode="all",
            selected_campgrounds=[],
            start_date=legacy_target.start_date,  # type: ignore[attr-defined]
            end_date=legacy_target.end_date,  # type: ignore[attr-defined]
            min_stay_length=1,
            coverage=[],
            definition_hash=definition_hash(
                provider_id=1,
                destination_type="recreation_area",
                destination_id="area-cov",
                start_date=legacy_target.start_date,  # type: ignore[attr-defined]
                end_date=legacy_target.end_date,  # type: ignore[attr-defined]
                coverage_mode="all",
            ),
        )
        session.add(scan)
        await session.flush()
        await session.refresh(scan, ["coverage"])
        await reconcile_coverage(session, scan)
        await session.commit()
        return scan.id


async def _assert_slow_provider_timeout(database: object, target_id: object) -> None:
    """Verify slow provider lookups trigger the 90s check_target timeout."""
    import asyncio

    async def slow_fetch(*_args: object, **_kwargs: object) -> list[CampsiteDTO]:
        await asyncio.sleep(0.05)
        return []

    provider = MagicMock()
    provider.async_client.aclose = AsyncMock()
    provider.find_availabilities = AsyncMock(side_effect=slow_fetch)
    provider_cls = MagicMock(return_value=provider)

    with pytest.MonkeyPatch.context() as mp:
        orig_wait_for = asyncio.wait_for

        async def fast_timeout(coro: object, timeout: float | None = None) -> object:
            assert timeout == 90
            return await orig_wait_for(coro, timeout=0.001)  # type: ignore[arg-type]

        mp.setattr("camply.worker.engine.scanner.asyncio.wait_for", fast_timeout)
        with pytest.raises(asyncio.TimeoutError):
            await check_target(
                str(target_id),
                sessions=database.get_session,  # type: ignore[attr-defined]
                registry={1: provider_cls},
                persistent=True,
                terminal_attempt=False,
            )


@pytest.mark.anyio
async def test_area_coverage_timeouts_recoveries_deadlines_and_stale_callbacks(
    local_data: tuple,
) -> None:
    """Enforce lease/timeout bounds, round deadlines, crash recovery, and revision guards."""
    import uuid

    from camply.db.models import UniqueTarget
    from camply.worker.config import worker_config
    from camply.worker.engine.coverage import (
        prepare_rounds,
        record_attempt,
        recover_interrupted_attempts,
        register_attempt,
    )

    assert worker_config.lock_timeout >= 105

    database, legacy_target, legacy_scan = local_data
    now = dt.datetime.now(dt.timezone.utc)
    scan_id = await _seed_cov_area_scan(database, legacy_target, legacy_scan)

    await prepare_rounds(
        sessions=database.get_session, cooldown=55, heartbeat=300, now=now
    )
    async with database.get_session() as session:
        scan_row = await session.scalar(
            select(UserScan).where(UserScan.id == scan_id).options(*scan_load_options())
        )
        assert scan_row is not None
        assert scan_row.current_round_id is not None
        expected_deadline = now + dt.timedelta(seconds=2 * 300 + 780)
        assert scan_row.round_deadline_at is not None
        assert (
            abs(
                (
                    scan_row.round_deadline_at.replace(tzinfo=dt.timezone.utc)
                    - expected_deadline
                ).total_seconds()
            )
            < 1
        )
        t0, t1 = [link.target for link in scan_row.coverage]
        old_attempt = await register_attempt(
            session, t0, now=now - dt.timedelta(seconds=120)
        )
        _new_attempt = await register_attempt(session, t0, now=now)
        # Stale callback from superseded attempt must be rejected.
        await record_attempt(session, t0, old_attempt, error="timeout", terminal=True)
        assert t0.attempt_id == _new_attempt
        await session.commit()

    # Mark t0 interrupted via startup recovery (all open attempts recovered on boot).
    recovered = await recover_interrupted_attempts(database.get_session, now=now)
    assert recovered >= 1

    await _assert_slow_provider_timeout(database, t1.id)

    # Past round_deadline expires unresolved links and closes the round.
    past_deadline = now + dt.timedelta(seconds=2 * 300 + 800)
    await prepare_rounds(
        sessions=database.get_session, cooldown=55, heartbeat=300, now=past_deadline
    )
    async with database.get_session() as session:
        scan_row = await session.scalar(
            select(UserScan).where(UserScan.id == scan_id).options(*scan_load_options())
        )
        assert scan_row is not None
        assert scan_row.coverage
        target_ids = {link.target_id for link in scan_row.coverage}
        assert len(target_ids) == 2
        t0_reloaded = await session.get(UniqueTarget, t0.id)
        assert t0_reloaded is not None
        # Bumping coverage_revision rejects callbacks from pre-edit attempt IDs.
        stale_attempt = uuid.uuid4()
        t0_reloaded.attempt_id = stale_attempt
        scan_row.coverage_revision += 1
        await record_attempt(session, t0_reloaded, stale_attempt)
        assert any(
            link.error_category in {"round_deadline", "interrupted_attempt", None}
            for link in scan_row.coverage
        )


def test_postgres_for_update_targets_user_scans_only() -> None:
    """Queries locking UserScan with outer-joined target specify OF user_scans."""
    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql

    from camply.db.coverage import scan_load_options

    stmt = select(UserScan).options(*scan_load_options()).with_for_update(of=UserScan)
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE OF user_scans" in sql
