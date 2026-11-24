"""Durable bounded area notification windows and qualified delivery validation."""

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.coverage import live_targets, scan_load_options
from camply.db.models import NotificationOutbox, UniqueTarget, UserScan
from camply.worker.engine.alerts import matching_opening
from camply.worker.notifications.base import NotificationDTO


def summary(
    openings: list[NotificationDTO], scan: UserScan, *, app_url: str
) -> NotificationDTO:
    """Count distinct qualified sites and link a summary to one saved scan."""
    count = len(
        {
            (
                item.metadata["provider_id"],
                item.metadata["campground_id"],
                item.metadata["campsite_id"],
            )
            for item in openings
        }
    )
    campgrounds = len({item.metadata["campground_id"] for item in openings})
    return NotificationDTO(
        title=f"{count} new campsites: {scan.destination_name}",
        message=f"{count} campsites with new availability across {campgrounds} campgrounds at {scan.destination_name}. View matching stays and booking options in Camply.",
        booking_url=f"{app_url.rstrip('/')}/dashboard/scans/{scan.id}#results",
        url_title="View campsites",
        park_name=scan.destination_name,
        campsite_name="",
        start_date=scan.start_date,
        end_date=scan.end_date,
        metadata={
            "new_campsite_count": count,
            "openings": [item.model_dump(mode="json") for item in openings],
        },
    )


def _merge(old: list[dict], additions: list[dict]) -> list[dict]:
    """Union qualified site observations without combining different sites' nights."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for item in old + additions:
        meta = item["metadata"]
        key = (meta["target_id"], meta["campsite_id"])
        if key in merged:
            meta = {
                **meta,
                "available_dates": sorted(
                    set(
                        meta["available_dates"]
                        + merged[key]["metadata"]["available_dates"]
                    )
                ),
            }
        merged[key] = {**item, "metadata": meta}
    return list(merged.values())


async def enqueue_area(
    session: AsyncSession,
    scan: UserScan,
    target: UniqueTarget,
    openings: list[NotificationDTO],
    *,
    channel: str,
    now: dt.datetime,
    direct: bool = False,
) -> list[dt.datetime]:
    """Append with version/status guards and return due times for new outbox rows."""
    scheduled_due: list[dt.datetime] = []
    candidates = [
        item.model_copy(
            update={
                "metadata": {
                    **item.metadata,
                    "target_id": str(target.id),
                    "provider_id": target.provider_id,
                    "campground_id": target.campground_id,
                }
            }
        ).model_dump(mode="json")
        for item in openings
    ]
    for candidate_set in [[item] for item in candidates] if direct else [candidates]:
        window = int(now.timestamp()) // 5 * 5
        bumped = False
        while True:
            wall_now = dt.datetime.now(dt.timezone.utc)
            row = (
                await session.scalar(
                    select(NotificationOutbox)
                    .where(
                        NotificationOutbox.scan_id == scan.id,
                        NotificationOutbox.delivery_key == "area-summary",
                        NotificationOutbox.channel == channel,
                        NotificationOutbox.payload_kind == "area",
                        NotificationOutbox.scan_revision == scan.definition_revision,
                        NotificationOutbox.status == "pending",
                        NotificationOutbox.attempt_count == 0,
                        NotificationOutbox.next_attempt_at > max(now, wall_now),
                    )
                    .order_by(NotificationOutbox.next_attempt_at.desc())
                )
                if not direct
                else None
            )
            detection = (
                row.detection_id
                if row is not None
                else uuid.uuid4()
                if direct
                else uuid.uuid5(
                    scan.id, f"{scan.definition_revision}:{channel}:{window}"
                )
            )
            key = (
                f"{target.provider_id}:{target.campground_id}:{candidate_set[0]['metadata']['campsite_id']}"
                if direct
                else "area-summary"
            )
            if row is None:
                row = await session.scalar(
                    select(NotificationOutbox).where(
                        NotificationOutbox.detection_id == detection,
                        NotificationOutbox.scan_id == scan.id,
                        NotificationOutbox.delivery_key == key,
                    )
                )
            due = (
                dt.datetime.fromtimestamp(window + 5, dt.timezone.utc)
                if (bumped and not direct)
                else (now + dt.timedelta(seconds=5) if not direct else now)
            )
            if row is None:
                try:
                    async with session.begin_nested():
                        session.add(
                            NotificationOutbox(
                                detection_id=detection,
                                user_id=scan.user_id,
                                scan_id=scan.id,
                                target_id=None,
                                delivery_key=key,
                                channel=channel,
                                payload_kind="area",
                                scan_revision=scan.definition_revision,
                                payload_version=1,
                                payload={"candidates": candidate_set, "direct": direct},
                                created_at=now,
                                next_attempt_at=due,
                            )
                        )
                        await session.flush()
                    scheduled_due.append(due)
                    break
                except IntegrityError:
                    bumped = True
                    window = max(window + 5, int(wall_now.timestamp()) // 5 * 5)
                    continue
            version = row.payload_version
            if (
                row.status != "pending"
                or row.attempt_count
                or (row.next_attempt_at.replace(tzinfo=dt.timezone.utc) <= wall_now)
            ):
                bumped = True
                window = max(window + 5, int(wall_now.timestamp()) // 5 * 5)
                continue
            payload = {
                **row.payload,
                "candidates": _merge(row.payload["candidates"], candidate_set),
            }
            result = await session.execute(
                update(NotificationOutbox)
                .where(
                    NotificationOutbox.id == row.id,
                    NotificationOutbox.payload_version == version,
                    NotificationOutbox.status == "pending",
                    NotificationOutbox.attempt_count == 0,
                )
                .values(payload=payload, payload_version=version + 1)
                .returning(NotificationOutbox.id)
                .execution_options(synchronize_session=False)
            )
            if result.scalar_one_or_none():
                break
            await session.refresh(row)
    return scheduled_due


async def current_area_payload(
    session: AsyncSession, row: NotificationOutbox, *, today: dt.date, app_url: str
) -> NotificationDTO | None:
    """Recheck saved revision and every candidate against current live coverage."""
    scan = await session.scalar(
        select(UserScan)
        .where(UserScan.id == row.scan_id)
        .options(*scan_load_options())
        .execution_options(populate_existing=True)
    )
    if scan is None or scan.definition_revision != row.scan_revision:
        return None
    targets = {str(target.id): target for target in live_targets(scan)}
    matching = []
    for item in row.payload["candidates"]:
        target = targets.get(item["metadata"]["target_id"])
        if target is None:
            continue
        current = matching_opening(
            NotificationDTO.model_validate(item), scan, target, today
        )
        if current:
            matching.append(
                current.model_copy(update={"park_name": target.campground.name})
            )
    if not matching:
        return None
    return (
        matching[0]
        if row.payload.get("direct")
        else summary(matching, scan, app_url=app_url)
    )
