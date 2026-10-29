"""Shared async scanner without task queues, distributed locks, or metric clients."""

import datetime
import uuid as uuid_mod
from collections.abc import Callable
from typing import Any, Literal

import structlog
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.availability import matches_scan_filters
from camply.db.eligibility import eligible_scan_condition
from camply.db.models import (
    Campground,
    NotificationOutbox,
    ScanResult,
    UniqueTarget,
    User,
    UserScan,
)
from camply.providers.base import BaseProvider
from camply.providers.dto import CampsiteDTO
from camply.providers.utils import normalize_name
from camply.worker.engine.alerts import matching_opening, summarize_openings
from camply.worker.notifications.base import NotificationDTO

logger = structlog.getLogger(__name__)


def _matches_scan_filters(campsite: CampsiteDTO, scan: UserScan) -> bool:
    """Use the same site preferences and qualifying stays as the results API."""
    return matches_scan_filters(
        [night.isoformat() for night in campsite.available_dates],
        campsite_type=campsite.campsite_type.value,
        is_electric=campsite.is_electric,
        scan=scan,
    )


async def check_target(
    target_id: str,
    *,
    sessions: Callable[[], AsyncSession],
    registry: dict[int, type[BaseProvider]],
    dispatch: Callable[[UserScan, NotificationDTO], None] | None = None,
    persistent: bool = False,
    notification_mode: Literal["summary", "direct"] = "summary",
    app_url: str = "https://camply.juftin.dev",
    invite_only: bool = False,
    on_provider_result: Callable[[int, bool], None] | None = None,
) -> dict[str, Any]:
    """Check one shared target and atomically retain local delivery intents."""
    target_uuid = uuid_mod.UUID(target_id)
    scan_condition = eligible_scan_condition()
    if invite_only:
        scan_condition = and_(scan_condition, User.is_invited.is_(True))
    async with sessions() as session:
        # Load target
        stmt = select(UniqueTarget).where(UniqueTarget.id == target_uuid)
        result = await session.execute(stmt)
        target = result.scalar_one_or_none()

        if target is None:
            logger.warning("Target not found", target_id=target_id)
            return {"status": "error", "reason": "target_not_found"}

        if (
            persistent
            and target.end_date <= datetime.datetime.now(datetime.timezone.utc).date()
        ):
            return {"status": "skipped", "reason": "expired_target"}

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

        # Check for eligible subscribers before provider call
        sub_stmt = (
            select(func.count(UserScan.id))
            .join(User, User.id == UserScan.user_id)
            .where(
                UserScan.target_id == target_uuid,
                scan_condition,
            )
        )
        sub_res = await session.execute(sub_stmt)
        eligible_count = sub_res.scalar() or 0
        if eligible_count == 0:
            logger.info(
                "No eligible subscribers for target, skipping",
                target_id=target_id,
            )
            return {
                "status": "skipped",
                "reason": "no_eligible_subscribers",
                "provider_id": target.provider_id,
                "provider_name": "Recreation.gov"
                if target.provider_id == 1
                else f"Provider {target.provider_id}",
                "search_name": normalize_name(campground.name),
                "search_dates": f"{target.start_date.isoformat()} → {target.end_date.isoformat()}",
            }

        # Resolve provider class
        provider_cls = registry.get(target.provider_id)
        if provider_cls is None:
            logger.error(
                "Unknown provider",
                provider_id=target.provider_id,
            )
            return {"status": "error", "reason": "unknown_provider"}

        # Instantiate provider and call find_availabilities
        await session.commit()
        provider = provider_cls()
        try:
            availabilities: list[CampsiteDTO] = await provider.find_availabilities(
                park_id=target.campground_id,
                start_date=target.start_date,
                end_date=target.end_date,
            )
            if on_provider_result is not None:
                on_provider_result(target.provider_id, True)
        except Exception:
            if on_provider_result is not None:
                on_provider_result(target.provider_id, False)
            raise
        finally:
            try:
                await provider.async_client.aclose()
            except Exception:
                pass

        # Keep snapshots and alerts aligned with the current results API.
        first_night = max(
            target.start_date, datetime.datetime.now(datetime.timezone.utc).date()
        )
        availabilities = [
            campsite.model_copy(update={"available_dates": dates})
            for campsite in availabilities
            if (
                dates := [
                    night
                    for night in campsite.available_dates
                    if first_night <= night < target.end_date
                ]
            )
        ]

        # Load previous scan results for diffing
        prev_stmt = select(ScanResult).where(ScanResult.target_id == target_uuid)
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
            campground_id=target.campground_id,
            rec_area_id=campground.recreation_area_id,
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
                        title=f"Campsite Available: {normalize_name(campground.name)}",
                        message=(
                            f"{campsite.campsite_name} "
                            f"({campsite.campsite_type.value}) "
                            f"is available at {normalize_name(campground.name)}"
                        ),
                        booking_url=booking_url,
                        park_name=normalize_name(campground.name),  # type: ignore[arg-type]
                        campsite_name=campsite.campsite_name,
                        start_date=target.start_date,
                        end_date=target.end_date,
                        metadata={
                            "campsite_id": campsite.campsite_id,
                            "campsite_type": campsite.campsite_type.value,
                            "is_electric": campsite.is_electric,
                            "is_accessible": campsite.is_accessible,
                            "available_dates": [
                                d.isoformat() for d in campsite.available_dates
                            ],
                        },
                    )
                )

            new_results_to_store.append(
                ScanResult(
                    target_id=target_uuid,
                    campsite_id=campsite.campsite_id,
                    campsite_name=campsite.campsite_name,
                    campsite_type=campsite.campsite_type.value,
                    is_electric=campsite.is_electric,
                    is_accessible=campsite.is_accessible,
                    available_dates=[d.isoformat() for d in campsite.available_dates],
                )
            )

        # Replace previous scan results for this target
        await session.execute(
            delete(ScanResult).where(ScanResult.target_id == target_uuid)
        )
        session.add_all(new_results_to_store)

        # Update last_checked_at
        target.last_checked_at = datetime.datetime.now(tz=datetime.timezone.utc)
        session.add(target)

        if not persistent:
            await session.commit()

        detection_id = uuid_mod.uuid4()
        # Fan-out: find matching UserScans and enqueue notifications
        notifications_sent = 0
        if new_openings:
            us_stmt = (
                select(UserScan)
                .join(User, User.id == UserScan.user_id)
                .where(
                    UserScan.target_id == target_uuid,
                    scan_condition,
                )
            )
            us_result = await session.execute(us_stmt)
            active_scans = us_result.scalars().all()

            for scan in active_scans:
                matching = []
                for opening in new_openings:
                    current = matching_opening(
                        opening,
                        scan,
                        target,
                        datetime.datetime.now(datetime.timezone.utc).date(),
                    )
                    if current is not None and any(
                        (current.metadata["campsite_id"], night) not in previously_seen
                        for night in current.metadata["available_dates"]
                    ):
                        matching.append(current)
                if not matching:
                    continue
                notifications = (
                    [summarize_openings(matching, scan, target, app_url=app_url)]
                    if notification_mode == "summary"
                    else matching
                )
                for notification in notifications:
                    if persistent:
                        session.add(
                            NotificationOutbox(
                                detection_id=detection_id,
                                user_id=scan.user_id,
                                scan_id=scan.id,
                                target_id=target_uuid,
                                delivery_key="summary"
                                if notification_mode == "summary"
                                else notification.metadata["campsite_id"],
                                payload=notification.model_dump(mode="json"),
                                created_at=target.last_checked_at,
                                next_attempt_at=target.last_checked_at,
                            )
                        )
                    elif dispatch is not None:
                        dispatch(scan, notification)
                    notifications_sent += 1

            logger.info(
                "New openings detected and fanned out",
                target_id=target_id,
                new_openings=len(new_openings),
                notifications_sent=notifications_sent,
            )

        if persistent:
            await session.commit()

        return {
            "status": "success",
            "provider_id": target.provider_id,
            "provider_name": "Recreation.gov"
            if target.provider_id == 1
            else f"Provider {target.provider_id}",
            "search_name": normalize_name(campground.name),
            "search_dates": f"{target.start_date.isoformat()} → {target.end_date.isoformat()}",
            "availabilities_found": len(availabilities),
            "new_openings": len(new_openings),
            "notifications_sent": notifications_sent,
        }
