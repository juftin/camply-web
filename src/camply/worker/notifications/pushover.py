"""
Pushover notification provider implementation.
"""

from typing import Any, ClassVar

import httpx2
import jiter
import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from camply.worker.notifications.base import BaseNotificationProvider, NotificationDTO

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

    def __init__(self, client: httpx2.AsyncClient | None = None) -> None:
        self._client = client

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
        await self._send_alert(user_config, payload, require_acceptance=False)

    async def send_accepted(self, user_key: str, payload: NotificationDTO) -> bool:
        """Require explicit upstream acceptance before acknowledging durable delivery."""
        return await self._send_alert(
            {"user_key": user_key}, payload, require_acceptance=True
        )

    async def _send_alert(
        self,
        user_config: dict[str, Any],
        payload: NotificationDTO,
        *,
        require_acceptance: bool,
    ) -> bool:
        """Share request construction while preserving legacy delivery behavior."""
        user_key = str(user_config.get("user_key", ""))
        if not user_key:
            logger.warning("No user_key in Pushover config, skipping")
            return False

        if not self.config.app_token:
            logger.error("PUSHOVER_APP_TOKEN not configured, cannot send")
            return False

        message_data = {
            "token": self.config.app_token,
            "user": user_key,
            "title": payload.title,
            "message": payload.message,
            "url": payload.booking_url,
            "url_title": payload.url_title,
            "priority": 1,  # High priority (bypasses quiet hours)
            "sound": "pushover",
        }

        if self._client is not None:
            response = await self._client.post(
                url=self.config.api_url, json=message_data, timeout=10.0
            )
            response.raise_for_status()
            if (
                require_acceptance
                and jiter.from_json(response.content).get("status") != 1
            ):
                return False
        else:
            async with httpx2.AsyncClient() as client:
                response = await client.post(
                    url=self.config.api_url, json=message_data, timeout=10.0
                )
                response.raise_for_status()
                if (
                    require_acceptance
                    and jiter.from_json(response.content).get("status") != 1
                ):
                    return False

        logger.info(
            "Pushover notification sent",
            title=payload.title,
        )
        return True
