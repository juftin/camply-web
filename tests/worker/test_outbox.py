"""Standalone detection and delivery must survive restarts without false success."""

import asyncio
import datetime as dt
import sqlite3
from typing import Any, Literal
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from camply.db.config import DatabaseConfig
from camply.db.models import (
    NotificationOutbox,
    ScanResult,
    UniqueTarget,
    User,
    UserScan,
)
from camply.providers.dto import CampsiteDTO, CampsiteType
from camply.worker.engine.scanner import check_target
from camply.worker.outbox import (
    MissingCredentials,
    deliver_next,
    delivery_outcome,
    prune_finished,
    recover_deliveries,
)


def fake_provider(target: UniqueTarget) -> Any:
    """Produce a synthetic adapter that exposes only the real engine contract."""
    today = dt.datetime.now(dt.timezone.utc).date()
    provider = AsyncMock()
    provider.find_availabilities.return_value = [
        CampsiteDTO(
            campsite_id="site",
            campsite_name="Synthetic site",
            campsite_type=CampsiteType.TENT,
            capacity=4,
            available_dates=[
                today - dt.timedelta(days=1),
                today,
                today + dt.timedelta(days=1),
            ],
            is_electric=False,
            is_accessible=False,
        )
    ]
    factory = MagicMock(return_value=provider)
    factory.get_campground_url.return_value = "https://example.test/book"
    return factory


@pytest.mark.anyio
async def test_atomic_detection_and_unchanged_result_dedup(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
) -> None:
    """Retain one intent per detection rather than alerting on unchanged results."""
    database, target, scan = local_data
    registry = {1: fake_provider(target)}
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry=registry,
        persistent=True,
    )
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry=registry,
        persistent=True,
    )
    async with database.get_session() as session:
        rows = (await session.scalars(select(NotificationOutbox))).all()
        assert len(rows) == 1
        assert rows[0].scan_id == scan.id


@pytest.mark.anyio
async def test_delivery_clips_expired_nights_and_requires_acceptance(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
) -> None:
    """Reapply minimum stay after the UTC cutoff, and require explicit acceptance."""
    database, target, _ = local_data
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: fake_provider(target)},
        persistent=True,
    )
    send = AsyncMock(return_value=True)
    result = await deliver_next(database, send=send)
    assert result is not None
    assert result["outcome"] == "success"
    payload = send.call_args.args[1]
    metadata = payload.metadata["openings"][0]["metadata"]
    today = dt.datetime.now(dt.timezone.utc).date()
    assert metadata["available_dates"] == [
        today.isoformat(),
        (today + dt.timedelta(days=1)).isoformat(),
    ]


@pytest.mark.anyio
async def test_edited_filters_skip_pending_alert(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
) -> None:
    """The current scan, not its detection-time filters, controls delivery."""
    database, target, scan = local_data
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: fake_provider(target)},
        persistent=True,
    )
    async with database.get_session() as session:
        current = await session.get(UserScan, scan.id)
        assert current is not None
        current.min_stay_length = 3
        await session.commit()
    send = AsyncMock(return_value=True)
    result = await deliver_next(database, send=send)
    assert result is not None and result["outcome"] == "skipped"
    send.assert_not_awaited()


@pytest.mark.anyio
async def test_accepted_delivery_survives_write_contention(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
) -> None:
    """Retry a busy acknowledgment without repeating an accepted external send."""
    database, target, _ = local_data
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: fake_provider(target)},
        persistent=True,
    )
    writer = sqlite3.connect(database.HOST)

    async def accepted(*args: object) -> bool:
        """Hold a competing writer past the connection's busy timeout."""
        writer.execute("BEGIN IMMEDIATE")
        release = asyncio.get_running_loop().call_later(1.25, writer.rollback)
        releases.append(release)
        return True

    releases: list[asyncio.TimerHandle] = []
    send = AsyncMock(side_effect=accepted)
    try:
        result = await asyncio.wait_for(deliver_next(database, send=send), timeout=4)
        assert result is not None and result["outcome"] == "success"
        send.assert_awaited_once()
        async with database.get_session() as session:
            row = (await session.scalars(select(NotificationOutbox))).one()
            assert row.status == "sent" and row.attempt_count == 1
    finally:
        for release in releases:
            release.cancel()
        writer.close()


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["summary", "direct"])
async def test_durable_alert_modes_revalidate_each_site(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
    mode: Literal["summary", "direct"],
) -> None:
    """Group durable summaries per scan and remove sites excluded before delivery."""
    database, target, scan = local_data
    provider = fake_provider(target)
    first = provider.return_value.find_availabilities.return_value[0]
    provider.return_value.find_availabilities.return_value.append(
        first.model_copy(update={"campsite_id": "electric", "is_electric": True})
    )
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: provider},
        persistent=True,
        notification_mode=mode,
        app_url="https://synthetic.example/prefix",
    )
    async with database.get_session() as session:
        rows = (await session.scalars(select(NotificationOutbox))).all()
        assert len(rows) == (1 if mode == "summary" else 2)
        if mode == "summary":
            assert rows[0].payload["metadata"]["new_campsite_count"] == 2
            assert (
                rows[0].payload["booking_url"]
                == f"https://synthetic.example/prefix/dashboard/scans/{scan.id}#results"
            )
        current = await session.get(UserScan, scan.id)
        assert current is not None
        current.require_electric = True
        await session.commit()
    send = AsyncMock(return_value=True)
    while await deliver_next(database, send=send) is not None:
        pass
    send.assert_awaited_once()
    payload = send.call_args.args[1]
    if mode == "summary":
        assert payload.metadata["new_campsite_count"] == 1
        assert payload.metadata["openings"][0]["metadata"]["campsite_id"] == "electric"
    else:
        assert payload.metadata["campsite_id"] == "electric"


