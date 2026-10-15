"""
Scanner: check_target_availability Celery task.
"""

import asyncio
from typing import Any, Optional

import structlog

from db.config import db
from db.models import UserScan
from providers import PROVIDERS
from worker.celery_app import celery_app
from worker.config import worker_config
from worker.engine.scanner import _longest_consecutive as _longest_consecutive
from worker.engine.scanner import _matches_scan_filters as _matches_scan_filters
from worker.engine.scanner import check_target
from worker.locks import ValkeyLock
from worker.metrics import (
    CAMPGROUND_API_ERRORS_TOTAL,
    LOCK_CONTENTION_TOTAL,
    PROVIDER_CHECKS_TOTAL,
    SCAN_RESULTS_STORED_TOTAL,
    TARGETS_CHECKED_TOTAL,
    UNIQUE_TARGETS_CHECKED,
)
from worker.notifications.base import NotificationDTO

logger = structlog.getLogger(__name__)


def _record_provider_result(provider_id: int, success: bool) -> None:
    """Retain distributed check/error instrumentation outside the common engine."""
    TARGETS_CHECKED_TOTAL.inc()
    UNIQUE_TARGETS_CHECKED.inc()
    PROVIDER_CHECKS_TOTAL.labels(
        provider=str(provider_id), status="success" if success else "error"
    ).inc()
    if not success:
        CAMPGROUND_API_ERRORS_TOTAL.labels(provider=str(provider_id)).inc()


def _dispatch_notification(scan: UserScan, opening: NotificationDTO) -> None:
    """Send the existing Celery notification contract after result commit."""
    celery_app.send_task(
        name="camply.notifications.send_pushover_notification",
        kwargs={
            "user_id": str(scan.user_id),
            "notification": opening.model_dump(mode="json"),
            "scan_id": str(scan.id),
        },
        queue="celery",
    )


@celery_app.task(
    name="camply.search.check_campsite_availability",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def check_target_availability(self: Any, target_id: str) -> Optional[dict]:
    """
    Check campsite availability for a single UniqueTarget.

    1. Acquire Valkey distributed lock for this target.
    2. Load target + campground from DB.
    3. Instantiate the correct provider and call find_availabilities.
    4. Diff results against existing ScanResults to find new openings.
    5. Store new ScanResults.
    6. Fan out matching UserScans to notification tasks.
    7. Release lock and update last_checked_at.

    Args:
        target_id: UUID string of the UniqueTarget.
    """
    return asyncio.run(_check_target_availability_async(self, target_id))


async def _check_target_availability_async(self: Any, target_id: str) -> Optional[dict]:
    lock_key = f"lock:target:{target_id}"
    lock = ValkeyLock(valkey_url=worker_config.valkey_url)

    try:
        acquired = await lock.acquire(key=lock_key, timeout=worker_config.lock_timeout)
    except Exception:
        logger.warning(
            "Could not connect to Valkey for lock, skipping",
            target_id=target_id,
        )
        LOCK_CONTENTION_TOTAL.labels(outcome="error").inc()
        return {"status": "skipped", "reason": "valkey_unavailable"}

    if not acquired:
        logger.info("Lock not acquired, skipping", target_id=target_id)
        LOCK_CONTENTION_TOTAL.labels(outcome="skipped").inc()
        return {"status": "skipped", "reason": "lock_held"}

    LOCK_CONTENTION_TOTAL.labels(outcome="acquired").inc()

    try:
        result = await check_target(
            target_id,
            sessions=db.get_session,
            registry=PROVIDERS,
            dispatch=_dispatch_notification,
            on_provider_result=_record_provider_result,
        )
        if result["status"] == "success":
            SCAN_RESULTS_STORED_TOTAL.inc(result["availabilities_found"])
        return result

    except Exception as exc:
        logger.error(
            "Scanner task failed",
            target_id=target_id,
            error=str(exc),
        )
        try:
            raise self.retry(exc=exc)
        except Exception:
            # If retry fails (e.g. task is not registered), just log and return error
            return {"status": "error", "reason": str(exc)}

    finally:
        try:
            await lock.release(key=lock_key)
        except Exception:
            pass
        try:
            await lock.close()
        except Exception:
            pass
