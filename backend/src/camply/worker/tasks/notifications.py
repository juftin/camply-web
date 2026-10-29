"""
Notification delivery Celery tasks.
"""

import asyncio
from typing import Any, Optional

import structlog

from camply.db.config import db
from camply.worker.celery_app import celery_app
from camply.worker.engine.notifications import send_notification
from camply.worker.metrics import NOTIFICATIONS_SENT_TOTAL
from camply.worker.notifications.pushover import PushoverProvider

logger = structlog.getLogger(__name__)


@celery_app.task(
    name="camply.notifications.send_pushover_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
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
