"""
Shared in-process per-provider cooldown gate, Retry-After parsing, and pacing.

Coordinates HTTP 429 cooldown windows, bounded in-flight concurrency, and
optional minimum start-interval spacing across concurrent requests and provider
instances within a process without external infrastructure.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from weakref import WeakKeyDictionary

import structlog

from camply.providers.transport_config import TransportEvent, emit_transport_event

logger = structlog.getLogger(__name__)


def _parse_http_date_delta(cleaned: str, now_utc: datetime | None) -> float | None:
    """Parse an RFC 9110 HTTP-date string into a UTC delta in seconds."""
    try:
        parsed_dt = parsedate_to_datetime(cleaned)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None

    if parsed_dt is None:
        return None

    if parsed_dt.tzinfo is None:
        parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)

    reference = now_utc if now_utc is not None else datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)

    return (parsed_dt - reference).total_seconds()


def parse_retry_after(
    raw_header: str | None,
    *,
    max_seconds: float,
    now_utc: datetime | None = None,
) -> float | None:
    """
    Parse an HTTP ``Retry-After`` header in delta-seconds or RFC 9110 HTTP-date format.

    Parameters
    ----------
    raw_header : str | None
        Raw ``Retry-After`` header value from an HTTP response.
    max_seconds : float
        Upper clamp in seconds so extreme upstream headers cannot stall workers.
    now_utc : datetime | None, optional
        Reference UTC timestamp for deterministic testing of HTTP-date headers.

    Returns
    -------
    float | None
        Positive clamped delay in seconds, or ``None`` when the header is missing,
        unparseable, non-finite, or non-positive.
    """
    cleaned = raw_header.strip() if raw_header is not None else ""
    if not cleaned:
        return None

    delay: float | None
    try:
        delay = float(cleaned)
    except ValueError:
        delay = _parse_http_date_delta(cleaned, now_utc)

    if delay is None or not math.isfinite(delay) or delay <= 0.0:
        return None
    return min(delay, max_seconds)


class ProviderCooldownGate:
    """
    In-process shared cooldown, concurrency cap, and pacing gate for one provider.

    Synchronization primitives (``asyncio.Semaphore`` and ``asyncio.Lock``) are
    stored per running event loop in ``WeakKeyDictionary`` maps so sequential
    ``asyncio.run()`` invocations share monotonic timestamps without binding
    primitives across closed event loops.

    Parameters
    ----------
    provider_name : str
        Concrete provider class name (e.g., ``RecreationGovProvider``).
    max_concurrency : int, optional
        Maximum concurrent in-flight upstream requests (``0`` disables the cap).
    min_interval_seconds : float, optional
        Minimum spacing in seconds between outgoing request starts (``0.0`` disables).
    max_cooldown_seconds : float, optional
        Maximum single cooldown window in seconds (default ``60.0``).
    """

    def __init__(
        self,
        provider_name: str,
        max_concurrency: int = 4,
        min_interval_seconds: float = 0.0,
        max_cooldown_seconds: float = 60.0,
    ) -> None:
        self.provider_name = provider_name
        self.max_concurrency = max_concurrency
        self.min_interval_seconds = min_interval_seconds
        self.max_cooldown_seconds = max_cooldown_seconds
        self._cooldown_until: float = 0.0
        self._last_request_at: float = 0.0
        self._semaphores: WeakKeyDictionary[
            asyncio.AbstractEventLoop, asyncio.Semaphore
        ] = WeakKeyDictionary()
        self._pace_locks: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock] = (
            WeakKeyDictionary()
        )

    @property
    def cooldown_until(self) -> float:
        """Return the current monotonic cooldown deadline."""
        return self._cooldown_until

    def remaining_cooldown(self) -> float:
        """Return remaining active cooldown seconds (``0.0`` when idle)."""
        return max(0.0, self._cooldown_until - time.monotonic())

    def reset(self) -> None:
        """Clear cooldown and pacing timestamps (primarily for tests)."""
        self._cooldown_until = 0.0
        self._last_request_at = 0.0

    def trigger_cooldown(self, delay_seconds: float, *, reason: str = "429") -> float:
        """
        Extend the provider's shared cooldown deadline monotonically.

        Parameters
        ----------
        delay_seconds : float
            Requested cooldown delay in seconds before clamping.
        reason : str, optional
            Low-cardinality trigger reason (default ``"429"``).

        Returns
        -------
        float
            Clamped delay in seconds applied to the candidate deadline.
        """
        if not math.isfinite(delay_seconds) or delay_seconds <= 0.0:
            return 0.0
        clamped = min(delay_seconds, self.max_cooldown_seconds)
        candidate = time.monotonic() + clamped
        if candidate > self._cooldown_until:
            self._cooldown_until = candidate
            logger.warning(
                "Provider cooldown triggered",
                provider=self.provider_name,
                delay_seconds=round(clamped, 3),
                reason=reason,
            )
        return clamped

    async def wait_for_cooldown(self, *, reason: str = "429") -> float:
        """
        Wait until any active shared cooldown deadline has elapsed.

        Returns
        -------
        float
            Total seconds slept across all observed cooldown extensions.
        """
        total_waited = 0.0
        while True:
            remaining = self._cooldown_until - time.monotonic()
            if remaining <= 0.0:
                return total_waited
            logger.debug(
                "Provider cooldown active; waiting",
                provider=self.provider_name,
                delay_seconds=round(remaining, 3),
                reason=reason,
            )
            emit_transport_event(
                TransportEvent(
                    kind="cooldown_wait",
                    provider=self.provider_name,
                    reason=reason,
                    delay_seconds=remaining,
                )
            )
            await asyncio.sleep(remaining)
            total_waited += remaining

    async def acquire_pacing(self) -> float:
        """
        Reserve the next request-start slot and sleep outside the pacing lock.

        Returns
        -------
        float
            Seconds slept to honor ``min_interval_seconds``.
        """
        if self.min_interval_seconds <= 0.0:
            return 0.0

        pace_lock = self._get_pace_lock()
        async with pace_lock:
            now = time.monotonic()
            next_allowed = self._last_request_at + self.min_interval_seconds
            if self._last_request_at == 0.0 or now >= next_allowed:
                self._last_request_at = now
                wait_for = 0.0
            else:
                wait_for = next_allowed - now
                self._last_request_at = next_allowed

        if wait_for > 0.0:
            await asyncio.sleep(wait_for)
        return wait_for

    @asynccontextmanager
    async def slot(self, *, wait_cooldown: bool = True) -> AsyncIterator[None]:
        """
        Guard one upstream HTTP attempt with cooldown wait, concurrency cap, and pacing.

        Concurrency slots are never held while sleeping on a shared cooldown
        window, and are always released in ``finally`` on completion or cancellation.
        """
        semaphore = self._get_semaphore()
        while True:
            if wait_cooldown:
                await self.wait_for_cooldown()
            if semaphore is None:
                break
            await semaphore.acquire()
            if wait_cooldown and self.remaining_cooldown() > 0.0:
                # A sibling triggered cooldown while we waited for a slot;
                # release the slot before sleeping so we never starve concurrency.
                semaphore.release()
                continue
            break

        try:
            await self.acquire_pacing()
            yield
        finally:
            if semaphore is not None:
                semaphore.release()

    def _get_semaphore(self) -> asyncio.Semaphore | None:
        """Return the loop-scoped concurrency semaphore, or ``None`` if uncapped."""
        if self.max_concurrency <= 0:
            return None
        loop = asyncio.get_running_loop()
        semaphore = self._semaphores.get(loop)
        if semaphore is None:
            semaphore = asyncio.Semaphore(self.max_concurrency)
            self._semaphores[loop] = semaphore
        return semaphore

    def _get_pace_lock(self) -> asyncio.Lock:
        """Return the loop-scoped pacing mutex."""
        loop = asyncio.get_running_loop()
        lock = self._pace_locks.get(loop)
        if lock is None:
            lock = asyncio.Lock()
            self._pace_locks[loop] = lock
        return lock
