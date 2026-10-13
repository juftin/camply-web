"""
Base Provider Client for campsite booking APIs.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, ClassVar

import httpx
import structlog
from fake_useragent import UserAgent
from pydantic import BaseModel, field_validator

from camply_core.models import CampsiteDTO
from camply_core.transport import ProviderCircuitBreaker, RetryStrategy, RetryTransport

logger = structlog.getLogger()


class NullHandler(BaseModel):
    """
    Pydantic base model that converts empty strings to None before validation.
    """

    @field_validator("*", mode="before")
    @classmethod
    def convert_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class BaseProviderClient(ABC):
    """
    Pure async HTTP client for querying campsite providers.
    """

    _circuit_breakers: ClassVar[dict[str, ProviderCircuitBreaker]] = {}

    def __init__(self) -> None:
        try:
            self.user_agent = UserAgent(browsers=["Chrome"]).random
        except Exception:
            self.user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

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
        """
        return RetryStrategy()

    @property
    def headers(self) -> dict[str, str]:
        """
        HTTP headers for provider requests.
        """
        return {"User-Agent": self.user_agent}

    @classmethod
    def circuit_breaker_state(cls) -> dict[str, Any] | None:
        """
        Return the current circuit-breaker state for this provider.
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
        Force-reset the circuit breaker for this provider class (useful for tests).
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

    async def aclose(self) -> None:
        """
        Close the underlying HTTP client cleanly.
        """
        await self.async_client.aclose()

    @abstractmethod
    async def find_availabilities(
        self,
        park_id: str,
        start_date: date,
        end_date: date,
    ) -> list[CampsiteDTO]:
        """
        Find campsite availabilities for the target park and dates.
        Nights queried are [start_date, end_date).
        """

    @classmethod
    @abstractmethod
    def get_rec_area_url(cls, rec_area_id: str) -> str:
        """
        Get the booking/informational URL for a recreation area.
        """

    @classmethod
    @abstractmethod
    def get_campground_url(cls, campground_id: str) -> str:
        """
        Get the booking URL for a campground.
        """
