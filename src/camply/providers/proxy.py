"""
Opt-in in-process BYO proxy rotation pool and quarantine state management.

Manages round-robin proxy selection across validated ``ProxyEndpoint`` entries,
provider-scoped quarantines (HTTP 429/403), global quarantines (proxy transport
errors), and strict fail-closed exhaustion handling without ever falling back to
direct host egress.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import structlog

from camply.providers.errors import ProxyPoolExhaustedError
from camply.providers.transport_config import (
    ProxyEndpoint,
    ProxyExhaustedPolicy,
    TransportEvent,
    emit_transport_event,
)

logger = structlog.getLogger(__name__)


@dataclass
class ProxyEntry:
    """
    Mutable runtime health state for one configured proxy endpoint.

    Parameters
    ----------
    endpoint : ProxyEndpoint
        Immutable, credential-safe endpoint descriptor.
    global_quarantined_until : float, optional
        Monotonic deadline for global proxy failures affecting all providers.
    provider_quarantined_until : dict[str, float], optional
        Per-provider monotonic quarantine deadlines for HTTP 429/403 responses.
    quarantine_count : int, optional
        Total number of quarantine events recorded for this proxy in process.
    last_reason : str | None, optional
        Most recent quarantine reason code.
    """

    endpoint: ProxyEndpoint
    global_quarantined_until: float = 0.0
    provider_quarantined_until: dict[str, float] = field(default_factory=dict)
    quarantine_count: int = 0
    last_reason: str | None = None

    def quarantine_until(self, provider_name: str) -> float:
        """Return the effective monotonic quarantine deadline for *provider_name*."""
        return max(
            self.global_quarantined_until,
            self.provider_quarantined_until.get(provider_name, 0.0),
        )

    def is_healthy(self, provider_name: str, now: float | None = None) -> bool:
        """Return ``True`` when the proxy is not quarantined for *provider_name*."""
        current = time.monotonic() if now is None else now
        return current >= self.quarantine_until(provider_name)


class ProxyPool:
    """
    In-process round-robin pool of BYO proxies with provider- and global-scoped quarantine.

    Parameters
    ----------
    endpoints : Sequence[ProxyEndpoint]
        Non-empty ordered sequence of validated proxy endpoints.
    quarantine_seconds : float, optional
        Default quarantine duration in seconds (default ``60.0``).
    max_wait_seconds : float, optional
        Maximum seconds ``wait`` policy may pause before failing fast (default ``60.0``).
    exhausted_policy : ProxyExhaustedPolicy, optional
        Behavior when every proxy is quarantined: ``"wait"`` or ``"fail"``.
    """

    def __init__(
        self,
        endpoints: Sequence[ProxyEndpoint],
        *,
        quarantine_seconds: float = 60.0,
        max_wait_seconds: float = 60.0,
        exhausted_policy: ProxyExhaustedPolicy = "wait",
    ) -> None:
        if not endpoints:
            raise ValueError("ProxyPool requires at least one validated proxy endpoint")
        self.entries: tuple[ProxyEntry, ...] = tuple(
            ProxyEntry(endpoint=ep) for ep in endpoints
        )
        self.quarantine_seconds = quarantine_seconds
        self.max_wait_seconds = max_wait_seconds
        self.exhausted_policy: ProxyExhaustedPolicy = exhausted_policy
        self._cursor: int = 0
        self._credential_tokens: tuple[str, ...] = tuple(
            dict.fromkeys(
                token
                for entry in self.entries
                for token in entry.endpoint.credential_tokens()
            )
        )

    def __len__(self) -> int:
        """Return the number of configured proxies in the pool."""
        return len(self.entries)

    def __repr__(self) -> str:
        """Return a credential-free summary representation of the proxy pool."""
        labels = ", ".join(entry.endpoint.label for entry in self.entries)
        return (
            f"ProxyPool(size={len(self.entries)}, "
            f"policy={self.exhausted_policy!r}, endpoints=[{labels}])"
        )

    def credential_tokens(self) -> tuple[str, ...]:
        """Return all configured credential tokens for defensive error scrubbing."""
        return self._credential_tokens

    async def select(self, provider_name: str) -> ProxyEndpoint:
        """
        Select the next healthy proxy for *provider_name* in round-robin order.

        When every proxy is quarantined, ``exhausted_policy == "wait"`` pauses up
        to ``max_wait_seconds`` for the soonest expiry; ``"fail"`` or waits above
        the cap raise ``ProxyPoolExhaustedError`` without direct-egress fallback.
        """
        pool_size = len(self.entries)
        while True:
            now = time.monotonic()
            for offset in range(pool_size):
                idx = (self._cursor + offset) % pool_size
                entry = self.entries[idx]
                if entry.is_healthy(provider_name, now):
                    self._cursor = (idx + 1) % pool_size
                    emit_transport_event(
                        TransportEvent(
                            kind="proxy_selected",
                            provider=provider_name,
                            reason="round_robin",
                            proxy_label=entry.endpoint.label,
                        )
                    )
                    return entry.endpoint

            soonest_deadline = min(
                entry.quarantine_until(provider_name) for entry in self.entries
            )
            soonest_wait = max(0.0, soonest_deadline - now)

            if self.exhausted_policy == "fail":
                self._raise_exhausted(
                    provider_name=provider_name,
                    reason="all_quarantined",
                    retry_after=soonest_wait,
                )

            if soonest_wait > self.max_wait_seconds:
                self._raise_exhausted(
                    provider_name=provider_name,
                    reason="wait_cap_exceeded",
                    retry_after=soonest_wait,
                )

            if soonest_wait > 0.0:
                logger.debug(
                    "Provider cooldown active; waiting",
                    provider=provider_name,
                    delay_seconds=round(soonest_wait, 3),
                    reason="all_quarantined",
                )
                emit_transport_event(
                    TransportEvent(
                        kind="cooldown_wait",
                        provider=provider_name,
                        reason="all_quarantined",
                        delay_seconds=soonest_wait,
                    )
                )
                await asyncio.sleep(soonest_wait)

    def quarantine(
        self,
        index: int,
        *,
        provider_name: str,
        reason: str,
        duration: float | None = None,
        global_scope: bool = False,
    ) -> float:
        """
        Quarantine proxy at *index* either for *provider_name* or globally.

        Parameters
        ----------
        index : int
            0-based proxy slot index.
        provider_name : str
            Concrete provider class name that triggered the quarantine.
        reason : str
            Low-cardinality reason code (e.g., ``429``, ``403``, ``proxy_error``).
        duration : float | None, optional
            Explicit quarantine duration in seconds; falls back to
            ``self.quarantine_seconds`` when ``None`` or non-positive.
        global_scope : bool, optional
            When ``True``, quarantines the proxy across all providers.

        Returns
        -------
        float
            Effective quarantine duration in seconds.
        """
        entry = self.entries[index]
        window = (
            duration
            if (duration is not None and math.isfinite(duration) and duration > 0.0)
            else self.quarantine_seconds
        )
        deadline = time.monotonic() + window
        if global_scope:
            entry.global_quarantined_until = max(
                entry.global_quarantined_until, deadline
            )
            scope = "global"
        else:
            current = entry.provider_quarantined_until.get(provider_name, 0.0)
            entry.provider_quarantined_until[provider_name] = max(current, deadline)
            scope = "provider"

        entry.quarantine_count += 1
        entry.last_reason = reason
        logger.warning(
            "Proxy quarantined",
            provider=provider_name,
            proxy=entry.endpoint.label,
            reason=reason,
            scope=scope,
            quarantine_seconds=round(window, 3),
        )
        emit_transport_event(
            TransportEvent(
                kind="proxy_quarantined",
                provider=provider_name,
                reason=reason,
                proxy_label=entry.endpoint.label,
                delay_seconds=window,
            )
        )
        return window

    def snapshot(self, provider_name: str | None = None) -> list[dict[str, Any]]:
        """Return a credential-free diagnostic snapshot of pool health."""
        now = time.monotonic()
        rows: list[dict[str, Any]] = []
        for entry in self.entries:
            deadline = (
                entry.quarantine_until(provider_name)
                if provider_name is not None
                else entry.global_quarantined_until
            )
            remaining = max(0.0, deadline - now)
            rows.append(
                {
                    "index": entry.endpoint.index,
                    "label": entry.endpoint.label,
                    "healthy": remaining <= 0.0,
                    "quarantine_remaining": round(remaining, 3),
                    "quarantine_count": entry.quarantine_count,
                    "last_reason": entry.last_reason,
                }
            )
        return rows

    def reset(self) -> None:
        """Clear all quarantine deadlines and reset round-robin cursor."""
        self._cursor = 0
        for entry in self.entries:
            entry.global_quarantined_until = 0.0
            entry.provider_quarantined_until.clear()
            entry.quarantine_count = 0
            entry.last_reason = None

    def _raise_exhausted(
        self,
        *,
        provider_name: str,
        reason: str,
        retry_after: float,
    ) -> None:
        """Log, emit metric event, and raise ``ProxyPoolExhaustedError``."""
        pool_size = len(self.entries)
        logger.warning(
            "Proxy pool exhausted",
            provider=provider_name,
            policy=self.exhausted_policy,
            pool_size=pool_size,
            retry_after_seconds=round(retry_after, 3),
        )
        emit_transport_event(
            TransportEvent(
                kind="proxy_exhausted",
                provider=provider_name,
                reason=reason,
                delay_seconds=retry_after,
            )
        )
        raise ProxyPoolExhaustedError(
            provider_name,
            retry_after=retry_after,
            pool_size=pool_size,
        )
