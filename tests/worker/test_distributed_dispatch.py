"""Keep shared scanning on Celery transport in the existing distributed runtime."""

import datetime as dt
from typing import Literal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import HttpUrl
from sqlalchemy import select

from camply.db.config import DatabaseConfig
from camply.db.models import (
    NotificationOutbox,
    ScanResult,
    UniqueTarget,
    User,
    UserScan,
)
from camply.worker.config import worker_config
from camply.worker.notifications.base import NotificationDTO
from camply.worker.tasks import heartbeat, scanner

from .test_outbox import fake_provider


@pytest.mark.anyio
@pytest.mark.parametrize("notification_mode", ["summary", "direct"])
@pytest.mark.parametrize("notification_provider", ["pushover", "ntfy"])
async def test_discovery_and_alerts_use_celery(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
    monkeypatch: pytest.MonkeyPatch,
    notification_mode: Literal["summary", "direct"],
    notification_provider: str,
) -> None:
    """Persist results and publish existing scan/alert contracts without local intents."""
    database, target, scan = local_data
    async with database.get_session() as session:
        user = await session.get(User, scan.user_id)
        assert user is not None
        user.notification_provider = notification_provider
        await session.commit()
    provider = fake_provider(target)
    monkeypatch.setattr(heartbeat, "db", database)
    monkeypatch.setattr(scanner, "db", database)
    monkeypatch.setattr(scanner, "PROVIDERS", {1: provider})
    monkeypatch.setattr(worker_config, "notification_mode", notification_mode)
    monkeypatch.setattr(worker_config, "app_url", HttpUrl("https://example.test/app"))
    lock = AsyncMock()
    lock.acquire.return_value = True
    task = MagicMock()

    with (
        patch.object(heartbeat.celery_app, "send_task") as publish,
        patch.object(scanner, "ValkeyLock", return_value=lock),
    ):
        discovery = await heartbeat._discover_targets_async()
        assert discovery["discovered"] == discovery["enqueued"] == 1
        publish.assert_called_once_with(
            name="search.check_availability",
            kwargs={"target_id": str(target.id)},
            queue="celery",
        )
        publish.reset_mock()

        result = await scanner._check_target_availability_async(task, str(target.id))
        assert result is not None
        assert result["status"] == "success"
        assert result["notifications_sent"] == 1
        publish.assert_called_once()
        alert = publish.call_args.kwargs
        assert alert["name"] == f"notifications.send_{notification_provider}"
        assert alert["queue"] == "celery"
        assert alert["kwargs"]["user_id"] == str(scan.user_id)
        assert alert["kwargs"]["scan_id"] == str(scan.id)
        payload = NotificationDTO.model_validate(alert["kwargs"]["notification"])
        assert payload.booking_url == (
            f"https://example.test/app/dashboard/scans/{scan.id}#results"
            if notification_mode == "summary"
            else "https://example.test/book"
        )

    provider.return_value.find_availabilities.assert_awaited_once()
    lock.acquire.assert_awaited_once_with(
        key=f"lock:target:{target.id}", timeout=worker_config.lock_timeout
    )
    lock.release.assert_awaited_once_with(key=f"lock:target:{target.id}")
    lock.close.assert_awaited_once()
    task.retry.assert_not_called()
    async with database.get_session() as session:
        assert len((await session.scalars(select(ScanResult))).all()) == 1
        stored_target = await session.get(UniqueTarget, target.id)
        assert stored_target is not None and stored_target.last_checked_at is not None
        assert (await session.scalars(select(NotificationOutbox))).all() == []


def test_area_outbox_event_driven_task_execution() -> None:
    """Area outbox is not on Beat; it drains due work and reschedules only when needed."""
    from camply.worker.celery_app import celery_app
    from camply.worker.tasks.notifications import deliver_area_outbox

    assert "area-outbox" not in celery_app.conf.beat_schedule

    with (
        patch("camply.worker.outbox.recover_deliveries", new_callable=AsyncMock) as rec,
        patch(
            "camply.worker.outbox.deliver_next",
            new_callable=AsyncMock,
            side_effect=[{"outcome": "success"}, None],
        ) as nxt,
        patch(
            "camply.worker.outbox.next_area_due",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(celery_app, "send_task") as send_task,
    ):
        result = deliver_area_outbox()
    assert result == {"delivered": 1}
    rec.assert_awaited_once()
    assert nxt.await_count == 2
    assert all(call.kwargs.get("area_only") is True for call in nxt.await_args_list)
    send_task.assert_not_called()

    retry_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=120)
    with (
        patch("camply.worker.outbox.recover_deliveries", new_callable=AsyncMock),
        patch(
            "camply.worker.outbox.deliver_next",
            new_callable=AsyncMock,
            side_effect=[{"outcome": "retry"}, None],
        ),
        patch(
            "camply.worker.outbox.next_area_due",
            new_callable=AsyncMock,
            return_value=retry_at,
        ),
        patch.object(celery_app, "send_task") as send_task,
    ):
        result = deliver_area_outbox()
    assert result == {"delivered": 1}
    send_task.assert_called_once_with(
        name="notifications.send_area_summary",
        eta=retry_at,
        queue="celery",
    )


