"""Keep subscriber weekday preferences consistent through detection and delivery."""

import datetime as dt
from typing import Literal
from unittest.mock import AsyncMock, MagicMock

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
from camply.worker.engine.notifications import send_notification
from camply.worker.engine.scanner import check_target
from camply.worker.outbox import deliver_next

from .test_outbox import fake_provider

FRIDAY = dt.date(2030, 1, 4)
"""Future synthetic booking Friday, followed by Saturday and Sunday."""


async def configure_weekend(
    database: DatabaseConfig, target: UniqueTarget, scan: UserScan
) -> MagicMock:
    """Use a fixed multiweek target with a Friday-through-Sunday opening."""
    async with database.get_session() as session:
        saved_target = await session.get(UniqueTarget, target.id)
        assert saved_target is not None
        saved_target.start_date = FRIDAY - dt.timedelta(days=3)
        saved_target.end_date = FRIDAY + dt.timedelta(days=10)
        saved_scan = await session.get(UserScan, scan.id)
        assert saved_scan is not None
        saved_scan.min_stay_length = 1
        await session.commit()
    factory = fake_provider(target)
    factory.return_value.find_availabilities.return_value[0].available_dates = [
        FRIDAY + dt.timedelta(days=offset) for offset in range(3)
    ]
    return factory


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["summary", "direct"])
@pytest.mark.parametrize("persistent", [True, False])
async def test_weekday_subscribers_share_observations_and_ignore_excluded_changes(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
    mode: Literal["summary", "direct"],
    persistent: bool,
) -> None:
    """One provider check serves independent preferences without excluded-night alerts."""
    database, target, scan = local_data
    factory = await configure_weekend(database, target, scan)
    async with database.get_session() as session:
        first = await session.get(UserScan, scan.id)
        assert first is not None
        first.allowed_weekdays = [4, 5]
        first.min_stay_length = 2
        other = User(email="other-weekdays@example.test", pushover_token="synthetic")
        session.add(other)
        await session.flush()
        second = UserScan(
            user_id=other.id,
            target_id=target.id,
            allowed_weekdays=[6],
            min_stay_length=1,
        )
        session.add(second)
        await session.commit()
        second_id = second.id
    dispatch = MagicMock()
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: factory},
        persistent=persistent,
        notification_mode=mode,
        dispatch=dispatch,
    )
    factory.return_value.find_availabilities.assert_awaited_once()
    async with database.get_session() as session:
        if persistent:
            rows = (await session.scalars(select(NotificationOutbox))).all()
            alerts = {row.scan_id: row.payload for row in rows}
        else:
            alerts = {
                call.args[0].id: call.args[1].model_dump(mode="json")
                for call in dispatch.call_args_list
            }
        assert set(alerts) == {scan.id, second_id}
        for scan_id, expected in (
            (scan.id, ["2030-01-04", "2030-01-05"]),
            (second_id, ["2030-01-06"]),
        ):
            payload = alerts[scan_id]
            opening = (
                payload["metadata"]["openings"][0] if mode == "summary" else payload
            )
            assert opening["metadata"]["available_dates"] == expected
        snapshot = (await session.scalars(select(ScanResult))).one()
        assert snapshot.available_dates == ["2030-01-04", "2030-01-05", "2030-01-06"]
    dispatch.reset_mock()
    factory.return_value.find_availabilities.return_value[0].available_dates.append(
        FRIDAY + dt.timedelta(days=4)
    )
    result = await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: factory},
        persistent=persistent,
        notification_mode=mode,
        dispatch=dispatch,
    )
    assert result["notifications_sent"] == 0
    dispatch.assert_not_called()
    async with database.get_session() as session:
        if persistent:
            assert len((await session.scalars(select(NotificationOutbox))).all()) == 2


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["summary", "direct"])
@pytest.mark.parametrize("channel", ["pushover", "ntfy"])
@pytest.mark.parametrize("runtime", ["standalone", "distributed"])
@pytest.mark.parametrize("remaining", [True, False])
async def test_queued_weekday_edits_revalidate_both_runtimes_and_channels(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
    monkeypatch: pytest.MonkeyPatch,
    mode: Literal["summary", "direct"],
    channel: str,
    runtime: str,
    remaining: bool,
) -> None:
    """Pending direct and summary alerts narrow or skip under the current selection."""
    database, target, scan = local_data
    factory = await configure_weekend(database, target, scan)
    async with database.get_session() as session:
        user = await session.get(User, scan.user_id)
        assert user is not None
        user.notification_provider = channel
        user.ntfy_topic = "synthetic-topic"
        await session.commit()
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: factory},
        persistent=True,
        notification_mode=mode,
    )
    async with database.get_session() as session:
        queued = (await session.scalars(select(NotificationOutbox))).one()
        payload = queued.payload
        saved_scan = await session.get(UserScan, scan.id)
        assert saved_scan is not None
        saved_scan.allowed_weekdays = [4] if remaining else [0]
        await session.commit()
    send = AsyncMock(return_value=True)
    provider = MagicMock(send_alert=send, send_accepted=send)
    monkeypatch.setattr("camply.worker.outbox.NtfyProvider", lambda: provider)
    monkeypatch.setattr(
        "camply.worker.engine.notifications.NtfyProvider", lambda: provider
    )
    if runtime == "standalone":
        result = await deliver_next(database, send=send)
        assert result is not None
        assert result["outcome"] == ("success" if remaining else "skipped")
    else:
        result = await send_notification(
            str(scan.user_id),
            payload,
            str(scan.id),
            sessions=database.get_session,
            channel=channel,
            provider_factory=lambda: provider,
        )
        assert result["status"] == ("success" if remaining else "skipped")
    if remaining:
        send.assert_awaited_once()
        sent = (
            send.call_args.kwargs["payload"]
            if runtime == "distributed"
            else send.call_args.args[1]
        )
        opening = (
            sent.metadata["openings"][0]
            if mode == "summary"
            else sent.model_dump(mode="json")
        )
        assert opening["metadata"]["available_dates"] == ["2030-01-04"]
        assert opening["start_date"] == "2030-01-04"
        assert opening["end_date"] == "2030-01-05"
        if mode == "summary":
            assert sent.metadata["new_campsite_count"] == 1
    else:
        send.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["summary", "direct"])
async def test_distributed_retargeted_scan_skips_old_openings(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
    mode: Literal["summary", "direct"],
) -> None:
    """A queued opening remains associated with its original shared target."""
    database, target, scan = local_data
    factory = await configure_weekend(database, target, scan)
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: factory},
        persistent=True,
        notification_mode=mode,
    )
    async with database.get_session() as session:
        payload = (await session.scalars(select(NotificationOutbox))).one().payload
        other = UniqueTarget(
            provider_id=target.provider_id,
            campground_id=target.campground_id,
            start_date=FRIDAY,
            end_date=FRIDAY + dt.timedelta(days=5),
        )
        session.add(other)
        await session.flush()
        saved_scan = await session.get(UserScan, scan.id)
        assert saved_scan is not None
        saved_scan.target_id = other.id
        await session.commit()
    provider = MagicMock(send_alert=AsyncMock())
    result = await send_notification(
        str(scan.user_id),
        payload,
        str(scan.id),
        sessions=database.get_session,
        provider_factory=lambda: provider,
    )
    assert result["status"] == "skipped"
    provider.send_alert.assert_not_awaited()
