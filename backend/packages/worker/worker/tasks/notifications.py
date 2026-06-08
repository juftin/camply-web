"""
Notification delivery Celery tasks.
"""

import asyncio
import uuid as uuid_mod
from typing import Any

import structlog
from sqlalchemy import select

from db.config import db
from db.models import User
from worker.celery_app import celery_app
from worker.metrics import NOTIFICATIONS_SENT_TOTAL
from worker.notifications.base import NotificationDTO
from worker.notifications.pushover import PushoverProvider

logger = structlog.getLogger(__name__)


@celery_app.task(
    name="worker.tasks.notifications.send_pushover_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def send_pushover_notification(self: Any, user_id: str, notification: dict) -> dict:
    """
    Send a Pushover notification to a specific user.

    Args:
        user_id: UUID string of the User.
        notification: Serialized NotificationDTO dict.
    """
    return asyncio.run(_send_pushover_notification_async(self, user_id, notification))


async def _send_pushover_notification_async(
    self: Any, user_id: str, notification: dict
) -> dict:
    """
    Async implementation of Pushover notification delivery.
    """
    user_uuid = uuid_mod.UUID(user_id)

    async with db.get_session() as session:
        stmt = select(User).where(User.id == user_uuid)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            logger.warning("User not found", user_id=user_id)
            return {"status": "error", "reason": "user_not_found"}

        if not user.pushover_token:
            logger.info(
                "User has no pushover_token, skipping",
                user_id=user_id,
            )
            return {"status": "skipped", "reason": "no_pushover_token"}

        pushover_token = user.pushover_token

    # Reconstruct NotificationDTO from dict
    try:
        payload = NotificationDTO.model_validate(notification)
    except Exception as exc:
        logger.error(
            "Invalid notification DTO",
            user_id=str(user_id),
            error=str(exc),
        )
        return {"status": "error", "reason": str(exc)}

    provider = PushoverProvider()
    try:
        await provider.send_alert(
            user_config={"user_key": pushover_token},
            payload=payload,
        )
        NOTIFICATIONS_SENT_TOTAL.inc()
        return {"status": "success"}
    except Exception as exc:
        logger.error(
            "Pushover notification failed",
            user_id=str(user_id),
            error=str(exc),
        )
        try:
            raise self.retry(exc=exc)
        except Exception:
            return {"status": "error", "reason": str(exc)}
