# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Base notification provider ABC and shared DTO.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class NotificationDTO(BaseModel):
    """
    Unified notification payload passed to all notification providers.
    Serialized as JSON for Celery task arguments.
    """

    title: str
    message: str
    booking_url: str
    park_name: str
    campsite_name: str
    start_date: date
    end_date: date
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseNotificationProvider(ABC):
    """
    ABC for notification delivery channels (Pushover, Email, Webhook, etc.).
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique slug: 'pushover', 'email', 'webhook'."""
        ...

    @abstractmethod
    async def send_alert(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> None:
        """
        Deliver the notification to the user.

        Args:
            user_config: Provider-specific user configuration
                         (e.g., user_key for Pushover).
            payload: The standardized notification data.
        """
        ...
