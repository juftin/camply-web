"""
HTTP transport utilities including retries with exponential backoff and circuit breaking.
"""

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, ClassVar

import httpx
import structlog

from camply_core.errors import CircuitBreakerOpenError, ProviderRateLimitedError

logger = structlog.getLogger()

_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_SERVER_ERROR_MIN = 500
_HTTP_SERVER_ERROR_MAX = 599

_RETRYABLE_CONNECTION_ERRORS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
)


@dataclass
class RetryStrategy:
    """
    Configuration for request retries with exponential backoff and jitter.
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retry_on_429: bool = True
    retry_on_5xx: bool = True
    retry_on_connection_errors: bool = True
    _5xx_base_delay: float = 0.5
    _5xx_max_delay: float = 30.0


class ProviderCircuitBreaker:
    """
    Tracks consecutive failures and opens the circuit after a threshold.
    """

    _state: ClassVar[dict[str, dict[str, Any]]] = {}
    _locks: ClassVar[dict[str, asyncio.Lock]] = {}

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        provider_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 300.0,
    ) -> None:
        self._provider_name = provider_name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

        if provider_name not in self._state:
            self._state[provider_name] = {
                "state": self.CLOSED,
                "consecutive_failures": 0,
                "last_failure_time": 0.0,
            }
        if provider_name not in self._locks:
            self._locks[provider_name] = asyncio.Lock()

    @property
    def state(self) -> str:
        """Return the current circuit state (CLOSED / OPEN / HALF_OPEN)."""
        return self._state[self._provider_name]["state"]

    @property
    def consecutive_failures(self) -> int:
        """Return the number of consecutive failures recorded."""
        return self._state[self._provider_name]["consecutive_failures"]

    async def check(self) -> None:
        """
        Check whether the circuit is open.
        """
        async with self._locks[self._provider_name]:
            st = self._state[self._provider_name]
            if st["state"] == self.OPEN:
                elapsed = time.monotonic() - st["last_failure_time"]
                if elapsed >= self._recovery_timeout:
                    st["state"] = self.HALF_OPEN
                    logger.info(
                        "Circuit half-opened after recovery timeout",
                        provider=self._provider_name,
                    )
                else:
                    raise CircuitBreakerOpenError(self._provider_name)

    async def on_success(self) -> None:
        """
        Record a successful request. Resets the circuit to CLOSED.
        """
        async with self._locks[self._provider_name]:
            st = self._state[self._provider_name]
            if st["state"] != self.CLOSED:
                logger.info(
                    "Circuit closed after successful request",
                    provider=self._provider_name,
                )
            st["state"] = self.CLOSED
            st["consecutive_failures"] = 0

    async def on_failure(self) -> None:
        """
        Record a failed request. Transitions to OPEN if threshold is exceeded.
        """
        async with self._locks[self._provider_name]:
            st = self._state[self._provider_name]
            st["consecutive_failures"] += 1
            st["last_failure_time"] = time.monotonic()
            if st["consecutive_failures"] >= self._failure_threshold:
                st["state"] = self.OPEN
                logger.warning(
                    "Circuit opened after consecutive failures",
                    failures=st["consecutive_failures"],
                    provider=self._provider_name,
                )

    def reset(self) -> None:
        """
        Force-reset the circuit breaker to CLOSED (useful in testing).
        """
        st = self._state[self._provider_name]
        st["state"] = self.CLOSED
        st["consecutive_failures"] = 0
        st["last_failure_time"] = 0.0


class RetryTransport(httpx.AsyncHTTPTransport):
    """
    Custom AsyncHTTPTransport adding retry with exponential backoff and circuit breaking.
    """

    def __init__(
        self,
        retry_strategy: RetryStrategy | None = None,
        circuit_breaker: ProviderCircuitBreaker | None = None,
    ) -> None:
        self._retry_strategy = retry_strategy or RetryStrategy()
        self._circuit_breaker = circuit_breaker
        self._inner = httpx.AsyncHTTPTransport()
        self._cb_tasks: set[asyncio.Task[None]] = set()
        super().__init__()

    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        """
        Dispatch request with retry and optional circuit breaker.
        """
        if self._circuit_breaker:
            await self._circuit_breaker.check()

        await request.aread()
        request_body = request.content

        last_exception: Exception | None = None
        last_response: httpx.Response | None = None

        for attempt in range(self._retry_strategy.max_retries + 1):
            try:
                req = self._request_for_attempt(request, request_body, attempt)
                result = await self._execute_attempt(req, attempt)
            except ProviderRateLimitedError:
                self._record_failure()
                raise

            if result is None:
                continue

            if isinstance(result, Exception):
                self._record_failure()
                last_exception = result
                break

            if self._is_5xx(result):
                self._record_failure()
                last_response = result
                break

            self._record_success()
            return result

        if last_exception is not None:
            raise last_exception

        if last_response is not None:
            return last_response

        raise httpx.RemoteProtocolError("Unexpected retry state")

    @staticmethod
    def _request_for_attempt(
        original: httpx.Request,
        body: bytes,
        attempt: int,
    ) -> httpx.Request:
        """Reconstruct request for retries."""
        if attempt == 0:
            return original
        return httpx.Request(
            method=original.method,
            url=str(original.url),
            headers=original.headers,
            content=body,
        )

    async def _execute_attempt(
        self,
        request: httpx.Request,
        attempt: int,
    ) -> httpx.Response | Exception | None:
        """Execute one attempt."""
        try:
            response = await self._inner.handle_async_request(request)
        except _RETRYABLE_CONNECTION_ERRORS as exc:
            if self._connection_retryable(attempt):
                delay = self._compute_delay(
                    attempt,
                    base=self._retry_strategy._5xx_base_delay,
                    max_delay=self._retry_strategy._5xx_max_delay,
                )
                logger.debug(
                    "Retrying after connection error",
                    attempt=attempt + 1,
                    error=type(exc).__name__,
                )
                await asyncio.sleep(delay)
                return None
            return exc

        if self._is_429(response) and self._retry_strategy.retry_on_429:
            if await self._handle_retryable_response(response, attempt, "429"):
                return None
            raise ProviderRateLimitedError(
                f"Rate limited after {self._retry_strategy.max_retries} retries"
            )

        if self._is_5xx(response) and self._retry_strategy.retry_on_5xx:
            if await self._handle_retryable_response(
                response, attempt, str(response.status_code)
            ):
                return None
            return response

        return response

    @staticmethod
    def _is_429(response: httpx.Response) -> bool:
        """Return True when response is HTTP 429."""
        return response.status_code == _HTTP_TOO_MANY_REQUESTS

    @staticmethod
    def _is_5xx(response: httpx.Response) -> bool:
        """Return True when response is HTTP 5xx."""
        return _HTTP_SERVER_ERROR_MIN <= response.status_code <= _HTTP_SERVER_ERROR_MAX

    def _connection_retryable(self, attempt: int) -> bool:
        """Return True if connection error should be retried."""
        return (
            self._retry_strategy.retry_on_connection_errors
            and attempt < self._retry_strategy.max_retries
        )

    async def _handle_retryable_response(
        self,
        response: httpx.Response,
        attempt: int,
        label: str,
    ) -> bool:
        """Handle retryable response with backoff."""
        if attempt >= self._retry_strategy.max_retries:
            return False

        delay: float | None = None
        if self._is_429(response):
            delay = self._parse_retry_after(response)
        if delay is None:
            delay = self._compute_delay(
                attempt,
                base=self._retry_strategy._5xx_base_delay,
                max_delay=self._retry_strategy._5xx_max_delay,
            )

        logger.debug(
            "Retrying after status",
            status=label,
            attempt=attempt + 1,
            delay=round(delay, 2),
        )
        await asyncio.sleep(delay)
        return True

    def _compute_delay(
        self,
        attempt: int,
        base: float = 0.5,
        max_delay: float = 30.0,
    ) -> float:
        """Exponential backoff with optional jitter."""
        delay = min(base * (self._retry_strategy.backoff_factor**attempt), max_delay)
        if self._retry_strategy.jitter:
            delay *= 0.5 + random.random() * 0.5
        return delay

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float | None:
        """Parse the Retry-After header."""
        raw = response.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    def _record_success(self) -> None:
        """Notify circuit breaker of success."""
        if self._circuit_breaker:
            task = asyncio.create_task(self._circuit_breaker.on_success())
            self._cb_tasks.add(task)
            task.add_done_callback(self._cb_tasks.discard)

    def _record_failure(self) -> None:
        """Notify circuit breaker of failure."""
        if self._circuit_breaker:
            task = asyncio.create_task(self._circuit_breaker.on_failure())
            self._cb_tasks.add(task)
            task.add_done_callback(self._cb_tasks.discard)
