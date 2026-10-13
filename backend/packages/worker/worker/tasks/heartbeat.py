"""
Heartbeat: Periodic task to discover targets needing checks.
"""

import asyncio
import datetime

import structlog
from sqlalchemy import select

from db.config import db
from db.eligibility import eligible_scan_condition
from db.models import UniqueTarget, User, UserScan
from worker.celery_app import celery_app
from worker.config import worker_config
from worker.metrics import TARGETS_DISCOVERED_TOTAL, TARGETS_ENQUEUED_TOTAL
from worker.telemetry import record_discovery_completion

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
        result = asyncio.run(_discover_targets_async())
        record_discovery_completion(
            targets_discovered=result.get("discovered", 0),
            targets_enqueued=result.get("enqueued", 0),
            status="success",
        )
        return result
    except Exception:
        logger.exception("Heartbeat task failed")
        record_discovery_completion(
            targets_discovered=0,
            targets_enqueued=0,
            status="error",
        )
        return {"status": "error"}


async def _discover_targets_async() -> dict:
    """
    Async implementation of target discovery.
    """
    from datetime import timezone

    now = datetime.datetime.now(tz=timezone.utc)
    cooldown_threshold = now - datetime.timedelta(seconds=worker_config.target_cooldown)

    async with db.get_session() as session:
        # Find targets with eligible user scans that need checking
        stmt = (
            select(UniqueTarget)
            .join(UserScan, UserScan.target_id == UniqueTarget.id)
            .join(User, User.id == UserScan.user_id)
            .where(
                eligible_scan_condition(),
                (
                    (UniqueTarget.last_checked_at.is_(None))
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

        TARGETS_DISCOVERED_TOTAL.inc(len(targets))
        TARGETS_ENQUEUED_TOTAL.inc(enqueued)

        return {"discovered": len(targets), "enqueued": enqueued}
