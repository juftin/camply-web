"""
Tests for the ValkeyLock distributed lock helper.

These tests require a running Valkey/Redis instance.
When Valkey is not available, they are skipped.
"""

import uuid

import pytest

from worker.locks import ValkeyLock


def _valkey_available() -> bool:
    """Check if a Valkey/Redis instance is reachable."""
    try:
        import redis

        r = redis.Redis.from_url("redis://localhost:6379/0", socket_connect_timeout=2)
        r.ping()
        r.close()
        return True
    except Exception:
        return False


valkey_required = pytest.mark.skipif(
    not _valkey_available(),
    reason="Valkey/Redis not available on localhost:6379",
)


@pytest.mark.skipif(
    not _valkey_available(),
    reason="Valkey/Redis not available on localhost:6379",
)
class TestValkeyLock:
    """Tests for the ValkeyLock class (requires running Valkey)."""

    @pytest.mark.anyio
    async def test_acquire_and_release(self) -> None:
        """Basic lock lifecycle: acquire then release."""
        lock = ValkeyLock("redis://localhost:6379/0")
        key = f"test:lock:{uuid.uuid4()}"

        try:
            acquired = await lock.acquire(key, timeout=30)
            assert acquired is True

            released = await lock.release(key)
            assert released is True
        finally:
            await lock.close()

    @pytest.mark.anyio
    async def test_concurrent_acquire_fails(self) -> None:
        """Two locks on the same key: only one succeeds."""
        lock1 = ValkeyLock("redis://localhost:6379/0")
        lock2 = ValkeyLock("redis://localhost:6379/0")
        key = f"test:lock:{uuid.uuid4()}"

        try:
            acquired1 = await lock1.acquire(key, timeout=30)
            assert acquired1 is True

            acquired2 = await lock2.acquire(key, timeout=30)
            assert acquired2 is False

            await lock1.release(key)
        finally:
            await lock1.close()
            await lock2.close()

    @pytest.mark.anyio
    async def test_token_based_release(self) -> None:
        """Lock B cannot release Lock A's key."""
        lock1 = ValkeyLock("redis://localhost:6379/0")
        lock2 = ValkeyLock("redis://localhost:6379/0")
        key = f"test:lock:{uuid.uuid4()}"

        try:
            acquired = await lock1.acquire(key, timeout=30)
            assert acquired is True

            # lock2 should NOT be able to release lock1's lock
            released = await lock2.release(key)
            assert released is False

            # lock1 should still be able to release
            released = await lock1.release(key)
            assert released is True
        finally:
            await lock1.close()
            await lock2.close()

    @pytest.mark.anyio
    async def test_lock_expiry(self) -> None:
        """Lock should auto-expire after timeout."""
        lock = ValkeyLock("redis://localhost:6379/0")
        key = f"test:lock:{uuid.uuid4()}"

        try:
            acquired = await lock.acquire(key, timeout=1)  # 1 second expiry
            assert acquired is True

            # Wait for expiry
            import asyncio

            await asyncio.sleep(1.5)

            # A new lock should be able to acquire the same key
            lock2 = ValkeyLock("redis://localhost:6379/0")
            acquired2 = await lock2.acquire(key, timeout=30)
            assert acquired2 is True

            await lock2.release(key)
            await lock2.close()
        finally:
            await lock.close()
