"""Verify fixed windows, saturation, and accounting across Valkey connections."""

import asyncio
import os
import uuid

import pytest

from camply.server import rate_limits
from camply.server.rate_limits import (
    MemoryRateLimits,
    Policy,
    RateLimitUnavailable,
    ValkeyRateLimits,
)


@pytest.mark.asyncio
async def test_memory_window_expiry_and_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Capacity preserves active buckets and an increment cannot extend a window."""
    now = 100
    monkeypatch.setattr(rate_limits.time, "monotonic", lambda: now)
    store = MemoryRateLimits(max_buckets=1)
    policy = Policy("synthetic", 2, 60)
    assert await store.consume(policy, "first") == 0
    now += 30
    assert await store.consume(policy, "first") == 0
    with pytest.raises(RateLimitUnavailable):
        await store.consume(policy, "second")
    assert await store.consume(policy, "first") == 30
    now += 30
    assert await store.consume(policy, "second") == 0


@pytest.mark.asyncio
async def test_shared_valkey_enforces_one_atomic_budget() -> None:
    """Two clients share admission and expiry when pointed at fixture Valkey."""
    if not (url := os.environ.get("CAMPLY_API_TEST_VALKEY_URL")):
        pytest.skip("Set CAMPLY_API_TEST_VALKEY_URL to a disposable Valkey instance")
    first = ValkeyRateLimits(url)
    second = ValkeyRateLimits(url)
    policy = Policy(f"synthetic-{uuid.uuid4().hex}", 10, 2)
    try:
        results = await asyncio.gather(
            *(store.consume(policy, "shared") for store in (first, second) * 10)
        )
        assert results.count(0) == 10
        assert all(0 <= retry <= policy.window for retry in results)
        assert await second.consume(policy, "different") == 0
        await asyncio.sleep(policy.window)
        assert await first.consume(policy, "shared") == 0
    finally:
        await first.close()
        await second.close()
