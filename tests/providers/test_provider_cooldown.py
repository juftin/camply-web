"""Tests for shared per-provider cooldown gates, Retry-After parsing, and concurrency pacing."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx2
import pytest

from camply.providers.base import BaseProvider, RetryStrategy, RetryTransport
from camply.providers.cooldown import ProviderCooldownGate, parse_retry_after
from camply.providers.errors import ProviderRateLimitedError
from camply.providers.transport_config import (
    TransportEvent,
    register_transport_observer,
    unregister_transport_observer,
)


def _make_response(
    status_code: int, headers: dict[str, str] | None = None
) -> httpx2.Response:
    """Build a synthetic ``httpx2.Response`` for cooldown tests."""
    return httpx2.Response(
        status_code=status_code,
        headers=headers or {},
        request=httpx2.Request("GET", "https://example.com/api"),
    )


class _DummyProviderA(BaseProvider):
    """Concrete provider A for cross-instance pacing and cooldown isolation tests."""

    async def search_upstream(self, query):  # type: ignore[override]
        return []

    async def find_availabilities(self, park_id, start_date, end_date):  # type: ignore[override]
        return []

    async def sync_metadata(self) -> None:
        return None

    async def populate_database(self) -> None:
        return None

    @property
    def provider(self):  # type: ignore[override]
        from camply.db.models import Provider

        return Provider(id=101, name="DummyA", url="https://a.example")

    @classmethod
    def get_rec_area_url(cls, rec_area_id: str) -> str:
        return f"https://a.example/area/{rec_area_id}"

    @classmethod
    def get_campground_url(
        cls, campground_id: str, *, rec_area_id: str | None = None
    ) -> str:
        return f"https://a.example/camp/{campground_id}"


class _DummyProviderB(_DummyProviderA):
    """Distinct provider subclass B to verify cross-provider cooldown isolation."""


class TestParseRetryAfter:
    """Tests for numeric and RFC 9110 HTTP-date Retry-After parsing."""

    @pytest.mark.parametrize(
        ("header", "max_seconds", "expected"),
        [
            (None, 60.0, None),
            ("", 60.0, None),
            ("   ", 60.0, None),
            ("5", 60.0, 5.0),
            ("2.5", 60.0, 2.5),
            ("0", 60.0, None),
            ("-3", 60.0, None),
            ("nan", 60.0, None),
            ("inf", 60.0, None),
            ("-inf", 60.0, None),
            ("86400", 60.0, 60.0),
            ("not-a-date-or-number", 60.0, None),
        ],
    )
    def test_numeric_and_invalid_values(
        self, header: str | None, max_seconds: float, expected: float | None
    ) -> None:
        """Numeric Retry-After values parse, clamp, and reject non-positive/non-finite inputs."""
        assert parse_retry_after(header, max_seconds=max_seconds) == expected

    def test_http_date_future_clamped_and_past(self) -> None:
        """RFC 9110 HTTP-date headers compute UTC deltas, clamp to max_seconds, and ignore past dates."""
        now = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
        assert (
            parse_retry_after(
                "Wed, 21 Oct 2026 07:28:15 GMT",
                max_seconds=60.0,
                now_utc=now,
            )
            == 15.0
        )
        assert (
            parse_retry_after(
                "Wed, 21 Oct 2026 08:28:00 GMT",
                max_seconds=60.0,
                now_utc=now,
            )
            == 60.0
        )
        assert (
            parse_retry_after(
                "Wed, 21 Oct 2026 07:27:00 GMT",
                max_seconds=60.0,
                now_utc=now,
            )
            is None
        )


class TestProviderCooldownGate:
    """Unit and concurrency tests for ProviderCooldownGate."""

    @pytest.mark.asyncio
    async def test_cooldown_deadline_is_monotonic_and_clamped(self) -> None:
        """Shorter delays cannot shorten an active longer cooldown deadline."""
        gate = ProviderCooldownGate(
            provider_name="ProviderA",
            max_concurrency=4,
            min_interval_seconds=0.0,
            max_cooldown_seconds=10.0,
        )
        first = gate.trigger_cooldown(100.0, reason="429")
        assert first == 10.0
        deadline_after_first = gate.cooldown_until

        second = gate.trigger_cooldown(2.0, reason="429")
        assert second == 2.0
        assert gate.cooldown_until == deadline_after_first

    @pytest.mark.asyncio
    async def test_cross_provider_isolation(self) -> None:
        """An active cooldown on Provider A does not delay Provider B."""
        gate_a = ProviderCooldownGate("ProviderA", max_cooldown_seconds=10.0)
        gate_b = ProviderCooldownGate("ProviderB", max_cooldown_seconds=10.0)
        gate_a.trigger_cooldown(5.0, reason="429")

        start = time.monotonic()
        async with gate_b.slot():
            elapsed = time.monotonic() - start
        assert elapsed < 0.1
        assert gate_a.remaining_cooldown() > 4.0

    @pytest.mark.asyncio
    async def test_sibling_concurrent_requests_wait_for_shared_429_cooldown(
        self,
    ) -> None:
        """When one request receives HTTP 429, queued siblings wait until cooldown expires."""
        gate = ProviderCooldownGate(
            provider_name="BurstProvider",
            max_concurrency=2,
            max_cooldown_seconds=5.0,
        )
        transport = RetryTransport(
            retry_strategy=RetryStrategy(max_retries=2, jitter=False),
            provider_name="BurstProvider",
            cooldown_gate=gate,
            max_cooldown_seconds=5.0,
        )
        transport._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)

        cooldown_delay = 0.15
        dispatch_times: list[float] = []
        cooldown_triggered_at: list[float] = []
        call_count = 0

        async def fake_send(request: httpx2.Request) -> httpx2.Response:
            nonlocal call_count
            call_count += 1
            now = time.monotonic()
            dispatch_times.append(now)
            if call_count == 1:
                cooldown_triggered_at.append(now)
                return _make_response(429, headers={"Retry-After": str(cooldown_delay)})
            await asyncio.sleep(0.01)
            return _make_response(200)

        transport._inner.handle_async_request = AsyncMock(side_effect=fake_send)
        events: list[TransportEvent] = []
        register_transport_observer(events.append)
        try:
            requests = [
                httpx2.Request("GET", f"https://example.com/item/{idx}")
                for idx in range(10)
            ]
            responses = await asyncio.gather(
                *(transport.handle_async_request(req) for req in requests)
            )
        finally:
            unregister_transport_observer(events.append)
            await transport.aclose()

        assert all(resp.status_code == 200 for resp in responses)
        assert cooldown_triggered_at
        # After the initial pair (concurrency=2) starts, queued siblings must wait
        # until the shared cooldown deadline has elapsed.
        queued_dispatches = dispatch_times[2:]
        assert queued_dispatches
        assert all(
            t >= cooldown_triggered_at[0] + cooldown_delay - 0.02
            for t in queued_dispatches
        )
        assert any(
            e.kind == "cooldown_wait" and e.provider == "BurstProvider" for e in events
        )

    @pytest.mark.asyncio
    async def test_429_fallback_uses_retry_strategy_base_delay_and_persists_after_exhaustion(
        self,
    ) -> None:
        """429 without Retry-After uses base_delay (clamped) and keeps cooldown active after exhaustion."""
        gate = ProviderCooldownGate(
            provider_name="RateLimitedProvider",
            max_concurrency=4,
            max_cooldown_seconds=0.12,
        )
        strategy = RetryStrategy(
            max_retries=1,
            base_delay=0.08,
            max_delay=1.0,
            _5xx_base_delay=0.01,
            jitter=False,
        )
        transport = RetryTransport(
            retry_strategy=strategy,
            provider_name="RateLimitedProvider",
            cooldown_gate=gate,
            max_cooldown_seconds=0.12,
        )
        transport._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)
        transport._inner.handle_async_request = AsyncMock(
            side_effect=[_make_response(429), _make_response(429)]
        )

        start = time.monotonic()
        with pytest.raises(ProviderRateLimitedError):
            await transport.handle_async_request(
                httpx2.Request("GET", "https://example.com/api")
            )
        elapsed = time.monotonic() - start
        # Attempt 0 triggers 0.08s cooldown (base_delay, not _5xx_base_delay=0.01s).
        assert elapsed >= 0.07
        # Final exhausted 429 triggers attempt-1 cooldown (min(0.16, 0.12) = 0.12s).
        assert gate.remaining_cooldown() > 0.05
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_concurrency_cap_and_unlimited_mode(self) -> None:
        """Bounded concurrency caps peak in-flight requests; 0 disables the cap."""
        gate = ProviderCooldownGate("CappedProvider", max_concurrency=4)
        active = 0
        peak = 0

        async def work() -> None:
            nonlocal active, peak
            async with gate.slot():
                active += 1
                peak = max(peak, active)
                await asyncio.sleep(0.02)
                active -= 1

        await asyncio.gather(*(work() for _ in range(20)))
        assert peak == 4

        unlimited_gate = ProviderCooldownGate("UnlimitedProvider", max_concurrency=0)
        active_u = 0
        peak_u = 0

        async def work_unlimited() -> None:
            nonlocal active_u, peak_u
            async with unlimited_gate.slot():
                active_u += 1
                peak_u = max(peak_u, active_u)
                await asyncio.sleep(0.02)
                active_u -= 1

        await asyncio.gather(*(work_unlimited() for _ in range(10)))
        assert peak_u == 10

    @pytest.mark.asyncio
    async def test_concurrency_slot_released_before_retry_backoff_sleep(self) -> None:
        """A request sleeping for retry backoff must release its concurrency slot."""
        gate = ProviderCooldownGate("SlotReleaseProvider", max_concurrency=1)
        transport = RetryTransport(
            retry_strategy=RetryStrategy(
                max_retries=1,
                _5xx_base_delay=0.15,
                jitter=False,
            ),
            provider_name="SlotReleaseProvider",
            cooldown_gate=gate,
        )
        transport._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)

        req1_first_done = asyncio.Event()
        req2_completed_before_req1_retry = False
        req1_calls = 0

        async def fake_send(request: httpx2.Request) -> httpx2.Response:
            nonlocal req1_calls, req2_completed_before_req1_retry
            if str(request.url).endswith("/first"):
                req1_calls += 1
                if req1_calls == 1:
                    req1_first_done.set()
                    return _make_response(500)
                return _make_response(200)
            # Second request runs while first is sleeping for 500 backoff
            if req1_calls == 1:
                req2_completed_before_req1_retry = True
            return _make_response(200)

        transport._inner.handle_async_request = AsyncMock(side_effect=fake_send)

        task1 = asyncio.create_task(
            transport.handle_async_request(
                httpx2.Request("GET", "https://example.com/first")
            )
        )
        await req1_first_done.wait()
        await asyncio.sleep(0.01)
        resp2 = await transport.handle_async_request(
            httpx2.Request("GET", "https://example.com/second")
        )
        resp1 = await task1
        await transport.aclose()

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert req2_completed_before_req1_retry is True

    @pytest.mark.asyncio
    async def test_min_interval_pacing_across_provider_instances(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Configured min_interval_seconds spaces request starts across instances without blocking others."""
        BaseProvider.reset_transport_state()
        monkeypatch.setenv("CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS", "0.06")
        monkeypatch.setenv("CAMPLY_PROVIDER_MAX_CONCURRENCY", "4")
        try:
            provider_a1 = _DummyProviderA()
            provider_a2 = _DummyProviderA()
            provider_b = _DummyProviderB()

            starts_a: list[float] = []
            start_b: list[float] = []

            async def send_a(request: httpx2.Request) -> httpx2.Response:
                starts_a.append(time.monotonic())
                return _make_response(200)

            async def send_b(request: httpx2.Request) -> httpx2.Response:
                start_b.append(time.monotonic())
                return _make_response(200)

            for inst in (provider_a1, provider_a2):
                transport = inst.async_client._transport
                assert isinstance(transport, RetryTransport)
                transport._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)
                transport._inner.handle_async_request = AsyncMock(side_effect=send_a)

            transport_b = provider_b.async_client._transport
            assert isinstance(transport_b, RetryTransport)
            transport_b._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)
            transport_b._inner.handle_async_request = AsyncMock(side_effect=send_b)

            await asyncio.gather(
                provider_a1.async_client.get("https://a.example/1"),
                provider_a2.async_client.get("https://a.example/2"),
                provider_a1.async_client.get("https://a.example/3"),
                provider_b.async_client.get("https://b.example/1"),
            )

            starts_a.sort()
            assert len(starts_a) == 3
            assert starts_a[1] - starts_a[0] >= 0.05
            assert starts_a[2] - starts_a[1] >= 0.05
            # Provider B was not delayed behind Provider A's 3-request pacing queue
            assert start_b[0] - starts_a[0] < 0.05

            await provider_a1.async_client.aclose()
            await provider_a2.async_client.aclose()
            await provider_b.async_client.aclose()
        finally:
            BaseProvider.reset_transport_state()

    @pytest.mark.asyncio
    async def test_cancellation_during_wait_preserves_slot_and_state(self) -> None:
        """Cancelling a task waiting on cooldown or semaphore leaves the gate healthy."""
        gate = ProviderCooldownGate("CancelProvider", max_concurrency=1)
        gate.trigger_cooldown(5.0, reason="429")

        async def waiter() -> None:
            async with gate.slot():
                pass

        task = asyncio.create_task(waiter())
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        gate.reset()
        entered = False
        async with gate.slot():
            entered = True
        assert entered is True

    def test_sequential_asyncio_run_event_loops_are_safe(self) -> None:
        """Reusing one ProviderCooldownGate across sequential asyncio.run() loops never deadlocks."""
        gate = ProviderCooldownGate(
            "MultiLoopProvider",
            max_concurrency=2,
            min_interval_seconds=0.01,
            max_cooldown_seconds=5.0,
        )

        async def run_first_loop() -> None:
            async with gate.slot():
                gate.trigger_cooldown(0.05, reason="429")

        async def run_second_loop() -> float:
            start = time.monotonic()
            async with gate.slot():
                return time.monotonic() - start

        asyncio.run(run_first_loop())
        elapsed = asyncio.run(run_second_loop())
        assert elapsed >= 0.03
