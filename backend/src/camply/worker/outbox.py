"""Persist retries and acknowledge standalone alerts only after accepted delivery."""

import asyncio
import datetime as dt
import sqlite3
import time
import uuid
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any

import httpx
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError

from camply.db.config import DatabaseConfig
from camply.db.models import NotificationOutbox, UniqueTarget, User, UserScan
from camply.worker.config import worker_config
from camply.worker.engine.alerts import matching_opening, summarize_openings
from camply.worker.notifications.base import NotificationDTO
from camply.worker.notifications.pushover import PushoverProvider

MAX_ATTEMPTS = 4
("""Persisted send budget, including interrupted attempts.""")


class MissingCredentials(Exception):
    """Delivery cannot be attempted until the owner configures application credentials."""


def is_sqlite_busy(error: OperationalError) -> bool:
    """Retry only SQLite lock contention; other storage faults must fail readiness."""
    code = getattr(error.orig, "sqlite_errorcode", 0)
    return code & 0xFF in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}


async def finish_delivery(
    database: DatabaseConfig, row_id: uuid.UUID, *, outcome: str, reason: str
) -> bool:
    """Persist an external outcome, retrying busy writes without sending again."""
    while True:
        try:
            async with database.get_session() as session:
                row = await session.get(NotificationOutbox, row_id)
                if row is None:
                    return False
                row.status = {
                    "success": "sent",
                    "retry": "retry",
                    "failure": "failed",
                    "skipped": "skipped",
                }[outcome]
                row.error_category = None if outcome == "success" else reason
                now = dt.datetime.now(dt.timezone.utc)
                row.next_attempt_at = now + dt.timedelta(seconds=120)
                row.finished_at = None if outcome == "retry" else now
                await session.commit()
                return True
        except OperationalError as error:
            if not is_sqlite_busy(error):
                raise
            await asyncio.sleep(0.25)


async def send_accepted(user_key: str, payload: NotificationDTO) -> bool:
    """Use current application credentials and verify the upstream response body."""
    provider = PushoverProvider()
    if not provider.config.app_token:
        raise MissingCredentials
    return await provider.send_accepted(user_key, payload)


def current_payload(
    payload: NotificationDTO, scan: UserScan, target: UniqueTarget, today: dt.date
) -> NotificationDTO | None:
    """Clip past/out-of-range nights using UTC, then apply the current scan filters."""
    if "openings" not in payload.metadata:
        return matching_opening(payload, scan, target, today)
    matching = [
        current
        for item in payload.metadata["openings"]
        if (
            current := matching_opening(
                NotificationDTO.model_validate(item), scan, target, today
            )
        )
        is not None
    ]
    return (
        summarize_openings(matching, scan, target, app_url=str(worker_config.app_url))
        if matching
        else None
    )


async def prune_finished(database: DatabaseConfig) -> None:
    """Remove old terminal records without touching active delivery attempts."""
    now = dt.datetime.now(dt.timezone.utc)
    async with database.get_session() as session:
        await session.execute(
            delete(NotificationOutbox).where(
                NotificationOutbox.finished_at < now - dt.timedelta(hours=24)
            )
        )
        await session.commit()


async def recover_deliveries(database: DatabaseConfig) -> None:
    """Recover interrupted attempts, respecting the finite persisted retry budget."""
    now = dt.datetime.now(dt.timezone.utc)
    async with database.get_session() as session:
        rows = (
            await session.scalars(
                select(NotificationOutbox).where(NotificationOutbox.status == "sending")
            )
        ).all()
        for row in rows:
            row.status = "failed" if row.attempt_count >= MAX_ATTEMPTS else "retry"
            row.error_category = "interrupted_delivery"
            row.next_attempt_at = now
            row.finished_at = now if row.status == "failed" else None
        await session.commit()


async def delivery_outcome(
    send: Callable[[str, NotificationDTO], Awaitable[bool]],
    token: str,
    payload: NotificationDTO,
) -> tuple[str, str]:
    """Classify upstream acceptance, permanent rejection, and transient failures."""
    try:
        accepted = await send(token, payload)
        outcome, reason = (
            ("success", "accepted")
            if accepted is True
            else ("failure", "delivery_not_accepted")
        )
    except MissingCredentials:
        outcome, reason = "skipped", "missing_app_credentials"
    except httpx.HTTPStatusError as exc:
        transient = (
            exc.response.status_code == HTTPStatus.TOO_MANY_REQUESTS
            or exc.response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
        )
        outcome, reason = (
            ("retry", "upstream_transient")
            if transient
            else ("failure", "upstream_rejected")
        )
    except httpx.TransportError:
        outcome, reason = "retry", "transport_error"
    except (ValueError, TypeError):
        outcome, reason = "failure", "invalid_response"
    except Exception:
        outcome, reason = "failure", "delivery_error"
    return outcome, reason


async def deliver_next(
    database: DatabaseConfig,
    *,
    invite_only: bool = False,
    send: Callable[[str, NotificationDTO], Awaitable[bool]] = send_accepted,
) -> dict[str, Any] | None:
    """Consume one due intent without holding a transaction across network delivery."""
    started = time.monotonic()
    now = dt.datetime.now(dt.timezone.utc)
    async with database.get_session() as session:
        row = (
            await session.scalars(
                select(NotificationOutbox)
                .where(
                    NotificationOutbox.status.in_(["pending", "retry"]),
                    NotificationOutbox.next_attempt_at <= now,
                )
                .order_by(NotificationOutbox.next_attempt_at, NotificationOutbox.id)
                .limit(1)
            )
        ).first()
        if row is None:
            return None
        outcome, reason = "skipped", "scan_ineligible"
        payload = None
        user = await session.get(User, row.user_id) if row.user_id else None
        scan = await session.get(UserScan, row.scan_id) if row.scan_id else None
        target = (
            await session.get(UniqueTarget, row.target_id) if row.target_id else None
        )
        if (
            user
            and scan
            and target
            and scan.user_id == user.id
            and scan.target_id == target.id
            and user.scanning_enabled
            and scan.is_active
            and (not invite_only or user.is_invited)
        ):
            try:
                payload = current_payload(
                    NotificationDTO.model_validate(row.payload),
                    scan,
                    target,
                    now.date(),
                )
            except (ValidationError, ValueError, KeyError, TypeError):
                outcome, reason = "failure", "invalid_payload"
        token = user.pushover_token if user else None
        if payload is not None and not token:
            payload = None
            reason = "missing_user_credentials"
        if payload is not None:
            row.status = "sending"
            row.attempt_count += 1
        else:
            row.status = "failed" if outcome == "failure" else "skipped"
            row.error_category = reason
            row.finished_at = now
        job_id, attempt, target_id = row.id, row.attempt_count, row.target_id
        await session.commit()
    if payload is not None:
        outcome, reason = await delivery_outcome(send, str(token), payload)
        if outcome == "retry" and attempt >= MAX_ATTEMPTS:
            outcome = "failure"
        if not await finish_delivery(database, job_id, outcome=outcome, reason=reason):
            return None
    return {
        "task_id": str(job_id),
        "attempt": max(1, attempt),
        "outcome": outcome,
        "reason": reason,
        "duration_ms": (time.monotonic() - started) * 1000,
        "entity_type": "target",
        "entity_id": str(target_id) if target_id else None,
    }
