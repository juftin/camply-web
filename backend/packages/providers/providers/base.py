"""
Base Provider Configuration
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, ClassVar

import httpx
import structlog
from pydantic import BaseModel, field_validator
from sqlalchemy import Insert, delete, insert, literal, null, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from sqlalchemy.sql.functions import concat

from db.models import Campground, Provider, RecreationArea, Search
from providers.dto import CampsiteDTO
from providers.errors import CircuitBreakerOpenError, ProviderRateLimitedError

logger = structlog.getLogger()

# ── HTTP status code constants ─────────────────────────────────────────
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_SERVER_ERROR_MIN = 500
_HTTP_SERVER_ERROR_MAX = 599

# ── Types of connection-level errors that are retryable ────────────────
_RETRYABLE_CONNECTION_ERRORS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
)


# ===========================================================================
# Retry Strategy
# ===========================================================================


@dataclass
class RetryStrategy:
    """
    Configuration for provider request retries with exponential backoff.

    Parameters
    ----------
    max_retries : int
        Maximum number of retry attempts (default 3).
    base_delay : float
        Initial delay in seconds for exponential backoff (default 1.0).
    max_delay : float
        Maximum delay in seconds for backoff (default 60.0).
    backoff_factor : float
        Multiplier for exponential backoff per attempt (default 2.0).
    jitter : bool
        Whether to add random jitter to delays (default True).
    retry_on_429 : bool
        Whether to retry on HTTP 429 Too Many Requests (default True).
    retry_on_5xx : bool
        Whether to retry on HTTP 5xx Server Errors (default True).
    retry_on_connection_errors : bool
        Whether to retry on connection/timeout errors (default True).
    _5xx_base_delay : float
        Base delay in seconds for 5xx retries (default 0.5).
    _5xx_max_delay : float
        Maximum delay in seconds for 5xx retries (default 30.0).
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


# ===========================================================================
# Circuit Breaker
# ===========================================================================


