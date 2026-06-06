# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Valkey distributed lock helper for preventing concurrent target checks.
"""

import uuid
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
import structlog

logger = structlog.getLogger(__name__)


class ValkeyLock:
    """
    Distributed lock using Valkey SET NX EX.

    Usage as async context manager::

        lock = ValkeyLock(valkey_url)
        async with lock("lock:target:123", timeout=120) as acquired:
            if acquired:
                ...  # do work

    Usage as manual acquire/release::

        lock = ValkeyLock(valkey_url)
        acquired = await lock.acquire("lock:target:123", timeout=120)
        try:
            if acquired:
                ...  # do work
        finally:
            await lock.release("lock:target:123")
    """

    def __init__(self, valkey_url: str) -> None:
        self._url = valkey_url
        self._client: aioredis.Redis | None = None
        self._tokens: dict[str, str] = {}

    def __call__(self, key: str, timeout: int = 120) -> Any:
        """Return an async context manager for the lock."""

        @asynccontextmanager
        async def lock_context() -> Any:
            acquired = await self.acquire(key=key, timeout=timeout)
            try:
                yield acquired
            finally:
                if acquired:
                    await self.release(key=key)

        return lock_context()

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._url, decode_responses=True)
        return self._client

    async def acquire(self, key: str, timeout: int = 120) -> bool:
        """
        Attempt to acquire a lock. Returns True if acquired.

        Uses SET NX EX for atomic set-if-not-exists with expiry.
        Lock value is a UUID so only the holder can release.
        """
        client = await self._get_client()
        token = str(uuid.uuid4())
        acquired = await client.set(key, token, nx=True, ex=timeout)
        if acquired:
            self._tokens[key] = token
        return bool(acquired)

    async def release(self, key: str) -> bool:
        """
        Release the lock if we still hold it (check token value).
        Uses a Lua script for atomicity.
        """
        client = await self._get_client()
        token = self._tokens.get(key)
        if token is None:
            return False

        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result: Any = await client.eval(script, 1, key, token)  # type: ignore[misc]
        if result:
            del self._tokens[key]
        return bool(result)

    async def close(self) -> None:
        """Close the Valkey client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
