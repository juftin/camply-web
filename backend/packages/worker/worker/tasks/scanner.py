"""
Scanner: check_target_availability Celery task.
"""

import asyncio
import datetime
import uuid as uuid_mod
from typing import Any, Optional

import structlog
from sqlalchemy import delete, select

from db.config import db
from db.models import Campground, ScanResult, UniqueTarget, UserScan
from providers import PROVIDERS
from providers.dto import CampsiteDTO
from worker.celery_app import celery_app
from worker.config import worker_config
from worker.locks import ValkeyLock
from worker.notifications.base import NotificationDTO

logger = structlog.getLogger(__name__)


def _longest_consecutive(dates: list[datetime.date]) -> int:
    """Find the longest consecutive streak of dates."""
    if not dates:
        return 0
    sorted_dates = sorted(dates)
    longest = 1
    current = 1
    for i in range(1, len(sorted_dates)):
        delta = (sorted_dates[i] - sorted_dates[i - 1]).days
        if delta == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def _matches_scan_filters(campsite: CampsiteDTO, scan: UserScan) -> bool:
    """
    Check whether a campsite matches a user's scan filters.

    Filters applied:
      - min_stay_length: consecutive nights available >= scan.min_stay_length
      - preferred_types: if set, campsite_type must be in the list
      - require_electric: if True, campsite must have electric hookup
    """
    # Minimum stay length: check for a consecutive block of N nights
    if scan.min_stay_length and scan.min_stay_length > 1:
        consec = _longest_consecutive(campsite.available_dates)
        if consec < scan.min_stay_length:
            return False

    # Preferred campsite types
    if scan.preferred_types:
        if campsite.campsite_type.value not in scan.preferred_types:
            return False

    # Electric required
    if scan.require_electric and not campsite.is_electric:
        return False

    return True


@celery_app.task(
    name="worker.tasks.scanner.check_target_availability",
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
    target_uuid = uuid_mod.UUID(target_id)
    lock_key = f"lock:target:{target_id}"
    lock = ValkeyLock(valkey_url=worker_config.valkey_url)

    try:
        acquired = await lock.acquire(
            key=lock_key, timeout=worker_config.lock_timeout
        )
    except Exception:
        logger.warning(
            "Could not connect to Valkey for lock, skipping",
            target_id=target_id,
        )
        return {"status": "skipped", "reason": "valkey_unavailable"}

    if not acquired:
        logger.info("Lock not acquired, skipping", target_id=target_id)
        return {"status": "skipped", "reason": "lock_held"}

    try:
        async with db.get_session() as session:
            # Load target
            stmt = select(UniqueTarget).where(UniqueTarget.id == target_uuid)
            result = await session.execute(stmt)
            target = result.scalar_one_or_none()

            if target is None:
                logger.warning("Target not found", target_id=target_id)
                return {"status": "error", "reason": "target_not_found"}

            # Load campground for name/booking URL
            cg_stmt = select(Campground).where(
                Campground.id == target.campground_id,
                Campground.provider_id == target.provider_id,
            )
            cg_result = await session.execute(cg_stmt)
            campground = cg_result.scalar_one_or_none()

            if campground is None:
                logger.warning(
                    "Campground not found",
                    campground_id=target.campground_id,
                )
                return {"status": "error", "reason": "campground_not_found"}

            # Resolve provider class
            provider_cls = PROVIDERS.get(target.provider_id)
            if provider_cls is None:
                logger.error(
                    "Unknown provider",
                    provider_id=target.provider_id,
                )
                return {"status": "error", "reason": "unknown_provider"}

            # Instantiate provider and call find_availabilities
            provider = provider_cls()
            try:
                availabilities: list[CampsiteDTO] = (
                    await provider.find_availabilities(
                        park_id=target.campground_id,
                        start_date=target.start_date,
                        end_date=target.end_date,
                    )
                )
            finally:
                try:
                    await provider.async_client.aclose()
                except Exception:
                    pass

            # Build a campsite lookup dict for O(1) access during fan-out
            campsite_by_id: dict[str, CampsiteDTO] = {
                c.campsite_id: c for c in availabilities
            }

            # Load previous scan results for diffing
            prev_stmt = select(ScanResult).where(
                ScanResult.target_id == target_uuid
            )
            prev_result = await session.execute(prev_stmt)
            previous_results = prev_result.scalars().all()

            # Build a set of previously seen (campsite_id, date) pairs
            previously_seen: set[tuple[str, str]] = set()
            for sr in previous_results:
                for date_str in sr.available_dates:
                    previously_seen.add((sr.campsite_id, date_str))

            # Identify new openings and build scan results
            new_openings: list[NotificationDTO] = []
            new_results_to_store: list[ScanResult] = []

            booking_url = provider_cls.get_campground_url(
                campground_id=target.campground_id
            )

            for campsite in availabilities:
                is_new = False
                for available_date in campsite.available_dates:
                    key = (campsite.campsite_id, available_date.isoformat())
                    if key not in previously_seen:
                        is_new = True
                        break

                if is_new:
                    new_openings.append(
                        NotificationDTO(
                            title=f"Campsite Available: {campground.name}",
                            message=(
                                f"{campsite.campsite_name} "
                                f"({campsite.campsite_type.value}) "
                                f"is available at {campground.name}"
                            ),
                            booking_url=booking_url,
                            park_name=campground.name,
                            campsite_name=campsite.campsite_name,
                            start_date=target.start_date,
                            end_date=target.end_date,
                            metadata={
                                "campsite_id": campsite.campsite_id,
                                "campsite_type": campsite.campsite_type.value,
                                "is_electric": campsite.is_electric,
                                "is_accessible": campsite.is_accessible,
                                "available_dates": [
                                    d.isoformat()
                                    for d in campsite.available_dates
                                ],
                            },
                        )
                    )

                new_results_to_store.append(
                    ScanResult(
                        target_id=target_uuid,
                        campsite_id=campsite.campsite_id,
                        available_dates=[
                            d.isoformat() for d in campsite.available_dates
                        ],
                    )
                )

            # Replace previous scan results for this target
            await session.execute(
                delete(ScanResult).where(
                    ScanResult.target_id == target_uuid
                )
            )
            session.add_all(new_results_to_store)

            # Update last_checked_at
            target.last_checked_at = datetime.datetime.now(
                tz=datetime.timezone.utc
            )
            session.add(target)

            await session.commit()

            # Fan-out: find matching UserScans and enqueue notifications
            notifications_sent = 0
            if new_openings:
                us_stmt = select(UserScan).where(
                    UserScan.target_id == target_uuid,
                    UserScan.is_active == True,  # noqa: E712
                )
                us_result = await session.execute(us_stmt)
                active_scans = us_result.scalars().all()

                for scan in active_scans:
                    for opening in new_openings:
                        campsite_id = opening.metadata["campsite_id"]
                        matching_campsite = campsite_by_id.get(campsite_id)
                        if matching_campsite is None:
                            continue
                        if _matches_scan_filters(matching_campsite, scan):
                            celery_app.send_task(
                                name="worker.tasks.notifications.send_pushover_notification",
                                kwargs={
                                    "user_id": str(scan.user_id),
                                    "notification": opening.model_dump(
                                        mode="json"
                                    ),
                                },
                                queue="celery",
                            )
                            notifications_sent += 1

                logger.info(
                    "New openings detected and fanned out",
                    target_id=target_id,
                    new_openings=len(new_openings),
                    notifications_sent=notifications_sent,
                )

            return {
                "status": "success",
                "availabilities_found": len(availabilities),
                "new_openings": len(new_openings),
                "notifications_sent": notifications_sent,
            }

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
