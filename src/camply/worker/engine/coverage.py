"""Durable current-round progress over shared campground attempts."""

import datetime as dt
import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.coverage import reconcile_coverage, scan_load_options
from camply.db.models import ScanTarget, UniqueTarget, UserScan

ATTEMPT_STALE_SECONDS = 105


def utc(value: dt.datetime) -> dt.datetime:
    """Normalize SQLite timestamps for comparisons with UTC clocks."""
    return value.replace(tzinfo=dt.timezone.utc) if value.tzinfo is None else value


async def _mark_interrupted_attempts(
    session: AsyncSession,
    *,
    now: dt.datetime,
    older_than_seconds: int | None = None,
) -> int:
    """Mark unfinished target attempts as interrupted so rounds can retry promptly."""
    stmt = select(UniqueTarget).where(
        UniqueTarget.attempt_id.is_not(None),
        UniqueTarget.attempt_started_at.is_not(None),
        UniqueTarget.attempt_finished_at.is_(None),
    )
    if older_than_seconds is not None:
        cutoff = now - dt.timedelta(seconds=older_than_seconds)
        stmt = stmt.where(UniqueTarget.attempt_started_at <= cutoff)
    targets = (await session.scalars(stmt.with_for_update())).all()
    if not targets:
        return 0
    for target in targets:
        attempt_id = target.attempt_id
        target.attempt_finished_at = now
        target.attempt_error_category = "interrupted_attempt"
        links = (
            await session.scalars(
                select(ScanTarget).where(
                    ScanTarget.target_id == target.id,
                    ScanTarget.attempt_id == attempt_id,
                    ScanTarget.outcome.in_(["pending", "retrying"]),
                )
            )
        ).all()
        for link in links:
            link.outcome = "retrying"
            link.error_category = "interrupted_attempt"
    return len(targets)


async def recover_interrupted_attempts(
    sessions: Callable[[], AsyncSession],
    *,
    older_than_seconds: int | None = None,
    now: dt.datetime | None = None,
) -> int:
    """Recover open attempts left behind by a crashed or restarted worker."""
    timestamp = now or dt.datetime.now(dt.timezone.utc)
    async with sessions() as session:
        recovered = await _mark_interrupted_attempts(
            session, now=timestamp, older_than_seconds=older_than_seconds
        )
        await session.commit()
        return recovered


def finish_round(scan: UserScan, *, now: dt.datetime) -> None:
    """Advance full-success time only after every captured member succeeded."""
    members = [
        link
        for link in scan.coverage
        if link.round_id == scan.current_round_id
        and link.coverage_revision == scan.coverage_revision
    ]
    if members and all(link.outcome in {"success", "failed"} for link in members):
        scan.round_completed_at = now
        if all(link.outcome == "success" for link in members):
            scan.last_full_checked_at = min(
                utc(link.successful_at)
                for link in members
                if link.successful_at is not None
            )


async def prepare_rounds(
    *,
    sessions: Callable[[], AsyncSession],
    cooldown: int,
    heartbeat: int = 300,
    now: dt.datetime | None = None,
) -> None:
    """Reconcile complete membership and recover expired work before discovery."""
    now = now or dt.datetime.now(dt.timezone.utc)
    async with sessions() as session:
        await _mark_interrupted_attempts(
            session, now=now, older_than_seconds=ATTEMPT_STALE_SECONDS
        )
        scans = (
            (
                await session.scalars(
                    select(UserScan)
                    .where(
                        UserScan.destination_type == "recreation_area",
                        UserScan.is_active.is_(True),
                        UserScan.end_date > now.date(),
                    )
                    .options(*scan_load_options())
                    .with_for_update()
                )
            )
            .unique()
            .all()
        )
        for scan in scans:
            await reconcile_coverage(session, scan)
            if not scan.coverage:
                continue
            if scan.current_round_id and not scan.round_completed_at:
                for link in scan.coverage:
                    if (
                        link.outcome in {"pending", "retrying"}
                        and scan.round_deadline_at
                        and utc(scan.round_deadline_at) <= now
                    ):
                        link.outcome, link.failed_at, link.error_category = (
                            "failed",
                            now,
                            "round_deadline",
                        )
                finish_round(scan, now=now)
                continue
            if (
                scan.round_completed_at
                and (now - utc(scan.round_completed_at)).total_seconds() < cooldown
            ):
                continue
            scan.current_round_id = uuid.uuid4()
            scan.round_started_at = now
            scan.round_deadline_at = now + dt.timedelta(seconds=2 * heartbeat + 780)
            scan.round_completed_at = None
            for link in scan.coverage:
                link.round_id = scan.current_round_id
                link.attempt_id = None
                link.error_category = None
                link.failed_at = None
                target = link.target
                fresh = (
                    target.last_checked_at
                    and utc(target.last_checked_at)
                    > now - dt.timedelta(seconds=cooldown)
                    and not target.attempt_error_category
                )
                link.outcome = "success" if fresh else "pending"
                link.successful_at = target.last_checked_at if fresh else None
            finish_round(scan, now=now)
        await session.commit()


async def register_attempt(
    session: AsyncSession, target: UniqueTarget, *, now: dt.datetime
) -> uuid.UUID:
    """Register one attempt with every current subscriber before network work."""
    attempt = uuid.uuid4()
    target.attempt_id, target.attempt_started_at = attempt, now
    target.attempt_finished_at = None
    links = (
        await session.scalars(
            select(ScanTarget).where(ScanTarget.target_id == target.id)
        )
    ).all()
    for link in links:
        scan = await session.get(UserScan, link.scan_id)
        if (
            scan
            and scan.current_round_id
            and link.round_id == scan.current_round_id
            and link.coverage_revision == scan.coverage_revision
            and link.outcome in {"pending", "retrying"}
        ):
            link.attempt_id = attempt
    return attempt


async def record_attempt(
    session: AsyncSession,
    target: UniqueTarget,
    attempt: uuid.UUID,
    *,
    error: str | None = None,
    terminal: bool = False,
) -> None:
    """Reject stale callbacks while preserving independently successful snapshots."""
    now = dt.datetime.now(dt.timezone.utc)
    if target.attempt_id != attempt:
        return
    target.attempt_finished_at, target.attempt_error_category = now, error
    links = (
        await session.scalars(
            select(ScanTarget).where(
                ScanTarget.target_id == target.id, ScanTarget.attempt_id == attempt
            )
        )
    ).all()
    for link in links:
        scan = await session.get(UserScan, link.scan_id)
        if (
            not scan
            or link.round_id != scan.current_round_id
            or link.coverage_revision != scan.coverage_revision
        ):
            continue
        link.outcome = (
            "success" if error is None else "failed" if terminal else "retrying"
        )
        link.successful_at = now if error is None else None
        link.failed_at = now if terminal and error else None
        link.error_category = error
        finish_round(scan, now=now)
