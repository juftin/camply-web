"""
Tests for transport retries and circuit breaker in camply_core.
"""

import pytest

from camply_core.errors import CircuitBreakerOpenError
from camply_core.transport import ProviderCircuitBreaker, RetryStrategy


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_retry_strategy_defaults() -> None:
    """Test RetryStrategy default configuration values."""
    strategy = RetryStrategy()
    assert strategy.max_retries == 3
    assert strategy.base_delay == 1.0
    assert strategy.max_delay == 60.0
    assert strategy.retry_on_429 is True
    assert strategy.retry_on_5xx is True


@pytest.mark.anyio
async def test_circuit_breaker_transitions() -> None:
    """Test circuit breaker state transitions (CLOSED -> OPEN -> HALF_OPEN)."""
    cb = ProviderCircuitBreaker(
        provider_name="test_provider",
        failure_threshold=2,
        recovery_timeout=0.1,
    )
    cb.reset()

    assert cb.state == ProviderCircuitBreaker.CLOSED
    await cb.check()

    # First failure
    await cb.on_failure()
    assert cb.consecutive_failures == 1
    assert cb.state == ProviderCircuitBreaker.CLOSED

    # Second failure triggers OPEN
    await cb.on_failure()
    assert cb.consecutive_failures == 2
    assert cb.state == ProviderCircuitBreaker.OPEN

    # Check should raise CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        await cb.check()

    # Success after reset closes circuit
    cb.reset()
    assert cb.state == ProviderCircuitBreaker.CLOSED
    assert cb.consecutive_failures == 0
