"""Keep shared scanning on Celery transport in the existing distributed runtime."""

from typing import Literal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import HttpUrl
from sqlalchemy import select

from db.config import DatabaseConfig
from db.models import NotificationOutbox, ScanResult, UniqueTarget, UserScan
from worker.config import worker_config
from worker.notifications.base import NotificationDTO
from worker.tasks import heartbeat, scanner

from .test_outbox import fake_provider


@pytest.mark.anyio
@pytest.mark.parametrize("notification_mode", ["summary", "direct"])
async def test_discovery_and_alerts_use_celery(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
    monkeypatch: pytest.MonkeyPatch,
    notification_mode: Literal["summary", "direct"],
) -> None:
    """Persist results and publish existing scan/alert contracts without local intents."""
    database, target, scan = local_data
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
            name="camply.search.check_campsite_availability",
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
        assert alert["name"] == "camply.notifications.send_pushover_notification"
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
