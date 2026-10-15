"""
Heartbeat: Periodic task to discover targets needing checks.
"""

import asyncio

import structlog

from db.config import db
from worker.celery_app import celery_app
from worker.config import worker_config
from worker.engine.discovery import due_targets
from worker.metrics import TARGETS_DISCOVERED_TOTAL, TARGETS_ENQUEUED_TOTAL
from worker.telemetry import record_discovery_completion

logger = structlog.getLogger(__name__)


@celery_app.task(name="camply.search.schedule_checks")
def discover_targets() -> dict:
    """
    Periodic task (defaults to every 5m / 300s). Discovers UniqueTargets that are due for
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
    targets = await due_targets(
        sessions=db.get_session, cooldown=worker_config.target_cooldown
    )
    enqueued = 0
    for target in targets:
        celery_app.send_task(
            name="camply.search.check_campsite_availability",
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

    return {
        "status": "success",
        "provider_name": "All Providers",
        "search_name": "Active Target Discovery",
        "discovered": len(targets),
        "enqueued": enqueued,
    }