@pytest.mark.anyio
@pytest.mark.parametrize("notification_mode", ["summary", "direct"])
async def test_area_scan_dispatches_outbox_task_on_commit(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
    monkeypatch: pytest.MonkeyPatch,
    notification_mode: Literal["summary", "direct"],
) -> None:
    """Committing a new area outbox window triggers event-driven Celery delivery."""
    from .test_area_alerts import _seed_area_scan

    database, _, _ = local_data
    _, _, targets = await _seed_area_scan(database)
    async with database.get_session() as session:
        await session.execute(ScanResult.__table__.delete())
        await session.commit()

    target_one, target_two = targets

    def area_provider(target: UniqueTarget) -> MagicMock:
        provider_factory = fake_provider(target)
        provider_factory.return_value.find_availabilities.return_value[
            0
        ].available_dates = [
            target.start_date,
            target.start_date + dt.timedelta(days=1),
        ]
        return provider_factory

    monkeypatch.setattr(scanner, "db", database)
    monkeypatch.setattr(scanner, "PROVIDERS", {1: area_provider(target_one)})
    monkeypatch.setattr(worker_config, "notification_mode", notification_mode)
    lock = AsyncMock()
    lock.acquire.return_value = True
    task = MagicMock()

    with (
        patch.object(scanner.celery_app, "send_task") as publish,
        patch.object(scanner, "ValkeyLock", return_value=lock),
    ):
        result = await scanner._check_target_availability_async(
            task, str(target_one.id)
        )

    assert result is not None
    assert result["status"] == "success"
    assert result["notifications_sent"] == 1
    publish.assert_called_once()
    call = publish.call_args.kwargs
    assert call["name"] == "notifications.send_area_summary"
    assert call["queue"] == "celery"
    if notification_mode == "summary":
        assert "eta" in call and isinstance(call["eta"], dt.datetime)
    else:
        assert "eta" not in call

    # Second campground opening in the same 5s summary window coalesces without
    # scheduling a duplicate task; direct mode dispatches a new task immediately.
    monkeypatch.setattr(scanner, "PROVIDERS", {1: area_provider(target_two)})
    with (
        patch.object(scanner.celery_app, "send_task") as publish_two,
        patch.object(scanner, "ValkeyLock", return_value=lock),
    ):
        result_two = await scanner._check_target_availability_async(
            task, str(target_two.id)
        )
    assert result_two is not None
    assert result_two["status"] == "success"
    if notification_mode == "summary":
        publish_two.assert_not_called()
    else:
        publish_two.assert_called_once_with(
            name="notifications.send_area_summary",
            queue="celery",
        )


@pytest.mark.anyio
async def test_heartbeat_recovers_overdue_area_outbox(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Heartbeat dispatches deliver_area_outbox only when overdue area rows exist."""
    import uuid

    database, target, scan = local_data
    now = dt.datetime.now(dt.timezone.utc)
    async with database.get_session() as session:
        stored_target = await session.get(UniqueTarget, target.id)
        assert stored_target is not None
        stored_target.last_checked_at = now
        session.add(
            NotificationOutbox(
                detection_id=uuid.uuid4(),
                user_id=scan.user_id,
                scan_id=scan.id,
                target_id=None,
                delivery_key="area-summary",
                channel="pushover",
                payload_kind="area",
                scan_revision=scan.definition_revision,
                payload_version=1,
                payload={"candidates": [], "direct": False},
                created_at=now - dt.timedelta(minutes=2),
                next_attempt_at=now - dt.timedelta(minutes=1),
            )
        )
        await session.commit()

    monkeypatch.setattr(heartbeat, "db", database)
    with patch.object(heartbeat.celery_app, "send_task") as publish:
        await heartbeat._discover_targets_async()

    publish.assert_called_once_with(
        name="notifications.send_area_summary",
        queue="celery",
    )
