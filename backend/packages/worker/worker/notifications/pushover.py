"""
Pushover notification provider implementation.
"""

from typing import Any, ClassVar

import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from camply_core.notifications.pushover import PushoverClient
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

        client = PushoverClient(
            app_token=self.config.app_token,
            api_url=self.config.api_url,
        )
        await client.send_alert(
            user_key=user_key,
            payload=payload,
            priority=1,
        )