class ProviderCircuitBreaker:
    """
    Per-provider circuit breaker that tracks consecutive failures.

    After ``failure_threshold`` consecutive failures the circuit opens.
    After ``recovery_timeout`` seconds the circuit half-opens to allow one
    test request.  Success closes the circuit; a further failure opens it
    again.

    State is stored in a class-level dict keyed by provider name so that
    multiple instances of the same provider share one breaker.

    Parameters
    ----------
    provider_name : str
        Unique name for this circuit breaker (typically ``type(self).__name__``).
    failure_threshold : int
        Number of consecutive failures before the circuit opens (default 5).
    recovery_timeout : float
        Seconds to wait before transitioning from OPEN to HALF_OPEN (default 300).
    """

    # ── class-level state ──────────────────────────────────────────────
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

        # Bootstrap class-level state on first instantiation
        if provider_name not in self._state:
            self._state[provider_name] = {
                "state": self.CLOSED,
                "consecutive_failures": 0,
                "last_failure_time": 0.0,
            }
        if provider_name not in self._locks:
            self._locks[provider_name] = asyncio.Lock()

    # ── public API ─────────────────────────────────────────────────────

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

        Raises
        ------
        CircuitBreakerOpenError
            If the circuit is OPEN and the recovery timeout has not elapsed.
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
        Record a successful request.  Resets the circuit to CLOSED.
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
        Record a failed request.

        Increments the consecutive-failure counter.  If the threshold is
        reached the circuit transitions to OPEN.
        """
        async with self._locks[self._provider_name]:
            st = self._state[self._provider_name]
            st["consecutive_failures"] += 1
            st["last_failure_time"] = time.monotonic()
            if st["consecutive_failures"] >= self._failure_threshold:
                st["state"] = self.OPEN
                logger.warning(
                    "Circuit opened after %d consecutive failures",
                    st["consecutive_failures"],
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


# ===========================================================================
# Retry Transport
# ===========================================================================


class RetryTransport(httpx.AsyncHTTPTransport):
    """
    Custom ``httpx.AsyncHTTPTransport`` that adds retry logic with
    exponential backoff, optional jitter, and an optional per-provider
    circuit breaker.

    The transport respects the ``Retry-After`` header on HTTP 429 responses
    and falls back to exponential backoff when the header is absent.
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
        Dispatch *request* through this transport, with retry and optional
        circuit-breaker logic.
        """
        if self._circuit_breaker:
            await self._circuit_breaker.check()

        # Read body up front so we can reconstruct for retries
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

            # 5xx that exhausted retries
            if self._is_5xx(result):
                self._record_failure()
                last_response = result
                break

            self._record_success()
            return result

        if last_exception is not None:
            raise last_exception  # type: ignore[misc]

        if last_response is not None:
            return last_response

        raise httpx.RemoteProtocolError("Unexpected retry state")

    @staticmethod
    def _request_for_attempt(
        original: httpx.Request,
        body: bytes,
        attempt: int,
    ) -> httpx.Request:
        """Return the request to use for *attempt* (reconstructs for retries)."""
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
        """
        Execute one attempt and return the result.

        Returns
        -------
        ``None``
            Retry needed (connection or server error within limits).
        ``Exception``
            Non-recoverable error; caller should re-raise.
        ``httpx.Response``
            Final response (success or exhausted retries).
        """
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

    # ── response classification helpers ────────────────────────────────

    @staticmethod
    def _is_429(response: httpx.Response) -> bool:
        """Return ``True`` when the response is an HTTP 429."""
        return response.status_code == _HTTP_TOO_MANY_REQUESTS

    @staticmethod
    def _is_5xx(response: httpx.Response) -> bool:
        """Return ``True`` when the response is an HTTP 5xx."""
        return _HTTP_SERVER_ERROR_MIN <= response.status_code <= _HTTP_SERVER_ERROR_MAX

    def _connection_retryable(self, attempt: int) -> bool:
        """Return ``True`` if this connection error attempt should be retried."""
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
        """
        Sleep with backoff if *attempt* is below the max- retries threshold.

        Returns ``True`` when the caller should continue (retry), ``False``
        when retries have been exhausted.
        """
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
            "Retrying after %s",
            label,
            attempt=attempt + 1,
            delay=round(delay, 2),
        )
        await asyncio.sleep(delay)
        return True

    # ── delay computation ──────────────────────────────────────────────

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
        """Parse the ``Retry-After`` header from a response."""
        raw = response.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    # ── circuit-breaker helpers ─────────────────────────────────────────

    def _record_success(self) -> None:
        """Notify the circuit breaker (if present) of a successful request."""
        if self._circuit_breaker:
            task = asyncio.create_task(self._circuit_breaker.on_success())
            self._cb_tasks.add(task)
            task.add_done_callback(self._cb_tasks.discard)

    def _record_failure(self) -> None:
        """Notify the circuit breaker (if present) of a failed request."""
        if self._circuit_breaker:
            task = asyncio.create_task(self._circuit_breaker.on_failure())
            self._cb_tasks.add(task)
            task.add_done_callback(self._cb_tasks.discard)


# ===========================================================================
# Base Provider
# ===========================================================================


class BaseProvider(ABC):
    """
    Base Class for Providers
    """

    # ── class-level circuit breaker registry ───────────────────────────
    _circuit_breakers: ClassVar[dict[str, ProviderCircuitBreaker]] = {}

    def __init__(self) -> None:
        """
        Initialize the base provider.
        """
        try:
            from fake_useragent import UserAgent

            self.user_agent = UserAgent(browsers=["chrome"]).random
        except Exception:
            self.user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

        # Build retry transport with circuit breaker
        provider_name = type(self).__name__
        self._retry_strategy = self.retry_strategy
        cb = self._get_or_create_circuit_breaker(provider_name)
        transport = RetryTransport(
            retry_strategy=self._retry_strategy,
            circuit_breaker=cb,
        )
        self.async_client = httpx.AsyncClient(
            headers=self.headers,
            transport=transport,
        )

    @property
    def retry_strategy(self) -> RetryStrategy:
        """
        Return the retry strategy for this provider.

        Subclasses may override this property to provide custom tuning per
        provider (e.g. longer timeouts for a slow API).
        """
        return RetryStrategy()

    @classmethod
    def circuit_breaker_state(cls) -> dict[str, Any] | None:
        """
        Return the current circuit-breaker state for this provider class.

        Returns ``None`` if the circuit breaker has not been initialised yet
        (no instance of the provider has been created).
        """
        cb = cls._circuit_breakers.get(cls.__name__)
        if cb is None:
            return None
        return {
            "state": cb.state,
            "consecutive_failures": cb.consecutive_failures,
        }

    @classmethod
    def reset_circuit_breaker(cls) -> None:
        """
        Force-reset the circuit breaker for this provider class (testing).
        """
        cb = cls._circuit_breakers.get(cls.__name__)
        if cb is not None:
            cb.reset()

    @classmethod
    def _get_or_create_circuit_breaker(
        cls, provider_name: str
    ) -> ProviderCircuitBreaker:
        """Return an existing circuit breaker or create a new one."""
        if provider_name not in cls._circuit_breakers:
            cls._circuit_breakers[provider_name] = ProviderCircuitBreaker(
                provider_name=provider_name,
            )
        return cls._circuit_breakers[provider_name]

    @abstractmethod
    async def find_availabilities(
        self,
        park_id: str,
        start_date: date,
        end_date: date,
    ) -> list[CampsiteDTO]:
        """
        Find campsite availabilities for the target park and dates.
        """

    @abstractmethod
    async def sync_metadata(self) -> None:
        """
        Background task to update the 'Search' and 'Campground'
        tables with the latest info from the provider.
        """

    @property
    def headers(self) -> dict[str, str]:
        """
        Headers for the provider requests.
        """
        return {"User-Agent": self.user_agent}

    @abstractmethod
    async def populate_database(self) -> None:
        """
        Populate the database with data from the provider.
        """

    @property
    @abstractmethod
    def provider(self) -> Provider:
        """
        Return the provider instance.
        """

    @property
    def search_rec_area_statement(self) -> Insert:
        """
        SQL statement to search recreation areas.
        """
        rec_areas = insert(Search).from_select(
            names=[
                Search.id,
                Search.entity_type,
                Search.provider_id,
                Search.provider_name,
                Search.recreation_area_id,
                Search.recreation_area_name,
                Search.campground_id,
                Search.campground_name,
            ],
            select=select(
                concat(
                    "RecreationArea",
                    "/",
                    self.provider.id,
                    "/",
                    RecreationArea.id,
                    "/",
                ).label("id"),
                literal("RecreationArea").label("entity_type"),
                literal(self.provider.id).label("provider_id"),
                literal(self.provider.name).label("provider_name"),
                RecreationArea.id.label("recreation_area_id"),
                func.lower(RecreationArea.name).label("recreation_area_name"),
                null().label("campground_id"),
                null().label("campground_name"),
            ).where(RecreationArea.provider_id == self.provider.id),
        )
        return rec_areas

    @property
    def search_campground_statement(self) -> Insert:
        """
        SQL statement to search campgrounds.
        """
        campgrounds = insert(Search).from_select(
            names=[
                Search.id,
                Search.entity_type,
                Search.provider_id,
                Search.provider_name,
                Search.recreation_area_id,
                Search.recreation_area_name,
                Search.campground_id,
                Search.campground_name,
            ],
            select=select(
                concat(
                    "Campground",
                    "/",
                    self.provider.id,
                    "/",
                    RecreationArea.id,
                    "/",
                    Campground.id,
                ).label("id"),
                literal("Campground").label("entity_type"),
                literal(self.provider.id).label("provider_id"),
                literal(self.provider.name).label("provider_name"),
                RecreationArea.id.label("recreation_area_id"),
                func.lower(RecreationArea.name).label("recreation_area_name"),
                Campground.id.label("campground_id"),
                func.lower(Campground.name).label("campground_name"),
            )
            .select_from(
                Campground.__table__.outerjoin(
                    RecreationArea,
                    Campground.recreation_area_id == RecreationArea.id,
                )
            )
            .where(Campground.provider_id == self.provider.id),
        )
        return campgrounds

    async def populate_search_table(self, session: AsyncSession) -> None:
        """
        Populate the search table with campground and recreation area data.
        """
        logger.info(
            "Populating search table",
            provider=self.provider.name,
        )
        async with session.begin():
            await session.execute(
                delete(Search).where(Search.provider_name == self.provider.name)
            )
            await session.execute(self.search_rec_area_statement)
            await session.execute(self.search_campground_statement)
            await session.commit()

    @classmethod
    @abstractmethod
    def get_rec_area_url(cls, rec_area_id: str) -> str:
        """
        Get the URL for a recreation area.
        """

    @classmethod
    @abstractmethod
    def get_campground_url(cls, campground_id: str) -> str:
        """
        Get the URL for a campground.
        """


class NullHandler(BaseModel):
    """
    Empty String to Null Handler
    """

    @field_validator("*", mode="before")
    @classmethod
    def convert_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class DatabasePopulator(ABC, BaseModel):
    """
    Class that supports populating the database with data.
    """

    @abstractmethod
    async def to_database(self, session: AsyncSession) -> None:
        """
        Populate the database with the data.
        """
