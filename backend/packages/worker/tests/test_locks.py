"""
Tests for the ValkeyLock distributed lock helper.

These tests require a running Valkey/Redis instance.
When Valkey is not available, they are skipped.
"""

import uuid
from unittest.mock import AsyncMock, patch

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


class TestValkeyLockCallContextManager:
    """Tests for the __call__ async context manager protocol.

    These tests mock the underlying acquire/release to avoid needing Redis.
    """

    @pytest.mark.anyio
    async def test_context_manager_acquires_and_releases(self) -> None:
        """The context manager should acquire on enter, release on exit."""
        lock = ValkeyLock("redis://localhost:6379/0")

        with patch.object(lock, "acquire", new_callable=AsyncMock) as mock_acquire:
            with patch.object(lock, "release", new_callable=AsyncMock) as mock_release:
                mock_acquire.return_value = True

                async with lock("test:key", timeout=60) as acquired:
                    assert acquired is True

                mock_acquire.assert_called_once_with(key="test:key", timeout=60)
                mock_release.assert_called_once_with(key="test:key")

    @pytest.mark.anyio
    async def test_context_manager_skips_release_on_failure(self) -> None:
        """If acquire fails, release should not be called."""
        lock = ValkeyLock("redis://localhost:6379/0")

        with patch.object(lock, "acquire", new_callable=AsyncMock) as mock_acquire:
            with patch.object(lock, "release", new_callable=AsyncMock) as mock_release:
                mock_acquire.return_value = False

                async with lock("test:key", timeout=60) as acquired:
                    assert acquired is False

                mock_acquire.assert_called_once()
                mock_release.assert_not_called()

    @pytest.mark.anyio
    async def test_context_manager_releases_on_exception(self) -> None:
        """If the body raises, the lock should still be released."""
        lock = ValkeyLock("redis://localhost:6379/0")

        with patch.object(lock, "acquire", new_callable=AsyncMock) as mock_acquire:
            with patch.object(lock, "release", new_callable=AsyncMock) as mock_release:
                mock_acquire.return_value = True

                with pytest.raises(RuntimeError, match="fail"):
                    async with lock("test:key", timeout=60) as acquired:
                        assert acquired is True
                        raise RuntimeError("fail")

                mock_acquire.assert_called_once()
                mock_release.assert_called_once_with(key="test:key")


# ===========================================================================
# Unit tests for acquire/release with mocked Redis
# ===========================================================================


class TestValkeyLockMockedRedis:
    """Unit tests for ValkeyLock methods using mocked Redis client."""

    @pytest.mark.anyio
    async def test_acquire_success(self) -> None:
        """acquire should return True when Redis SET NX succeeds."""
        lock = ValkeyLock("redis://localhost:6379/0")
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True  # type: ignore[assignment]
        lock._client = mock_redis

        from unittest.mock import ANY

        result = await lock.acquire("test:key", timeout=30)
        assert result is True
        mock_redis.set.assert_called_once_with("test:key", ANY, nx=True, ex=30)

    @pytest.mark.anyio
    async def test_acquire_failure(self) -> None:
        """acquire should return False when key already exists."""
        lock = ValkeyLock("redis://localhost:6379/0")
        mock_redis = AsyncMock()
        mock_redis.set.return_value = None  # type: ignore[assignment]
        lock._client = mock_redis

        result = await lock.acquire("test:key", timeout=30)
        assert result is False

    @pytest.mark.anyio
    async def test_release_success(self) -> None:
        """release should return True when token matches."""
        lock = ValkeyLock("redis://localhost:6379/0")
        mock_redis = AsyncMock()
        mock_redis.eval.return_value = 1  # type: ignore[assignment]
        lock._client = mock_redis
        lock._tokens["test:key"] = "test-token"

        result = await lock.release("test:key")
        assert result is True
        mock_redis.eval.assert_called_once()

    @pytest.mark.anyio
    async def test_release_no_token(self) -> None:
        """release should return False when no token stored."""
        lock = ValkeyLock("redis://localhost:6379/0")
        mock_redis = AsyncMock()
        lock._client = mock_redis

        result = await lock.release("unknown:key")
        assert result is False
        mock_redis.eval.assert_not_called()

    @pytest.mark.anyio
    async def test_release_token_mismatch(self) -> None:
        """release should return False when stored token doesn't match."""
        lock = ValkeyLock("redis://localhost:6379/0")
        mock_redis = AsyncMock()
        mock_redis.eval.return_value = 0  # type: ignore[assignment]
        lock._client = mock_redis
        lock._tokens["test:key"] = "our-token"

        result = await lock.release("test:key")
        assert result is False

        # Token remains in dict
        assert "test:key" in lock._tokens

    @pytest.mark.anyio
    async def test_close_clears_client(self) -> None:
        """close should disconnect and clear the client."""
        lock = ValkeyLock("redis://localhost:6379/0")
        mock_redis = AsyncMock()
        lock._client = mock_redis

        await lock.close()
        mock_redis.aclose.assert_called_once()
        assert lock._client is None

    @pytest.mark.anyio
    async def test_close_without_client(self) -> None:
        """close should be a no-op when client is not initialized."""
        lock = ValkeyLock("redis://localhost:6379/0")
        lock._client = None
        await lock.close()  # Should not raise


# ===========================================================================
# Integration tests (require running Valkey)
# ===========================================================================


@pytest.mark.skipif(
    not _valkey_available(),
    reason="Valkey/Redis not available on localhost:6379",
)
class TestValkeyLockIntegration:
    """Integration tests for ValkeyLock (requires running Valkey)."""

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

            released = await lock2.release(key)
            assert released is False

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
            acquired = await lock.acquire(key, timeout=1)
            assert acquired is True

            import asyncio

            await asyncio.sleep(1.5)

            lock2 = ValkeyLock("redis://localhost:6379/0")
            acquired2 = await lock2.acquire(key, timeout=30)
            assert acquired2 is True

            await lock2.release(key)
            await lock2.close()
        finally:
            await lock.close()

    @pytest.mark.anyio
    async def test_context_manager_integration(self) -> None:
        """The context manager should acquire and release in an integration setting."""
        lock = ValkeyLock("redis://localhost:6379/0")
        key = f"test:lock:{uuid.uuid4()}"

        try:
            async with lock(key, timeout=30) as acquired:
                assert acquired is True

            # After context exits, the lock should be released
            async with lock(key, timeout=30) as reacquired:
                assert reacquired is True
        finally:
            await lock.close()
