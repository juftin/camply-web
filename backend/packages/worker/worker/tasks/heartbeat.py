"""
Heartbeat: Periodic task to discover targets needing checks.
"""

import asyncio
import datetime

import structlog
from sqlalchemy import select

from db.config import db
from db.models import UniqueTarget, UserScan
from worker.celery_app import celery_app
from worker.config import worker_config

logger = structlog.getLogger(__name__)


@celery_app.task(name="worker.tasks.heartbeat.discover_targets")
def discover_targets() -> dict:
    """
    Periodic task (every 60s). Discovers UniqueTargets that are due for
    a fresh availability check and enqueues checker tasks.

    A target is "due" if:
      - It has at least one active UserScan linked.
      - Its last_checked_at is NULL (never checked) or older than
        target_cooldown seconds.

    Returns a dict with counts for observability.
    """
    try:
        return asyncio.run(_discover_targets_async())
    except Exception:
        logger.exception("Heartbeat task failed")
        return {"status": "error"}


async def _discover_targets_async() -> dict:
    """
    Async implementation of target discovery.
    """
    from datetime import timezone

    now = datetime.datetime.now(tz=timezone.utc)
    cooldown_threshold = now - datetime.timedelta(seconds=worker_config.target_cooldown)

    async with db.get_session() as session:
        # Find targets with active user scans that need checking
        stmt = (
            select(UniqueTarget)
            .join(UserScan, UserScan.target_id == UniqueTarget.id)
            .where(
                UserScan.is_active == True,  # noqa: E712
                (
                    (UniqueTarget.last_checked_at == None)  # noqa: E711
                    | (UniqueTarget.last_checked_at < cooldown_threshold)
                ),
            )
            .distinct()
        )

        result = await session.execute(stmt)
        targets = result.scalars().all()

        enqueued = 0
        for target in targets:
            celery_app.send_task(
                name="worker.tasks.scanner.check_target_availability",
                kwargs={"target_id": str(target.id)},
                queue="celery",
            )
            enqueued += 1

        logger.info(
            "Heartbeat: discovered targets",
            total=len(targets),
            enqueued=enqueued,
        )

        return {"discovered": len(targets), "enqueued": enqueued}
