"""
Base Provider Configuration
"""

import asyncio
import inspect
import random
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date
from typing import Any, ClassVar

import httpx2
import structlog
from pydantic import BaseModel, field_validator
from sqlalchemy import (
    Insert,
    and_,
    case,
    delete,
    func,
    insert,
    literal,
    null,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.models import Campground, Provider, RecreationArea, Search
from camply.providers.dto import (
    CampgroundSearchResult,
    CampsiteDTO,
    ProviderSearchQuery,
    ProviderSearchResult,
    RecreationAreaSearchResult,
    SearchEntityType,
)
from camply.providers.errors import CircuitBreakerOpenError, ProviderRateLimitedError

logger = structlog.getLogger()


@dataclass(frozen=True)
class CampgroundCapabilities:
    """Normalized discovery capability columns for a persisted campground."""

    campsite_types: list[str] | None = None
    has_electric: bool = False
    has_water: bool = False
    has_sewer: bool = False
    pets_allowed: bool = False
    ada_accessible: bool = False
    max_rv_length: int | None = None

    def as_columns(self) -> dict[str, Any]:
        """Return keyword arguments matching ``Campground`` capability columns."""
        return {
            "campsite_types": self.campsite_types,
            "has_electric": self.has_electric,
            "has_water": self.has_water,
            "has_sewer": self.has_sewer,
            "pets_allowed": self.pets_allowed,
            "ada_accessible": self.ada_accessible,
            "max_rv_length": self.max_rv_length,
        }


@dataclass(frozen=True)
class ProviderFilterCapabilities:
    """Monitor filter controls supported by a provider's availability feed."""

    preferred_types: bool = True
    """Whether the provider reports campsite types (Tent, RV, Cabin, Other)."""
    require_electric: bool = True
    """Whether the provider reports electric hookup availability per site."""
    require_accessible: bool = True
    """Whether the provider reports ADA accessibility per site."""
    min_rv_length: bool = True
    """Whether the provider reports maximum vehicle/RV length per site."""


# ── HTTP status code constants ─────────────────────────────────────────
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_SERVER_ERROR_MIN = 500
_HTTP_SERVER_ERROR_MAX = 599

# ── Types of connection-level errors that are retryable ────────────────
_RETRYABLE_CONNECTION_ERRORS = (
    httpx2.ConnectError,
    httpx2.TimeoutException,
    httpx2.RemoteProtocolError,
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
        self._ensure_state()

    def _ensure_state(self) -> None:
        """Ensure class-level state and lock exist for this provider."""
        if self._provider_name not in self._state:
            self._state[self._provider_name] = {
                "state": self.CLOSED,
                "consecutive_failures": 0,
                "last_failure_time": 0.0,
            }
        if self._provider_name not in self._locks:
            self._locks[self._provider_name] = asyncio.Lock()

    # ── public API ─────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        """Return the current circuit state (CLOSED / OPEN / HALF_OPEN)."""
        self._ensure_state()
        return self._state[self._provider_name]["state"]

    @property
    def consecutive_failures(self) -> int:
        """Return the number of consecutive failures recorded."""
        self._ensure_state()
        return self._state[self._provider_name]["consecutive_failures"]

    async def check(self) -> None:
        """
        Check whether the circuit is open.

        Raises
        ------
        CircuitBreakerOpenError
            If the circuit is OPEN and the recovery timeout has not elapsed.
        """
        self._ensure_state()
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
        self._ensure_state()
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
        self._ensure_state()
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
        self._ensure_state()
        st = self._state[self._provider_name]
        st["state"] = self.CLOSED
        st["consecutive_failures"] = 0
        st["last_failure_time"] = 0.0


# ===========================================================================
# Retry Transport
# ===========================================================================


class RetryTransport(httpx2.AsyncHTTPTransport):
    """
    Custom ``httpx2.AsyncHTTPTransport`` that adds retry logic with
    exponential backoff, optional jitter, and an optional per-provider
    circuit breaker.

    The transport respects the ``Retry-After`` header on HTTP 429 responses
    and falls back to exponential backoff when the header is absent.
    """

    def __init__(
        self,
        retry_strategy: RetryStrategy | None = None,
        circuit_breaker: ProviderCircuitBreaker | None = None,
        limits: httpx2.Limits | None = None,
    ) -> None:
        self._retry_strategy = retry_strategy or RetryStrategy()
        self._circuit_breaker = circuit_breaker
        self._inner = httpx2.AsyncHTTPTransport(
            limits=limits
            or httpx2.Limits(
                max_keepalive_connections=50,
                max_connections=200,
                keepalive_expiry=30.0,
            )
        )
        self._cb_tasks: set[asyncio.Task[None]] = set()
        super().__init__()

    async def aclose(self) -> None:
        """Release retry sockets and reap owned circuit-breaker update tasks."""
        try:
            await self._inner.aclose()
        finally:
            try:
                await super().aclose()
            finally:
                if self._cb_tasks:
                    await asyncio.gather(*self._cb_tasks, return_exceptions=True)

    async def handle_async_request(
        self,
        request: httpx2.Request,
    ) -> httpx2.Response:
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
        last_response: httpx2.Response | None = None

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

        raise httpx2.RemoteProtocolError("Unexpected retry state")

    @staticmethod
    def _request_for_attempt(
        original: httpx2.Request,
        body: bytes,
        attempt: int,
    ) -> httpx2.Request:
        """Return the request to use for *attempt* (reconstructs for retries)."""
        if attempt == 0:
            return original
        return httpx2.Request(
            method=original.method,
            url=str(original.url),
            headers=original.headers,
            content=body,
        )

    async def _execute_attempt(
        self,
        request: httpx2.Request,
        attempt: int,
    ) -> httpx2.Response | Exception | None:
        """
        Execute one attempt and return the result.

        Returns
        -------
        ``None``
            Retry needed (connection or server error within limits).
        ``Exception``
            Non-recoverable error; caller should re-raise.
        ``httpx2.Response``
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
    def _is_429(response: httpx2.Response) -> bool:
        """Return ``True`` when the response is an HTTP 429."""
        return response.status_code == _HTTP_TOO_MANY_REQUESTS

    @staticmethod
    def _is_5xx(response: httpx2.Response) -> bool:
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
        response: httpx2.Response,
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
    def _parse_retry_after(response: httpx2.Response) -> float | None:
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
    filter_capabilities: ClassVar[ProviderFilterCapabilities] = (
        ProviderFilterCapabilities()
    )
    """Site-attribute monitor filters supported by this provider."""

    def __init__(self) -> None:
        """
        Initialize the base provider.
        """
        try:
            from fake_useragent import UserAgent

            self.user_agent = UserAgent(browsers=["Chrome"]).random
        except Exception:
            self.user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

        # Build retry transport with circuit breaker and tuned connection pool
        provider_name = type(self).__name__
        self._retry_strategy = self.retry_strategy
        cb = self._get_or_create_circuit_breaker(provider_name)
        limits = httpx2.Limits(
            max_keepalive_connections=50,
            max_connections=200,
            keepalive_expiry=30.0,
        )
        transport = RetryTransport(
            retry_strategy=self._retry_strategy,
            circuit_breaker=cb,
            limits=limits,
        )
        self.async_client = httpx2.AsyncClient(
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

    async def search(
        self,
        query: str = "",
        *,
        state: str | None = None,
        entity_type: SearchEntityType | str | None = None,
        recreation_area_id: str | None = None,
        limit: int = 50,
    ) -> list[ProviderSearchResult]:
        """Discover campgrounds and recreation areas upstream without database access.

        None selects both entity types; strings and SearchEntityType members
        select a single type. Blank text browses the catalog. State codes are
        normalized to uppercase;
        parent IDs are exact strings. Failures propagate rather than appearing
        as an empty result. Results are unique within this provider.
        """
        request = ProviderSearchQuery(
            query=query.strip(),
            entity_type=SearchEntityType(entity_type)
            if entity_type is not None
            else None,
            state=state.strip().upper() if state is not None else None,
            recreation_area_id=recreation_area_id,
            limit=limit,
        )
        results = await self.search_upstream(request)
        unique = {
            (
                result.entity_type,
                result.campground_id
                if result.entity_type == "campground"
                else result.recreation_area_id,
            ): result
            for result in results
        }
        return list(unique.values())[: request.limit]

    @abstractmethod
    async def search_upstream(
        self, query: ProviderSearchQuery
    ) -> list[ProviderSearchResult]:
        """Implement upstream discovery for a provider API family."""

    async def _complete_search(
        self, query: ProviderSearchQuery
    ) -> list[ProviderSearchResult]:
        """Read complete native catalogs; paginated families override this method.

        Catalog-backed providers already return all matching rows from
        ``search_upstream``. Pagination-backed providers must exhaust their
        source rather than interpreting the public search display limit as a
        target limit.
        """
        return await self.search_upstream(query)

    async def get_campground(self, campground_id: str) -> CampgroundSearchResult:
        """Resolve an exact eligible native campground ID without a database.

        Raises
        ------
        ValueError
            If the ID is blank, unknown, hidden or unavailable for online camping.
        """
        campground_id = self._native_id(campground_id)
        results = await self._complete_search(
            ProviderSearchQuery(entity_type=SearchEntityType.CAMPGROUND)
        )
        for result in results:
            if (
                isinstance(result, CampgroundSearchResult)
                and result.campground_id == campground_id
            ):
                return result
        raise ValueError(f"Unknown or unbookable campground ID: {campground_id}")

    async def get_recreation_area(
        self, recreation_area_id: str
    ) -> RecreationAreaSearchResult:
        """Resolve a visible native recreation area, including an empty area."""
        recreation_area_id = self._native_id(recreation_area_id)
        results = await self._complete_search(
            ProviderSearchQuery(
                entity_type=SearchEntityType.RECREATION_AREA,
                recreation_area_id=recreation_area_id,
            )
        )
        for result in results:
            if (
                isinstance(result, RecreationAreaSearchResult)
                and result.recreation_area_id == recreation_area_id
            ):
                return result
        raise ValueError(f"Unknown recreation-area ID: {recreation_area_id}")

    async def filter_campgrounds(
        self,
        campgrounds: list[CampgroundSearchResult],
        *,
        query: str = "",
        state: str | None = None,
    ) -> list[CampgroundSearchResult]:
        """Apply provider-defined discovery filters to resolved campground targets.

        Catalog providers use local substring matching. Providers whose search
        relevance is defined upstream override this hook to retain that behavior
        for explicit selections. A valid target filtered out here is not an
        unknown-ID error.
        """
        request = ProviderSearchQuery(
            query=query.strip(),
            state=state.strip().upper() if state is not None else None,
            entity_type=SearchEntityType.CAMPGROUND,
        )
        return [result for result in campgrounds if result.matches(request)]

    async def iter_campgrounds(
        self, recreation_area_id: str
    ) -> AsyncIterator[CampgroundSearchResult]:
        """Enumerate every eligible child of a valid area without a result cap.

        Complete upstream responses are validated before yielding any target.
        Unknown areas fail; a known area without camping produces no targets.
        """
        recreation_area_id = self._native_id(recreation_area_id)
        await self.get_recreation_area(recreation_area_id)
        results = await self._complete_search(
            ProviderSearchQuery(
                entity_type=SearchEntityType.CAMPGROUND,
                recreation_area_id=recreation_area_id,
            )
        )
        unique = {
            result.campground_id: result
            for result in results
            if isinstance(result, CampgroundSearchResult)
            and result.recreation_area_id == recreation_area_id
        }
        for result in unique.values():
            yield result

    @staticmethod
    def _native_id(value: str) -> str:
        """Normalize opaque selectors without coercing their native identity."""
        value = value.strip()
        if not value:
            raise ValueError("Native IDs must not be blank")
        return value

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

    async def list_campsites(self, park_id: str) -> list[CampsiteDTO]:
        """
        List eligible overnight campsites in the target park without filtering by availability.
        """
        raise NotImplementedError(
            f"{self.provider.name} does not expose a campsite catalog."
        )

    @abstractmethod
    async def sync_metadata(self) -> None:
        """
        Background task to update the 'Search' and 'Campground'
        tables with the latest info from the provider.
        """

    async def enrich_metadata(self) -> None:
        """Optionally refresh cached destination details after catalog ingestion."""
        return None

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
        SQL statement to search recreation areas with aggregated child capabilities.
        """
        agg_electric = (
            func.coalesce(
                func.max(case((Campground.has_electric.is_(True), 1), else_=0)), 0
            )
            == 1
        )
        agg_water = (
            func.coalesce(
                func.max(case((Campground.has_water.is_(True), 1), else_=0)), 0
            )
            == 1
        )
        agg_sewer = (
            func.coalesce(
                func.max(case((Campground.has_sewer.is_(True), 1), else_=0)), 0
            )
            == 1
        )
        agg_pets = (
            func.coalesce(
                func.max(case((Campground.pets_allowed.is_(True), 1), else_=0)), 0
            )
            == 1
        )
        agg_ada = (
            func.coalesce(
                func.max(case((Campground.ada_accessible.is_(True), 1), else_=0)), 0
            )
            == 1
        )
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
                Search.city,
                Search.state,
                Search.country,
                Search.latitude,
                Search.longitude,
                Search.reservable,
                Search.has_electric,
                Search.has_water,
                Search.has_sewer,
                Search.pets_allowed,
                Search.ada_accessible,
                Search.max_rv_length,
            ],
            select=select(
                (
                    literal(f"RecreationArea/{self.provider.id}/")
                    + RecreationArea.id
                    + "/"
                ).label("id"),
                literal("RecreationArea").label("entity_type"),
                literal(self.provider.id).label("provider_id"),
                literal(self.provider.name).label("provider_name"),
                RecreationArea.id.label("recreation_area_id"),
                RecreationArea.name.label("recreation_area_name"),
                null().label("campground_id"),
                null().label("campground_name"),
                RecreationArea.city.label("city"),
                RecreationArea.state.label("state"),
                RecreationArea.country.label("country"),
                RecreationArea.latitude.label("latitude"),
                RecreationArea.longitude.label("longitude"),
                RecreationArea.reservable.label("reservable"),
                agg_electric.label("has_electric"),
                agg_water.label("has_water"),
                agg_sewer.label("has_sewer"),
                agg_pets.label("pets_allowed"),
                agg_ada.label("ada_accessible"),
                func.max(Campground.max_rv_length).label("max_rv_length"),
            )
            .select_from(
                RecreationArea.__table__.outerjoin(
                    Campground,
                    and_(
                        Campground.recreation_area_id == RecreationArea.id,
                        Campground.provider_id == RecreationArea.provider_id,
                        Campground.enabled.is_(True),
                        Campground.reservable.is_(True),
                    ),
                )
            )
            .where(
                RecreationArea.provider_id == self.provider.id,
                RecreationArea.enabled.is_(True),
            )
            .group_by(
                RecreationArea.id,
                RecreationArea.name,
                RecreationArea.city,
                RecreationArea.state,
                RecreationArea.country,
                RecreationArea.latitude,
                RecreationArea.longitude,
                RecreationArea.reservable,
            ),
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
                Search.city,
                Search.state,
                Search.country,
                Search.latitude,
                Search.longitude,
                Search.reservable,
                Search.campsite_types,
                Search.has_electric,
                Search.has_water,
                Search.has_sewer,
                Search.pets_allowed,
                Search.ada_accessible,
                Search.max_rv_length,
            ],
            select=select(
                (
                    literal(f"Campground/{self.provider.id}/")
                    + func.coalesce(RecreationArea.id, "")
                    + "/"
                    + Campground.id
                ).label("id"),
                literal("Campground").label("entity_type"),
                literal(self.provider.id).label("provider_id"),
                literal(self.provider.name).label("provider_name"),
                RecreationArea.id.label("recreation_area_id"),
                RecreationArea.name.label("recreation_area_name"),
                Campground.id.label("campground_id"),
                Campground.name.label("campground_name"),
                Campground.city.label("city"),
                Campground.state.label("state"),
                Campground.country.label("country"),
                Campground.latitude.label("latitude"),
                Campground.longitude.label("longitude"),
                Campground.reservable.label("reservable"),
                Campground.campsite_types.label("campsite_types"),
                Campground.has_electric.label("has_electric"),
                Campground.has_water.label("has_water"),
                Campground.has_sewer.label("has_sewer"),
                Campground.pets_allowed.label("pets_allowed"),
                Campground.ada_accessible.label("ada_accessible"),
                Campground.max_rv_length.label("max_rv_length"),
            )
            .select_from(
                Campground.__table__.outerjoin(
                    RecreationArea,
                    and_(
                        Campground.recreation_area_id == RecreationArea.id,
                        Campground.provider_id == RecreationArea.provider_id,
                    ),
                )
            )
            .where(
                Campground.provider_id == self.provider.id,
                Campground.enabled.is_(True),
                Campground.reservable.is_(True),
            ),
        )
        return campgrounds

    async def populate_search_table(
        self, session: AsyncSession, *, commit: bool = True
    ) -> None:
        """
        Populate search rows and commit them with any pending metadata updates.

        Reuse the session's current transaction so an ingestion failure
        cannot publish metadata separately from its search index.
        """
        logger.info(
            "Populating search table",
            provider=self.provider.name,
        )
        await session.execute(
            delete(Search).where(Search.provider_id == self.provider.id)
        )
        await session.execute(self.search_rec_area_statement)
        await session.execute(self.search_campground_statement)
        type_rows = await session.execute(
            select(Campground.recreation_area_id, Campground.campsite_types).where(
                Campground.provider_id == self.provider.id,
                Campground.enabled.is_(True),
                Campground.reservable.is_(True),
                Campground.recreation_area_id.is_not(None),
                Campground.campsite_types.is_not(None),
            )
        )
        raw_rows = type_rows.all()
        if inspect.iscoroutine(raw_rows):
            raw_rows.close()
            raw_rows = ()
        area_types: dict[str, set[str]] = {}
        for area_id, site_types in raw_rows:
            if area_id and site_types:
                area_types.setdefault(str(area_id), set()).update(site_types)
        for area_id, combined_types in area_types.items():
            await session.execute(
                update(Search)
                .where(
                    Search.id == f"RecreationArea/{self.provider.id}/{area_id}/",
                )
                .values(campsite_types=sorted(combined_types))
            )
        if commit:
            await session.commit()
        else:
            await session.flush()

    async def _existing_campground_capabilities(
        self, session: AsyncSession
    ) -> dict[str, CampgroundCapabilities]:
        """Load verified discovery capabilities keyed by campground ID before catalog upsert."""
        rows = (
            await session.execute(
                select(
                    Campground.id,
                    Campground.campsite_types,
                    Campground.has_electric,
                    Campground.has_water,
                    Campground.has_sewer,
                    Campground.pets_allowed,
                    Campground.ada_accessible,
                    Campground.max_rv_length,
                ).where(Campground.provider_id == self.provider.id)
            )
        ).all()
        return {
            row.id: CampgroundCapabilities(
                campsite_types=list(row.campsite_types) if row.campsite_types else None,
                has_electric=bool(row.has_electric),
                has_water=bool(row.has_water),
                has_sewer=bool(row.has_sewer),
                pets_allowed=bool(row.pets_allowed),
                ada_accessible=bool(row.ada_accessible),
                max_rv_length=row.max_rv_length,
            )
            for row in rows
        }

    @classmethod
    @abstractmethod
    def get_rec_area_url(cls, rec_area_id: str) -> str:
        """
        Get the URL for a recreation area.
        """

    @classmethod
    @abstractmethod
    def get_campground_url(
        cls, campground_id: str, *, rec_area_id: str | None = None
    ) -> str:
        """
        Get the URL for a campground, with park context when required.
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
