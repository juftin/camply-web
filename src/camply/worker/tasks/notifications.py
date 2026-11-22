"""
Notification delivery Celery tasks.
"""

import asyncio
import datetime
from typing import Any, Optional

import structlog

from camply.db.config import db
from camply.worker.celery_app import celery_app
from camply.worker.config import worker_config
from camply.worker.engine.notifications import send_notification
from camply.worker.metrics import NOTIFICATIONS_SENT_TOTAL
from camply.worker.notifications.pushover import PushoverProvider

logger = structlog.getLogger(__name__)

AREA_OUTBOX_BATCH_SIZE = 100
("""Maximum area outbox intents consumed per Celery task invocation.""")


@celery_app.task(
    name="notifications.send_pushover",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    ignore_result=True,
)
def send_pushover_notification(
    self: Any,
    user_id: str,
    notification: dict,
    scan_id: Optional[str] = None,
) -> dict:
    """
    Send a Pushover notification to a specific user.

    Args:
        user_id: UUID string of the User.
        notification: Serialized NotificationDTO dict.
        scan_id: Optional UUID string of originating UserScan.
    """
    return asyncio.run(
        _send_pushover_notification_async(self, user_id, notification, scan_id)
    )


async def _send_pushover_notification_async(
    self: Any, user_id: str, notification: dict, scan_id: Optional[str] = None
) -> dict:
    """Apply Celery retry and metric policy around the shared delivery operation."""
    try:
        result = await send_notification(
            user_id,
            notification,
            scan_id,
            sessions=db.get_session,
            provider_factory=PushoverProvider,
        )
        if result["status"] == "success":
            NOTIFICATIONS_SENT_TOTAL.inc()
        return result
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except Exception:
            return {"status": "error", "reason": str(exc)}


@celery_app.task(
    name="notifications.send_ntfy",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    ignore_result=True,
)
def send_ntfy_notification(
    self: Any,
    user_id: str,
    notification: dict,
    scan_id: Optional[str] = None,
) -> dict:
    """Deliver ntfy independently of the legacy Pushover task."""
    try:
        result = asyncio.run(
            send_notification(
                user_id,
                notification,
                scan_id,
                sessions=db.get_session,
                channel="ntfy",
            )
        )
        if result["status"] == "success":
            NOTIFICATIONS_SENT_TOTAL.inc()
        return result
    except Exception:
        raise self.retry(exc=RuntimeError("ntfy delivery failed")) from None


@celery_app.task(name="notifications.send_area_summary", ignore_result=True)
def deliver_area_outbox() -> dict:
    """Consume bounded area work on demand and reschedule only if work remains."""
    from camply.worker.outbox import deliver_next, next_area_due, recover_deliveries

    async def consume() -> tuple[int, datetime.datetime | None]:
        """Recover expired claims, process a bounded page, and check remaining work."""
        await recover_deliveries(db)
        count = 0
        for _ in range(AREA_OUTBOX_BATCH_SIZE):
            result = await deliver_next(
                db, invite_only=worker_config.invite_only, area_only=True
            )
            if result is None:
                break
            if result["outcome"] == "success":
                NOTIFICATIONS_SENT_TOTAL.inc()
            count += 1
        return count, await next_area_due(db)

    delivered, next_due = asyncio.run(consume())
    if next_due is not None:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        if next_due.tzinfo is None:
            next_due = next_due.replace(tzinfo=datetime.timezone.utc)
        if next_due <= now and delivered >= AREA_OUTBOX_BATCH_SIZE:
            celery_app.send_task(
                name="notifications.send_area_summary",
                queue="celery",
            )
        else:
            eta = max(next_due, now + datetime.timedelta(seconds=1))
            celery_app.send_task(
                name="notifications.send_area_summary",
                eta=eta,
                queue="celery",
            )
    return {"delivered": delivered}
