"""Exercise alert grouping and new-opening detection with real snapshot storage."""

import datetime
import uuid
from collections.abc import AsyncIterator
from typing import Literal
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from camply.db.models import (
    Base,
    Campground,
    Provider,
    ScanResult,
    UniqueTarget,
    User,
    UserScan,
)
from camply.providers.dto import CampsiteDTO, CampsiteType
from camply.worker.config import WorkerConfig
from camply.worker.tasks import scanner


@pytest.fixture
async def scanner_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[
    tuple[
        async_sessionmaker[AsyncSession],
        str,
        list[str],
        list[CampsiteDTO],
        MagicMock,
        MagicMock,
    ]
]:
    """Isolate database storage and external effects for scanner regressions."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with maker() as session:
        provider = Provider(id=1, name="Synthetic provider", url="https://book.example")
        campground = Campground(id="camp", provider_id=1, name="Synthetic Camp")
        target = UniqueTarget(
            provider_id=1,
            campground_id="camp",
            start_date=datetime.date(2027, 7, 1),
            end_date=datetime.date(2027, 7, 6),
        )
        users = [User(email=f"camper-{i}@example.com") for i in range(4)]
        session.add_all([provider, campground, target, *users])
        await session.flush()
        scans = [
            UserScan(user_id=user.id, target_id=target.id, min_stay_length=2)
            for user in users
        ]
        scans[1].require_electric = True
        scans[2].is_active = False
        users[3].scanning_enabled = False
        session.add_all(scans)
        await session.commit()
        target_id = str(target.id)
        scan_ids = [str(scan.id) for scan in scans]

    sites = [
        CampsiteDTO(
            campsite_id=f"site-{i}",
            campsite_name=f"Site {i}",
            campsite_type=CampsiteType.TENT,
            capacity=6,
            available_dates=[datetime.date(2027, 7, 1), datetime.date(2027, 7, 2)],
            is_electric=i == 0,
            is_accessible=False,
        )
        for i in range(3)
    ]
    provider_mock = MagicMock()
    provider_mock.find_availabilities = AsyncMock(return_value=sites)
    provider_mock.async_client.aclose = AsyncMock()
    provider_class = MagicMock(return_value=provider_mock)
    provider_class.get_campground_url.return_value = "https://book.example/camp"
    lock = AsyncMock()
    lock.acquire.return_value = True
    dispatch = MagicMock()
    monkeypatch.setattr(scanner, "db", MagicMock(get_session=maker))
    monkeypatch.setattr(scanner, "ValkeyLock", MagicMock(return_value=lock))
    monkeypatch.setitem(scanner.PROVIDERS, 1, provider_class)
    monkeypatch.setattr(scanner.celery_app, "send_task", dispatch)
    try:
        yield maker, target_id, scan_ids, sites, provider_mock, dispatch
    finally:
        await engine.dispose()


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["summary", "direct"])
async def test_grouped_openings_and_reappearance(  # noqa: PLR0915
    monkeypatch: pytest.MonkeyPatch,
    mode: Literal["summary", "direct"],
    scanner_setup: tuple[
        async_sessionmaker[AsyncSession],
        str,
        list[str],
        list[CampsiteDTO],
        MagicMock,
        MagicMock,
    ],
) -> None:
    """Group new sites per subscriber; unchanged or too-short openings stay quiet."""
    maker, target_id, scan_ids, sites, provider_mock, dispatch = scanner_setup
    monkeypatch.setattr(
        scanner,
        "worker_config",
        WorkerConfig(
            notification_mode=mode,
            app_url=HttpUrl("https://camply.example/prefix/"),
        ),
    )
    result = await scanner._check_target_availability_async(MagicMock(), target_id)
    assert result is not None and result["status"] == "success", result
    assert dispatch.call_count == (2 if mode == "summary" else 4)
    alerts = [call.kwargs["kwargs"] for call in dispatch.call_args_list]
    assert {alert["scan_id"] for alert in alerts} == set(scan_ids[:2])
    for alert in alerts:
        payload = alert["notification"]
        if mode == "summary":
            assert payload["booking_url"] == (
                f"https://camply.example/prefix/dashboard/scans/{alert['scan_id']}#results"
            )
            assert payload["url_title"] == "View campsites"
            expected = 3 if alert["scan_id"] == scan_ids[0] else 1
            assert payload["metadata"]["new_campsite_count"] == expected
        else:
            assert payload["booking_url"] == "https://book.example/camp"
            assert payload["url_title"] == "Book Now"
    async with maker() as session:
        stored = (await session.scalars(select(ScanResult))).all()
        assert {site.campsite_name for site in stored} == {
            "Site 0",
            "Site 1",
            "Site 2",
        }
    dispatch.reset_mock()
    await scanner._check_target_availability_async(MagicMock(), target_id)
    dispatch.assert_not_called()
    for site in sites:
        site.available_dates.append(datetime.date(2027, 7, 4))
    await scanner._check_target_availability_async(MagicMock(), target_id)
    dispatch.assert_not_called()
    for site in sites:
        site.available_dates.append(datetime.date(2027, 7, 3))
    await scanner._check_target_availability_async(MagicMock(), target_id)
    assert dispatch.call_count == (2 if mode == "summary" else 4)
    dispatch.reset_mock()
    async with maker() as session:
        checked_at = (await session.scalars(select(UniqueTarget))).one().last_checked_at
    provider_mock.find_availabilities.side_effect = RuntimeError("Provider unavailable")
    task = MagicMock()
    task.request.retries = 0
    task.retry.side_effect = RuntimeError("retry requested")
    with pytest.raises(RuntimeError, match="retry requested"):
        await scanner._check_target_availability_async(task, target_id)
    task.retry.assert_called_once()
    dispatch.assert_not_called()
    async with maker() as session:
        assert len((await session.scalars(select(ScanResult))).all()) == 3
        assert (
            await session.scalars(select(UniqueTarget))
        ).one().last_checked_at == checked_at
    provider_mock.find_availabilities.side_effect = None
    provider_mock.find_availabilities.return_value = []
    cleared = await scanner._check_target_availability_async(MagicMock(), target_id)
    assert cleared is not None and cleared["status"] == "success"
    dispatch.assert_not_called()
    async with maker() as session:
        assert (await session.scalars(select(ScanResult))).all() == []
    provider_mock.find_availabilities.return_value = sites
    await scanner._check_target_availability_async(MagicMock(), target_id)
    assert dispatch.call_count == (2 if mode == "summary" else 4)


@pytest.mark.anyio
@pytest.mark.parametrize("remaining_nights", [0, 1, 2])
@pytest.mark.parametrize("mode", ["summary", "direct"])
async def test_alerts_only_use_remaining_nights(
    monkeypatch: pytest.MonkeyPatch,
    remaining_nights: int,
    mode: Literal["summary", "direct"],
    scanner_setup: tuple[
        async_sessionmaker[AsyncSession],
        str,
        list[str],
        list[CampsiteDTO],
        MagicMock,
        MagicMock,
    ],
) -> None:
    """Expired nights cannot make a provider opening qualify for an alert."""
    maker, target_id, _, sites, _, dispatch = scanner_setup
    monkeypatch.setattr(scanner, "worker_config", WorkerConfig(notification_mode=mode))
    today = datetime.datetime.now(tz=datetime.timezone.utc).date()
    yesterday = today - datetime.timedelta(days=1)
    current_dates = [
        today + datetime.timedelta(days=offset) for offset in range(remaining_nights)
    ]
    checkout = today + datetime.timedelta(days=3)
    async with maker() as session:
        target = await session.get(UniqueTarget, uuid.UUID(target_id))
        assert target is not None
        target.start_date = yesterday
        target.end_date = checkout
        await session.commit()
    for site in sites:
        site.available_dates = [
            yesterday,
            *current_dates,
            checkout,
            checkout + datetime.timedelta(days=1),
        ]

    result = await scanner._check_target_availability_async(MagicMock(), target_id)
    assert result is not None and result["status"] == "success"
    expected_alerts = 2 if mode == "summary" else 4
    assert dispatch.call_count == (expected_alerts if remaining_nights == 2 else 0)
    async with maker() as session:
        stored = (await session.scalars(select(ScanResult))).all()
        assert len(stored) == (3 if current_dates else 0)
        assert all(
            row.available_dates == [night.isoformat() for night in current_dates]
            for row in stored
        )


@pytest.mark.anyio
async def test_worker_persists_equipment_and_enforces_min_rv_length(
    monkeypatch: pytest.MonkeyPatch,
    scanner_setup: tuple[
        async_sessionmaker[AsyncSession],
        str,
        list[str],
        list[CampsiteDTO],
        MagicMock,
        MagicMock,
    ],
) -> None:
    """Scanner persists permitted_equipment/max_vehicle_length, isolates subscriber alerts, and safely revalidates legacy metadata."""
    from camply.worker.engine.alerts import matching_opening
    from camply.worker.notifications.base import NotificationDTO

    maker, target_id, scan_ids, sites, _, dispatch = scanner_setup
    monkeypatch.setattr(
        scanner, "worker_config", WorkerConfig(notification_mode="summary")
    )
    sites[0] = sites[0].model_copy(
        update={
            "campsite_type": CampsiteType.RV,
            "permitted_equipment": ["RV", "Trailer"],
            "max_vehicle_length": 34,
        }
    )
    sites[1] = sites[1].model_copy(
        update={
            "campsite_type": CampsiteType.RV,
            "permitted_equipment": ["RV"],
            "max_vehicle_length": 22,
        }
    )
    sites[2] = sites[2].model_copy(
        update={
            "campsite_type": CampsiteType.TENT,
            "permitted_equipment": ["Tent"],
            "max_vehicle_length": None,
        }
    )
    async with maker() as session:
        scan_long = await session.get(UserScan, uuid.UUID(scan_ids[0]))
        assert scan_long is not None
        scan_long.min_rv_length = 30
        scan_long.require_accessible = True
        await session.commit()

    sites[0] = sites[0].model_copy(update={"is_accessible": True})
    await scanner._check_target_availability_async(MagicMock(), target_id)
    async with maker() as session:
        stored = {
            row.campsite_id: row
            for row in (await session.scalars(select(ScanResult))).all()
        }
        assert stored["site-0"].max_vehicle_length == 34
        assert stored["site-0"].permitted_equipment == ["RV", "Trailer"]
        assert stored["site-1"].max_vehicle_length == 22
        assert stored["site-2"].max_vehicle_length is None

    alerts = [call.kwargs["kwargs"] for call in dispatch.call_args_list]
    long_alert = next(a for a in alerts if a["scan_id"] == scan_ids[0])
    openings = long_alert["notification"]["metadata"]["openings"]
    assert len(openings) == 1
    assert openings[0]["metadata"]["max_vehicle_length"] == 34
    assert openings[0]["metadata"]["permitted_equipment"] == ["RV", "Trailer"]

    # Legacy outbox payload without max_vehicle_length / permitted_equipment / is_accessible keys
    legacy_payload = NotificationDTO(
        title="Opening",
        message="Opening",
        booking_url="https://book.example",
        park_name="Camp",
        campsite_name="Legacy",
        start_date=datetime.date(2027, 7, 1),
        end_date=datetime.date(2027, 7, 3),
        metadata={
            "target_id": target_id,
            "campsite_id": "site-legacy",
            "campsite_type": "RV",
            "is_electric": True,
            "available_dates": ["2027-07-01", "2027-07-02"],
        },
    )
    today = datetime.date(2027, 6, 1)
    target = UniqueTarget(
        id=uuid.UUID(target_id),
        start_date=datetime.date(2027, 7, 1),
        end_date=datetime.date(2027, 7, 6),
    )
    assert (
        matching_opening(
            legacy_payload, UserScan(min_stay_length=1), target, today=today
        )
        is not None
    )
    assert (
        matching_opening(
            legacy_payload,
            UserScan(min_stay_length=1, min_rv_length=25),
            target,
            today=today,
        )
        is None
    )
    assert (
        matching_opening(
            legacy_payload,
            UserScan(min_stay_length=1, require_accessible=True),
            target,
            today=today,
        )
        is None
    )
