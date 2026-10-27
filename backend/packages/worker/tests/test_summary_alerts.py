"""Exercise alert grouping and new-opening detection with real snapshot storage."""

import datetime
from collections.abc import AsyncIterator
from typing import Literal
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import (
    Base,
    Campground,
    Provider,
    ScanResult,
    UniqueTarget,
    User,
    UserScan,
)
from providers.dto import CampsiteDTO, CampsiteType
from worker.config import WorkerConfig
from worker.tasks import scanner


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
async def test_grouped_openings_and_reappearance(
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
    provider_mock.find_availabilities.return_value = []
    await scanner._check_target_availability_async(MagicMock(), target_id)
    dispatch.assert_not_called()
    provider_mock.find_availabilities.return_value = sites
    await scanner._check_target_availability_async(MagicMock(), target_id)
    assert dispatch.call_count == (2 if mode == "summary" else 4)
