"""
Base notification provider ABC and shared DTO.
"""

from abc import ABC, abstractmethod
from typing import Any

from camply_core.models import NotificationDTO


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
