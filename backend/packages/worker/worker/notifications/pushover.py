# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Pushover notification provider implementation.
"""

from typing import Any, ClassVar

import httpx
import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from worker.notifications.base import BaseNotificationProvider, NotificationDTO

logger = structlog.getLogger(__name__)


class PushoverConfig(BaseSettings):
    """
    Pushover-specific configuration.
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="PUSHOVER_",
        case_sensitive=False,
    )

    app_token: str = Field(default="")
    api_url: str = "https://api.pushover.net/1/messages.json"


class PushoverProvider(BaseNotificationProvider):
    """
    Sends notifications via the Pushover API.

    Requires:
      - PUSHOVER_APP_TOKEN environment variable for the application token.
      - User's pushover_token stored in the User model.
    """

    config: ClassVar[PushoverConfig] = PushoverConfig()

    @property
    def provider_id(self) -> str:
        return "pushover"

    async def send_alert(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> None:
        """
        Send a push notification via Pushover.

        Args:
            user_config: Must contain "user_key" (the Pushover user token).
            payload: The notification content.
        """
        user_key = str(user_config.get("user_key", ""))
        if not user_key:
            logger.warning("No user_key in Pushover config, skipping")
            return

        if not self.config.app_token:
            logger.error("PUSHOVER_APP_TOKEN not configured, cannot send")
            return

        message_data = {
            "token": self.config.app_token,
            "user": user_key,
            "title": payload.title,
            "message": payload.message,
            "url": payload.booking_url,
            "url_title": "Book Now",
            "priority": 1,  # High priority (bypasses quiet hours)
            "sound": "pushover",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=self.config.api_url, json=message_data, timeout=10.0
            )
            response.raise_for_status()

        logger.info(
            "Pushover notification sent",
            user_key=user_key[:4] + "...",
            title=payload.title,
        )