@pytest.mark.anyio
async def test_failed_intent_insert_rolls_back_detection(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
) -> None:
    """A failed outbox write cannot commit results that would suppress the next alert."""
    database, target, _ = local_data
    async with database.get_session() as session:
        await session.execute(
            text(
                "CREATE TRIGGER reject_intent BEFORE INSERT ON notification_outbox BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END"
            )
        )
        await session.commit()
    with pytest.raises(IntegrityError):
        await check_target(
            str(target.id),
            sessions=database.get_session,
            registry={1: fake_provider(target)},
            persistent=True,
        )
    async with database.get_session() as session:
        assert (await session.scalars(select(ScanResult))).all() == []
        current = await session.get(UniqueTarget, target.id)
        assert current is not None and current.last_checked_at is None
        assert (await session.scalars(select(NotificationOutbox))).all() == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "status,expected", [(400, "failure"), (429, "retry"), (500, "retry")]
)
async def test_http_delivery_classification(status: int, expected: str) -> None:
    """Only rate limits and server errors qualify for another send attempt."""
    response = httpx.Response(
        status, request=httpx.Request("POST", "https://example.test")
    )
    send = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "synthetic", request=response.request, response=response
        )
    )
    outcome, _ = await delivery_outcome(send, "synthetic", MagicMock())
    assert outcome == expected


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error,expected",
    [
        (MissingCredentials(), "skipped"),
        (ValueError(), "failure"),
        (httpx.ReadTimeout("synthetic"), "retry"),
    ],
)
async def test_delivery_error_classification(error: Exception, expected: str) -> None:
    """Missing configuration and malformed responses cannot be reported as delivered."""
    outcome, _ = await delivery_outcome(
        AsyncMock(side_effect=error), "synthetic", MagicMock()
    )
    assert outcome == expected


@pytest.mark.anyio
async def test_four_send_budget_and_terminal_retention(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
) -> None:
    """Four transient failures terminate delivery and old terminal rows are pruned."""
    database, target, _ = local_data
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: fake_provider(target)},
        persistent=True,
    )
    send = AsyncMock(side_effect=httpx.ConnectError("synthetic"))
    for attempt in range(1, 5):
        result = await deliver_next(database, send=send)
        assert result is not None and result["attempt"] == attempt
        assert result["outcome"] == ("failure" if attempt == 4 else "retry")
        async with database.get_session() as session:
            row = (await session.scalars(select(NotificationOutbox))).one()
            row.next_attempt_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(
                seconds=1
            )
            await session.commit()
    assert await deliver_next(database, send=send) is None
    await prune_finished(database)
    async with database.get_session() as session:
        row = (await session.scalars(select(NotificationOutbox))).one()
        row.finished_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=25)
        await session.commit()
    await prune_finished(database)
    async with database.get_session() as session:
        assert (await session.scalars(select(NotificationOutbox))).all() == []


@pytest.mark.anyio
async def test_retry_and_interrupted_budget(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
) -> None:
    """Transient errors persist retries and interrupted attempts cannot loop forever."""
    database, target, _ = local_data
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: fake_provider(target)},
        persistent=True,
    )
    send = AsyncMock(side_effect=httpx.ConnectError("synthetic"))
    result = await deliver_next(database, send=send)
    assert result is not None and result["outcome"] == "retry"
    async with database.get_session() as session:
        row = (await session.scalars(select(NotificationOutbox))).one()
        assert row.attempt_count == 1
        row.status = "sending"
        row.attempt_count = 4
        await session.commit()
    await recover_deliveries(database)
    async with database.get_session() as session:
        row = (await session.scalars(select(NotificationOutbox))).one()
        assert row.status == "failed"
        assert row.finished_at is not None


@pytest.mark.anyio
async def test_noop_delivery_is_not_success(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
) -> None:
    """A legacy adapter returning without sending must not acknowledge an alert."""
    database, target, _ = local_data
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: fake_provider(target)},
        persistent=True,
    )
    result = await deliver_next(database, send=AsyncMock(return_value=None))
    assert result is not None and result["outcome"] == "failure"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "change", ["pause", "suspend", "delete", "uninvite", "missing_token", "relink"]
)
async def test_current_subscription_eligibility(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan], change: str
) -> None:
    """Queued delivery must honor changes made after the opening was detected."""
    database, target, scan = local_data
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: fake_provider(target)},
        persistent=True,
    )
    async with database.get_session() as session:
        current = await session.get(UserScan, scan.id)
        assert current is not None
        user = await session.get(User, current.user_id)
        assert user is not None
        if change == "pause":
            current.is_active = False
        elif change == "suspend":
            user.scanning_enabled = False
        elif change == "delete":
            await session.delete(current)
        elif change == "uninvite":
            user.is_invited = False
        elif change == "missing_token":
            user.pushover_token = None
        else:
            other = UniqueTarget(
                provider_id=target.provider_id,
                campground_id=target.campground_id,
                start_date=target.start_date,
                end_date=target.end_date + dt.timedelta(days=1),
            )
            session.add(other)
            await session.flush()
            current.target_id = other.id
        await session.commit()
    send = AsyncMock(return_value=True)
    result = await deliver_next(database, send=send, invite_only=True)
    assert result is not None and result["outcome"] == "skipped"
    send.assert_not_awaited()
