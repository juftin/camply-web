"""Behavior shared by Celery adapters and the durable local scan runner."""

import httpx
import pytest
from sqlalchemy import select

from camply.db.config import DatabaseConfig
from camply.db.models import (
    NotificationOutbox,
    ScanResult,
    UniqueTarget,
    User,
    UserScan,
)
from camply.worker.engine.scanner import check_target

from .test_outbox import fake_provider


@pytest.mark.anyio
async def test_failed_provider_preserves_results(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
) -> None:
    """An upstream failure cannot erase previously detected availability."""
    database, target, _ = local_data
    factory = fake_provider(target)
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: factory},
        persistent=True,
    )
    factory.return_value.find_availabilities.side_effect = httpx.ConnectError(
        "synthetic"
    )
    with pytest.raises(httpx.ConnectError):
        await check_target(
            str(target.id),
            sessions=database.get_session,
            registry={1: factory},
            persistent=True,
        )
    async with database.get_session() as session:
        assert len((await session.scalars(select(ScanResult))).all()) == 1
        assert len((await session.scalars(select(NotificationOutbox))).all()) == 1


@pytest.mark.anyio
async def test_reopening_is_a_distinct_detection(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
) -> None:
    """A real closing/reopening must remain alertable after previous delivery."""
    database, target, _ = local_data
    factory = fake_provider(target)
    available = factory.return_value.find_availabilities.return_value
    factory.return_value.find_availabilities.side_effect = [available, [], available]
    for _ in range(3):
        await check_target(
            str(target.id),
            sessions=database.get_session,
            registry={1: factory},
            persistent=True,
        )
    async with database.get_session() as session:
        rows = (await session.scalars(select(NotificationOutbox))).all()
        assert len(rows) == 2
        assert rows[0].detection_id != rows[1].detection_id


@pytest.mark.anyio
async def test_one_check_fans_out_to_two_subscribers(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
) -> None:
    """Shared-target checks fan out per subscription without repeating provider I/O."""
    database, target, _ = local_data
    async with database.get_session() as session:
        user = User(email="second@example.test", pushover_token="synthetic")
        session.add(user)
        await session.flush()
        session.add(UserScan(user_id=user.id, target_id=target.id, min_stay_length=1))
        await session.commit()
    factory = fake_provider(target)
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: factory},
        persistent=True,
    )
    factory.return_value.find_availabilities.assert_awaited_once()
    async with database.get_session() as session:
        assert len((await session.scalars(select(NotificationOutbox))).all()) == 2
