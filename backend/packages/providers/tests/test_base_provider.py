"""
Tests for the BaseProvider abstract class, retry transport, and circuit breaker.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from providers.base import (
    BaseProvider,
    DatabasePopulator,
    ProviderCircuitBreaker,
    RetryStrategy,
    RetryTransport,
)
from providers.errors import CircuitBreakerOpenError, ProviderRateLimitedError

# ===========================================================================
# Concrete subclass for testing BaseProvider
# ===========================================================================


class ConcreteProvider(BaseProvider):
    """Minimal concrete subclass of BaseProvider for testing."""

    async def find_availabilities(self, park_id, start_date, end_date):
        return []

    async def sync_metadata(self):
        pass

    async def populate_database(self):
        pass

    @property
    def provider(self):
        from db.models import Provider

        return Provider(id=1, name="TestProvider", url="https://test.provider")

    @classmethod
    def get_rec_area_url(cls, rec_area_id):
        return f"https://test.provider/area/{rec_area_id}"

    @classmethod
    def get_campground_url(cls, campground_id):
        return f"https://test.provider/camp/{campground_id}"


@pytest.fixture
def anyio_backend() -> str:
    """Limit anyio to asyncio backend only (trio is not installed)."""
    return "asyncio"


# ===========================================================================
# RetryStrategy tests
# ===========================================================================


class TestRetryStrategy:
    """Tests for the RetryStrategy dataclass."""

    def test_defaults(self) -> None:
        strategy = RetryStrategy()
        assert strategy.max_retries == 3
        assert strategy.base_delay == 1.0
        assert strategy.max_delay == 60.0
        assert strategy.backoff_factor == 2.0
        assert strategy.jitter is True
        assert strategy.retry_on_429 is True
        assert strategy.retry_on_5xx is True
        assert strategy.retry_on_connection_errors is True

    def test_custom_values(self) -> None:
        strategy = RetryStrategy(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            backoff_factor=3.0,
            jitter=False,
            retry_on_429=False,
        )
        assert strategy.max_retries == 5
        assert strategy.base_delay == 2.0
        assert strategy.max_delay == 120.0
        assert strategy.backoff_factor == 3.0
        assert strategy.jitter is False
        assert strategy.retry_on_429 is False


class TestRetryStrategyProviderOverride:
    """Tests for overriding retry strategy on BaseProvider subclasses."""

    def test_provider_default_retry_strategy(self) -> None:
        class CustomProvider(ConcreteProvider):
            pass

        provider = CustomProvider()
        strategy = provider.retry_strategy
        assert isinstance(strategy, RetryStrategy)
        assert strategy.max_retries == 3

    def test_provider_overrides_retry_strategy(self) -> None:
        class CustomProvider(ConcreteProvider):
            @property
            def retry_strategy(self) -> RetryStrategy:
                return RetryStrategy(
                    max_retries=7,
                    base_delay=3.0,
                    max_delay=90.0,
                )

        provider = CustomProvider()
        strategy = provider.retry_strategy
        assert strategy.max_retries == 7
        assert strategy.base_delay == 3.0
        assert strategy.max_delay == 90.0


# ===========================================================================
# Helper for building responses
# ===========================================================================


def _make_response(
    status_code: int, headers: dict[str, str] | None = None
) -> httpx.Response:
    """Helper to build a minimal ``httpx.Response`` for testing."""
    return httpx.Response(
        status_code=status_code,
        headers=headers or {},
        request=httpx.Request("GET", "https://example.com/api"),
    )


class _TransportMixin:
    """Mixin providing a convenience method for running requests through a transport."""

    @staticmethod
    async def _run_request(transport: RetryTransport) -> httpx.Response:
        """Send a basic GET request through *transport*."""
        request = httpx.Request("GET", "https://example.com/api")
        return await transport.handle_async_request(request)


# ===========================================================================
# RetryTransport tests
# ===========================================================================


class TestRetryTransportUnit(_TransportMixin):
    """Unit tests for ``RetryTransport`` using mocked inner transports."""

    pytestmark = pytest.mark.anyio

    # ── normal request ─────────────────────────────────────────────────

    async def test_normal_request_succeeds_on_first_try(self) -> None:
        strategy = RetryStrategy(max_retries=3, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_200 = _make_response(200)
        transport._inner.handle_async_request = AsyncMock(return_value=response_200)

        response = await self._run_request(transport)
        assert response.status_code == 200
        transport._inner.handle_async_request.assert_awaited_once()

    # ── 429 handling ───────────────────────────────────────────────────

    async def test_retries_on_429_with_exponential_backoff(self) -> None:
        strategy = RetryStrategy(max_retries=3, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_429 = _make_response(429)
        response_200 = _make_response(200)

        transport._inner.handle_async_request = AsyncMock(
            side_effect=[response_429, response_429, response_429, response_200]
        )

        response = await self._run_request(transport)
        assert response.status_code == 200
        assert (
            transport._inner.handle_async_request.await_count == 4
        )  # 3 retries + 1 initial

    async def test_retries_on_429_uses_retry_after_header(self) -> None:
        strategy = RetryStrategy(max_retries=2, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_429 = _make_response(429, headers={"Retry-After": "0.01"})
        response_200 = _make_response(200)

        transport._inner.handle_async_request = AsyncMock(
            side_effect=[response_429, response_200]
        )

        response = await self._run_request(transport)
        assert response.status_code == 200

    async def test_exhausts_retries_and_raises_on_429(self) -> None:
        strategy = RetryStrategy(max_retries=2, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_429 = _make_response(429)
        transport._inner.handle_async_request = AsyncMock(
            side_effect=[response_429, response_429, response_429]
        )

        with pytest.raises(ProviderRateLimitedError) as excinfo:
            await self._run_request(transport)
        assert "Rate limited" in str(excinfo.value)

    async def test_does_not_retry_on_429_when_disabled(self) -> None:
        strategy = RetryStrategy(max_retries=3, jitter=False, retry_on_429=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_429 = _make_response(429)
        transport._inner.handle_async_request = AsyncMock(return_value=response_429)

        response = await self._run_request(transport)
        assert response.status_code == 429
        transport._inner.handle_async_request.assert_awaited_once()

    # ── 5xx handling ───────────────────────────────────────────────────

    async def test_retries_on_5xx(self) -> None:
        strategy = RetryStrategy(max_retries=2, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_500 = _make_response(500)
        response_200 = _make_response(200)

        transport._inner.handle_async_request = AsyncMock(
            side_effect=[response_500, response_500, response_200]
        )

        response = await self._run_request(transport)
        assert response.status_code == 200
        assert transport._inner.handle_async_request.await_count == 3

    async def test_exhausts_retries_and_returns_last_5xx_response(self) -> None:
        """When all retries are exhausted on 5xx, returns the last response."""
        strategy = RetryStrategy(max_retries=2, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_500 = _make_response(500)
        transport._inner.handle_async_request = AsyncMock(
            side_effect=[response_500, response_500, response_500]
        )

        # Transport returns the last 5xx response instead of raising
        response = await self._run_request(transport)
        assert response.status_code == 500

    async def test_does_not_retry_on_5xx_when_disabled(self) -> None:
        strategy = RetryStrategy(max_retries=3, jitter=False, retry_on_5xx=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_500 = _make_response(500)
        transport._inner.handle_async_request = AsyncMock(return_value=response_500)

        response = await self._run_request(transport)
        assert response.status_code == 500
        transport._inner.handle_async_request.assert_awaited_once()

    # ── 4xx non-429 handling ───────────────────────────────────────────

    async def test_does_not_retry_on_4xx_non_429(self) -> None:
        strategy = RetryStrategy(max_retries=3, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_404 = _make_response(404)
        transport._inner.handle_async_request = AsyncMock(return_value=response_404)

        response = await self._run_request(transport)
        assert response.status_code == 404
        transport._inner.handle_async_request.assert_awaited_once()

    async def test_does_not_retry_on_400(self) -> None:
        strategy = RetryStrategy(max_retries=3, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_400 = _make_response(400)
        transport._inner.handle_async_request = AsyncMock(return_value=response_400)

        response = await self._run_request(transport)
        assert response.status_code == 400
        transport._inner.handle_async_request.assert_awaited_once()

    async def test_does_not_retry_on_401(self) -> None:
        strategy = RetryStrategy(max_retries=3, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_401 = _make_response(401)
        transport._inner.handle_async_request = AsyncMock(return_value=response_401)

        response = await self._run_request(transport)
        assert response.status_code == 401
        transport._inner.handle_async_request.assert_awaited_once()

    async def test_does_not_retry_on_403(self) -> None:
        strategy = RetryStrategy(max_retries=3, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_403 = _make_response(403)
        transport._inner.handle_async_request = AsyncMock(return_value=response_403)

        response = await self._run_request(transport)
        assert response.status_code == 403
        transport._inner.handle_async_request.assert_awaited_once()

    # ── Connection errors ──────────────────────────────────────────────

    async def test_retries_on_connect_error(self) -> None:
        strategy = RetryStrategy(max_retries=2, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_200 = _make_response(200)
        transport._inner.handle_async_request = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                response_200,
            ]
        )

        response = await self._run_request(transport)
        assert response.status_code == 200
        assert transport._inner.handle_async_request.await_count == 2

    async def test_retries_on_timeout_error(self) -> None:
        strategy = RetryStrategy(max_retries=2, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        response_200 = _make_response(200)
        transport._inner.handle_async_request = AsyncMock(
            side_effect=[
                httpx.TimeoutException("Timed out"),
                response_200,
            ]
        )

        response = await self._run_request(transport)
        assert response.status_code == 200

    async def test_exhausts_retries_on_connection_error(self) -> None:
        strategy = RetryStrategy(max_retries=2, jitter=False)
        transport = RetryTransport(retry_strategy=strategy)
        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)

        transport._inner.handle_async_request = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(httpx.ConnectError):
            await self._run_request(transport)

        assert (
            transport._inner.handle_async_request.await_count == 3
        )  # 1 initial + 2 retries

    # ── Retry-After header parsing ─────────────────────────────────────

    async def test_retry_after_parses_int(self) -> None:
        delay = RetryTransport._parse_retry_after(
            _make_response(429, headers={"Retry-After": "5"})
        )
        assert delay == 5.0

    async def test_retry_after_parses_float(self) -> None:
        delay = RetryTransport._parse_retry_after(
            _make_response(429, headers={"Retry-After": "2.5"})
        )
        assert delay == 2.5

    async def test_retry_after_none_when_missing(self) -> None:
        delay = RetryTransport._parse_retry_after(_make_response(429))
        assert delay is None

    async def test_retry_after_none_when_invalid(self) -> None:
        delay = RetryTransport._parse_retry_after(
            _make_response(429, headers={"Retry-After": "not-a-number"})
        )
        assert delay is None


# ===========================================================================
# Circuit Breaker tests
# ===========================================================================


class TestProviderCircuitBreaker:
    """Tests for ProviderCircuitBreaker."""

    def setup_method(self) -> None:
        """Clean circuit breaker state between tests."""
        ProviderCircuitBreaker._state.clear()
        ProviderCircuitBreaker._locks.clear()

    def test_initial_state_is_closed(self) -> None:
        cb = ProviderCircuitBreaker("TestProvider")
        assert cb.state == ProviderCircuitBreaker.CLOSED
        assert cb.consecutive_failures == 0

    @pytest.mark.anyio
    async def test_opens_after_failure_threshold(self) -> None:
        cb = ProviderCircuitBreaker(
            "TestProvider", failure_threshold=3, recovery_timeout=9999
        )
        for _ in range(3):
            await cb.on_failure()

        assert cb.state == ProviderCircuitBreaker.OPEN
        assert cb.consecutive_failures == 3

    @pytest.mark.anyio
    async def test_raises_circuit_breaker_open_error(self) -> None:
        cb = ProviderCircuitBreaker(
            "TestProvider", failure_threshold=2, recovery_timeout=9999
        )
        await cb.on_failure()
        await cb.on_failure()
        assert cb.state == ProviderCircuitBreaker.OPEN

        with pytest.raises(CircuitBreakerOpenError) as excinfo:
            await cb.check()
        assert "Circuit breaker is OPEN" in str(excinfo.value)

    @pytest.mark.anyio
    async def test_closes_after_success(self) -> None:
        cb = ProviderCircuitBreaker(
            "TestProvider", failure_threshold=2, recovery_timeout=9999
        )
        await cb.on_failure()
        await cb.on_failure()
        assert cb.state == ProviderCircuitBreaker.OPEN

        cb.reset()
        assert cb.state == ProviderCircuitBreaker.CLOSED
        assert cb.consecutive_failures == 0

    @pytest.mark.anyio
    async def test_half_open_after_recovery_timeout(self) -> None:
        cb = ProviderCircuitBreaker(
            "TestProvider", failure_threshold=2, recovery_timeout=0.01
        )
        await cb.on_failure()
        await cb.on_failure()
        assert cb.state == cb.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.02)

        # check() should transition to half-open
        await cb.check()
        assert cb.state == cb.HALF_OPEN

    @pytest.mark.anyio
    async def test_half_open_allows_one_request_and_closes_on_success(self) -> None:
        cb = ProviderCircuitBreaker(
            "TestProvider", failure_threshold=2, recovery_timeout=0.01
        )
        await cb.on_failure()
        await cb.on_failure()
        await asyncio.sleep(0.02)

        await cb.check()
        assert cb.state == cb.HALF_OPEN

        await cb.on_success()
        assert cb.state == cb.CLOSED
        assert cb.consecutive_failures == 0

    @pytest.mark.anyio
    async def test_half_open_reopens_on_failure(self) -> None:
        cb = ProviderCircuitBreaker(
            "TestProvider", failure_threshold=2, recovery_timeout=0.01
        )
        await cb.on_failure()
        await cb.on_failure()
        await asyncio.sleep(0.02)

        await cb.check()  # transitions to HALF_OPEN
        await cb.on_failure()

        # New failure increments counter: 2 + 1 = 3 (still >= 2) → OPEN
        assert cb.state == cb.OPEN
        assert cb.consecutive_failures == 3

    @pytest.mark.anyio
    async def test_reset_clears_state(self) -> None:
        cb = ProviderCircuitBreaker("TestProvider", failure_threshold=3)
        await cb.on_failure()
        await cb.on_failure()
        cb.reset()
        assert cb.state == cb.CLOSED
        assert cb.consecutive_failures == 0

    def test_concurrent_providers_have_separate_state(self) -> None:
        cb_a = ProviderCircuitBreaker("ProviderA", failure_threshold=2)
        cb_b = ProviderCircuitBreaker("ProviderB", failure_threshold=3)

        asyncio.run(cb_a.on_failure())
        asyncio.run(cb_a.on_failure())

        assert cb_a.state == cb_a.OPEN
        assert cb_b.state == cb_b.CLOSED


# ===========================================================================
# Circuit Breaker integration with RetryTransport
# ===========================================================================


class TestRetryTransportWithCircuitBreaker(_TransportMixin):
    """Tests that the transport properly integrates with the circuit breaker."""

    pytestmark = pytest.mark.anyio

    def setup_method(self) -> None:
        ProviderCircuitBreaker._state.clear()
        ProviderCircuitBreaker._locks.clear()

    async def test_circuit_breaker_blocks_requests_when_open(self) -> None:
        cb = ProviderCircuitBreaker(
            "TestProvider", failure_threshold=2, recovery_timeout=9999
        )
        strategy = RetryStrategy(max_retries=1, jitter=False)
        transport = RetryTransport(retry_strategy=strategy, circuit_breaker=cb)

        # Set circuit to open
        await cb.on_failure()
        await cb.on_failure()
        assert cb.state == cb.OPEN

        request = httpx.Request("GET", "https://example.com/api")
        with pytest.raises(CircuitBreakerOpenError):
            await transport.handle_async_request(request)

    async def test_circuit_breaker_records_failures_on_429(self) -> None:
        cb = ProviderCircuitBreaker(
            "TestProvider", failure_threshold=3, recovery_timeout=9999
        )
        strategy = RetryStrategy(max_retries=1, jitter=False)
        transport = RetryTransport(retry_strategy=strategy, circuit_breaker=cb)

        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)
        response_429 = _make_response(429)
        transport._inner.handle_async_request = AsyncMock(
            side_effect=[response_429, response_429]
        )

        with pytest.raises(ProviderRateLimitedError):
            await self._run_request(transport)

        # Yield to let fire-and-forget circuit breaker tasks complete
        await asyncio.sleep(0)

        # Circuit breaker records 1 failure — the final exhaustion after all retries
        assert cb.consecutive_failures == 1

    async def test_circuit_breaker_records_success(self) -> None:
        cb = ProviderCircuitBreaker(
            "TestProvider", failure_threshold=3, recovery_timeout=9999
        )
        strategy = RetryStrategy(max_retries=1, jitter=False)
        transport = RetryTransport(retry_strategy=strategy, circuit_breaker=cb)

        transport._inner = MagicMock(spec=httpx.AsyncHTTPTransport)
        response_200 = _make_response(200)
        transport._inner.handle_async_request = AsyncMock(return_value=response_200)

        await self._run_request(transport)

        # Give the fire-and-forget coroutine a moment to run
        await asyncio.sleep(0.01)
        assert cb.state == cb.CLOSED


# ===========================================================================
# BaseProvider circuit breaker integration tests
# ===========================================================================


class TestBaseProviderCircuitBreakerIntegration:
    """Tests that BaseProvider properly exposes circuit breaker state."""

    def setup_method(self) -> None:
        # Clean between tests — reset state without removing class-level entries
        ConcreteProvider.reset_circuit_breaker()

    def test_circuit_breaker_state_returns_none_before_init(self) -> None:
        cb = ConcreteProvider.circuit_breaker_state()
        # May be None before any instance is created
        assert cb is None or cb["state"] == "CLOSED"

    def test_circuit_breaker_state_after_init(self) -> None:
        ConcreteProvider()
        state = ConcreteProvider.circuit_breaker_state()
        assert state is not None
        assert state["state"] == "CLOSED"

    def test_reset_circuit_breaker(self) -> None:
        provider = ConcreteProvider()
        cb = ConcreteProvider._circuit_breakers[type(provider).__name__]
        asyncio.run(cb.on_failure())
        asyncio.run(cb.on_failure())
        asyncio.run(cb.on_failure())
        asyncio.run(cb.on_failure())
        asyncio.run(cb.on_failure())
        assert cb.state == cb.OPEN

        ConcreteProvider.reset_circuit_breaker()
        assert cb.state == cb.CLOSED


# ===========================================================================
# BaseProvider tests
# ===========================================================================


class TestBaseProviderInit:
    """Tests for BaseProvider.__init__."""

    def test_init_sets_user_agent(self) -> None:
        provider = ConcreteProvider()
        assert provider.user_agent is not None
        assert isinstance(provider.user_agent, str)

    def test_init_sets_async_client(self) -> None:
        provider = ConcreteProvider()
        assert provider.async_client is not None

    def test_async_client_has_retry_transport(self) -> None:
        """The async_client should be using our RetryTransport."""
        provider = ConcreteProvider()
        assert hasattr(provider.async_client, "_transport")
        transport = provider.async_client._transport
        assert isinstance(transport, RetryTransport)

    def test_headers_property(self) -> None:
        provider = ConcreteProvider()
        headers = provider.headers
        assert "User-Agent" in headers
        assert headers["User-Agent"] == provider.user_agent

    def test_user_agent_fallback(self) -> None:
        """When fake_useragent fails, use the fallback UA string."""
        with patch(
            "fake_useragent.UserAgent",
            side_effect=Exception("No fake useragent"),
        ):
            provider = ConcreteProvider()
        assert "Mozilla" in provider.user_agent


class TestBaseProviderSearchStatements:
    """Tests for the search table SQL statements.

    These tests the SQL generation logic without executing against a real DB.
    """

    def test_search_rec_area_statement_is_insert(self) -> None:
        provider = ConcreteProvider()
        stmt = provider.search_rec_area_statement
        from sqlalchemy import Insert

        assert isinstance(stmt, Insert)

    def test_search_campground_statement_is_insert(self) -> None:
        provider = ConcreteProvider()
        stmt = provider.search_campground_statement
        from sqlalchemy import Insert

        assert isinstance(stmt, Insert)


class TestBaseProviderPopulateSearchTable:
    """Tests for populate_search_table.

    Requires an async session mock.
    """

    @pytest.mark.anyio
    async def test_populate_search_table(self) -> None:
        provider = ConcreteProvider()
        mock_session = MagicMock()
        # session.begin() returns an async context manager
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=None)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session.begin.return_value = mock_ctx
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        await provider.populate_search_table(mock_session)

        # Should call execute at least twice (delete + rec area + campground)
        assert mock_session.execute.call_count >= 3


# ===========================================================================
# DatabasePopulator
# ===========================================================================


class TestDatabasePopulator:
    """Tests for DatabasePopulator ABC."""

    def test_abstract(self) -> None:
        """Cannot instantiate DatabasePopulator directly."""
        with pytest.raises(TypeError):
            DatabasePopulator()  # type: ignore[abstract]

    def test_concrete_subclass(self) -> None:
        class Populator(DatabasePopulator):
            async def to_database(self, session):
                pass

        p = Populator()
        assert isinstance(p, DatabasePopulator)
