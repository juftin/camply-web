"""Expiring quota counters with bounded memory and shared Valkey storage."""

import asyncio
import hashlib
import heapq
import math
import time
from collections.abc import Awaitable
from dataclasses import dataclass
from threading import Lock
from typing import Protocol, cast

MAX_MEMORY_BUCKETS = 8192
VALKEY_TIMEOUT = 1.0

_CONSUME = """
local count = tonumber(redis.call("GET", KEYS[1]) or "0")
if count >= tonumber(ARGV[1]) then
    return math.max(1, redis.call("PTTL", KEYS[1]))
end
if count == 0 then
    redis.call("SET", KEYS[1], 1, "PX", ARGV[2])
else
    redis.call("INCR", KEYS[1])
end
return 0
"""


@dataclass(frozen=True)
class Policy:
    """A stable scope, request budget and window in seconds."""

    scope: str
    limit: int
    window: int


class RateLimitUnavailable(RuntimeError):
    """Quota accounting could not safely accept the request."""


class RateLimits(Protocol):
    """Storage for fixed windows that begin on their first request."""

    async def consume(self, policy: Policy, subject: str) -> int:
        """Return zero on admission or the remaining window in seconds."""

    async def close(self) -> None:
        """Release storage resources when the application shuts down."""


@dataclass
class _Window:
    count: int
    expires: float


class MemoryRateLimits:
    """Keep active local windows even when new clients exceed capacity."""

    def __init__(self, max_buckets: int = MAX_MEMORY_BUCKETS) -> None:
        self._capacity = max_buckets
        self._windows: dict[tuple[str, str], _Window] = {}
        self._expirations: list[tuple[float, tuple[str, str]]] = []
        self._lock = Lock()

    async def consume(self, policy: Policy, subject: str) -> int:
        """Consume one request from its current process-local window."""
        key = (policy.scope, subject)
        with self._lock:
            now = time.monotonic()
            while self._expirations and self._expirations[0][0] <= now:
                _, expired = heapq.heappop(self._expirations)
                del self._windows[expired]
            window = self._windows.get(key)
            if window is None:
                if len(self._windows) >= self._capacity:
                    raise RateLimitUnavailable
                window = _Window(count=0, expires=now + policy.window)
                self._windows[key] = window
                heapq.heappush(self._expirations, (window.expires, key))
            if window.count >= policy.limit:
                return math.ceil(window.expires - now)
            window.count += 1
        return 0

    async def close(self) -> None:
        """The process-local store owns no external resources."""


class ValkeyRateLimits:
    """Admit or reject atomically across backend workers."""

    def __init__(self, url: str) -> None:
        try:
            import redis
        except ModuleNotFoundError as exc:
            if exc.name != "redis":
                raise
            raise RuntimeError(
                "Valkey API quotas require installing 'camply-web[distributed]'."
            ) from exc
        self._redis_error = redis.RedisError
        self._client = redis.asyncio.Redis.from_url(
            url,
            socket_connect_timeout=VALKEY_TIMEOUT,
            socket_timeout=VALKEY_TIMEOUT,
            max_connections=64,
        )

    async def consume(self, policy: Policy, subject: str) -> int:
        """Consume one request without extending the counter's expiry."""
        digest = hashlib.sha256(subject.encode()).hexdigest()
        key = f"camply:api-quota:{policy.scope}:{digest}"
        try:
            async with asyncio.timeout(VALKEY_TIMEOUT):
                remaining = await cast(
                    Awaitable[object],
                    self._client.eval(
                        _CONSUME, 1, key, policy.limit, policy.window * 1000
                    ),
                )
        except (self._redis_error, TimeoutError) as exc:
            raise RateLimitUnavailable from exc
        if not isinstance(remaining, int) or remaining < 0:
            raise RateLimitUnavailable
        return math.ceil(remaining / 1000)

    async def close(self) -> None:
        """Close this worker's Valkey pool."""
        await self._client.aclose()
