"""Supervised, bounded local work using the application's existing async engine."""

import asyncio
import datetime as dt
import time
import uuid
from collections import deque
from typing import Any

import structlog
from sqlalchemy.exc import OperationalError

from camply.db.config import DatabaseConfig
from camply.providers import PROVIDERS
from camply.worker.config import worker_config
from camply.worker.engine.catalog import populate_provider
from camply.worker.engine.discovery import due_targets
from camply.worker.engine.scanner import check_target
from camply.worker.outbox import (
    deliver_next,
    is_sqlite_busy,
    prune_finished,
    recover_deliveries,
)

_MAX_TARGET_ATTEMPTS = 4
("""Initial target check plus at most three retries per cycle.""")

logger = structlog.getLogger(__name__)


class LocalRunner:
    """Own one discovery loop and one consumer per kind of background work."""

    def __init__(
        self,
        database: DatabaseConfig,
        *,
        heartbeat: int,
        cooldown: int,
        invite_only: bool = False,
    ) -> None:
        """Keep all scheduler state scoped to one application lifespan."""
        self.database = database
        self.heartbeat = heartbeat
        self.cooldown = cooldown
        self.invite_only = invite_only
        self.scan_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self.catalog_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
        self.in_flight: set[str] = set()
        self.retries: dict[str, tuple[int, float, str]] = {}
        self.tasks: list[asyncio.Task[None]] = []
        self.history: deque[dict[str, Any]] = deque(maxlen=1000)
        self.last_discovery: dict[str, Any] | None = None
        self.catalog_job: str | None = None
        self.active: int = 0
        self.stopping = False
        self.wake = asyncio.Event()

    @property
    def healthy(self) -> bool:
        """A failed supervised loop makes readiness fail instead of disappearing."""
        return (
            bool(self.tasks)
            and not self.stopping
            and all(not task.done() for task in self.tasks)
        )

    def record(
        self,
        task_name: str,
        *,
        outcome: str,
        task_id: str | None = None,
        attempt: int = 1,
        duration_ms: float = 0,
        **context: Any,
    ) -> None:
        """Record only allowlisted operational context, bounded by count and age."""
        allowed = {
            key: value
            for key, value in context.items()
            if key
            in {
                "reason",
                "entity_type",
                "entity_id",
                "provider_id",
                "provider_name",
                "search_name",
                "search_dates",
            }
        }
        self.history.append(
            {
                "task_id": task_id or str(uuid.uuid4()),
                "event_id": str(uuid.uuid4()),
                "attempt": attempt,
                "task_name": task_name,
                "worker": "local",
                "finished_at": dt.datetime.now(dt.timezone.utc),
                "duration_ms": duration_ms,
                "outcome": {"failure": "error", "retry": "retrying"}.get(
                    outcome, outcome
                ),
                **allowed,
            }
        )
        self.recent()

    def recent(self) -> list[dict[str, Any]]:
        """Return recent attempts newest first, removing expired records."""
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
        while self.history and self.history[0]["finished_at"] < cutoff:
            self.history.popleft()
        return list(reversed(self.history))

    def request_sync(self) -> str:
        """Coalesce simultaneous manual/daily refreshes under one job identity."""
        if self.catalog_job is None:
            self.catalog_job = str(uuid.uuid4())
            self.catalog_queue.put_nowait(self.catalog_job)
        return self.catalog_job

    async def start(self) -> None:
        """Recover persisted alerts before starting supervised asynchronous loops."""
        await recover_deliveries(self.database)
        await prune_finished(self.database)
        self.tasks = [
            asyncio.create_task(loop(), name=f"camply-{loop.__name__}")
            for loop in (self._discover, self._scan, self._catalog, self._notifications)
        ]

    async def close(self) -> None:
        """Stop scheduling and cancel consumers, leaving interrupted sends durable."""
        self.stopping = True
        if self.tasks:
            self.tasks[0].cancel()
        try:
            await asyncio.wait_for(
                asyncio.gather(self.scan_queue.join(), self.catalog_queue.join()),
                timeout=5,
            )
        except asyncio.TimeoutError:
            pass
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def _discover(self) -> None:
        """Page eligible targets and prevent duplicate local dispatch."""
        next_catalog = dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1)
        while True:
            try:
                self.wake.clear()
                now = dt.datetime.now(dt.timezone.utc)
                if now.date() >= next_catalog:
                    self.request_sync()
                    next_catalog = now.date() + dt.timedelta(days=1)
                    await prune_finished(self.database)
                targets = await due_targets(
                    sessions=self.database.get_session,
                    cooldown=self.cooldown,
                    limit=100,
                    today=now.date(),
                    invite_only=self.invite_only,
                    exclude=self.in_flight
                    | {
                        key
                        for key, (_, deadline, _) in self.retries.items()
                        if deadline > time.monotonic()
                    },
                )
                enqueued = 0
                for target in targets:
                    key = str(target.id)
                    retry = self.retries.get(key)
                    if (
                        key in self.in_flight
                        or (retry and retry[1] > time.monotonic())
                        or self.scan_queue.full()
                    ):
                        continue
                    self.in_flight.add(key)
                    self.scan_queue.put_nowait(key)
                    enqueued += 1
                self.last_discovery = {
                    "timestamp": now,
                    "targets_discovered": len(targets),
                    "targets_enqueued": enqueued,
                    "status": "success",
                }
                self.record("camply.search.schedule_checks", outcome="success")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Standalone discovery loop error: %s", exc)
                self.record("camply.search.schedule_checks", outcome="failure")
            delays = [
                deadline - time.monotonic()
                for key, (_, deadline, _) in self.retries.items()
                if key not in self.in_flight and deadline > time.monotonic()
            ]
            try:
                await asyncio.wait_for(
                    self.wake.wait(), timeout=min([float(self.heartbeat), *delays])
                )
            except asyncio.TimeoutError:
                pass

    async def _scan(self) -> None:
        """Execute one target at a time with finite target-level backoff."""
        while True:
            key = await self.scan_queue.get()
            started = time.monotonic()
            self.active += 1
            retry = self.retries.get(key)
            attempt = retry[0] + 1 if retry else 1
            job_id = retry[2] if retry and retry[0] else str(uuid.uuid4())
            try:
                result = await check_target(
                    key,
                    sessions=self.database.get_session,
                    registry=PROVIDERS,
                    persistent=True,
                    notification_mode=worker_config.notification_mode,
                    app_url=str(worker_config.app_url),
                    invite_only=self.invite_only,
                )
                outcome = {
                    "success": "success",
                    "error": "failure",
                    "skipped": "skipped",
                }[result["status"]]
                self.retries.pop(key, None)
                self.record(
                    "camply.search.check_campsite_availability",
                    outcome=outcome,
                    task_id=job_id,
                    attempt=attempt,
                    duration_ms=(time.monotonic() - started) * 1000,
                    entity_type="target",
                    entity_id=key,
                    provider_id=result.get("provider_id"),
                    reason=result.get("reason"),
                )
            except Exception:
                delay = (
                    60 * (2 ** (attempt - 1))
                    if attempt < _MAX_TARGET_ATTEMPTS
                    else self.heartbeat
                )
                self.retries[key] = (
                    attempt if attempt < _MAX_TARGET_ATTEMPTS else 0,
                    time.monotonic() + delay,
                    job_id,
                )
                self.wake.set()
                self.record(
                    "camply.search.check_campsite_availability",
                    outcome="retry" if attempt < _MAX_TARGET_ATTEMPTS else "failure",
                    task_id=job_id,
                    attempt=attempt,
                    reason="provider_error",
                    entity_type="target",
                    entity_id=key,
                )
            finally:
                self.active -= 1
                self.in_flight.discard(key)
                self.scan_queue.task_done()

    async def _catalog(self) -> None:
        """Refresh provider catalogs sequentially, retaining individual outcomes."""
        while True:
            job = await self.catalog_queue.get()
            try:
                for provider_id, provider_cls in PROVIDERS.items():
                    started = time.monotonic()
                    self.active += 1
                    try:
                        await populate_provider(provider_id, provider_cls)
                        outcome = "success"
                    except Exception:
                        outcome = "failure"
                    finally:
                        self.active -= 1
                    self.record(
                        "camply.catalog.sync_provider_catalog",
                        outcome=outcome,
                        task_id=job,
                        duration_ms=(time.monotonic() - started) * 1000,
                        provider_id=provider_id,
                        provider_name=provider_cls.__name__,
                    )
            finally:
                self.catalog_job = None
                self.catalog_queue.task_done()

    async def _notifications(self) -> None:
        """Drain due durable alerts without blocking provider checks or HTTP."""
        while True:
            try:
                result = await deliver_next(self.database, invite_only=self.invite_only)
            except OperationalError as error:
                if not is_sqlite_busy(error):
                    raise
                await asyncio.sleep(0.5)
                continue
            if result is None:
                await asyncio.sleep(0.5)
            else:
                self.record("camply.notifications.send_pushover_notification", **result)
