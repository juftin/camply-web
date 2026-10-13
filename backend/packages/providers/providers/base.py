"""
Base Provider Configuration
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, ClassVar

import httpx
import structlog
from pydantic import BaseModel
from sqlalchemy import Insert, delete, insert, literal, null, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import concat

from camply_core.models import CampsiteDTO
from camply_core.providers.base import NullHandler
from camply_core.transport import (
    ProviderCircuitBreaker,
    RetryStrategy,
    RetryTransport,
)
from db.models import Campground, Provider, RecreationArea, Search

logger = structlog.getLogger()


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

            self.user_agent = UserAgent(browsers=["Chrome"]).random
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
                RecreationArea.name.label("recreation_area_name"),
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
                RecreationArea.name.label("recreation_area_name"),
                Campground.id.label("campground_id"),
                Campground.name.label("campground_name"),
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


class DatabasePopulator(ABC, BaseModel):
    """
    Class that supports populating the database with data.
    """

    @abstractmethod
    async def to_database(self, session: AsyncSession) -> None:
        """
        Populate the database with the data.
        """


__all__ = [
    "BaseProvider",
    "DatabasePopulator",
    "NullHandler",
    "ProviderCircuitBreaker",
    "RetryStrategy",
    "RetryTransport",
]
