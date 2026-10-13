"""
Pushover alert delivery transport.
"""

from typing import Any

import httpx
import structlog

from camply_core.errors import NotificationError
from camply_core.models import NotificationDTO

logger = structlog.getLogger()

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
# Default endpoint for Pushover message API.

_KEY_PREFIX_LENGTH: int = 4
# Number of characters to retain when masking user keys in log output.


class PushoverClient:
    """
    Client for delivering alerts via Pushover API with explicit credentials.
    """

    def __init__(
        self,
        app_token: str | None = None,
        api_url: str = PUSHOVER_API_URL,
    ) -> None:
        self.app_token = app_token or ""
        self.api_url = api_url

    async def send_alert(
        self,
        user_key: str,
        payload: NotificationDTO,
        app_token: str | None = None,
        priority: int = 1,
    ) -> None:
        """
        Send an alert notification to a Pushover user.
        """
        token = app_token or self.app_token
        if not token:
            raise NotificationError("Pushover application token is required.")
        if not user_key:
            raise NotificationError("Pushover user key is required.")

        message_data: dict[str, Any] = {
            "token": token,
            "user": user_key,
            "title": payload.title,
            "message": payload.message,
            "url": payload.booking_url,
            "url_title": "Book Now",
            "priority": priority,
            "sound": "pushover",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=self.api_url,
                    json=message_data,
                    timeout=10.0,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error(
                "Pushover notification failed",
                error=str(exc),
                title=payload.title,
            )
            raise NotificationError(f"Failed to send Pushover alert: {exc}") from exc

        masked_key = (
            user_key[:_KEY_PREFIX_LENGTH] + "..."
            if len(user_key) >= _KEY_PREFIX_LENGTH
            else "***"
        )
        logger.info(
            "Pushover notification sent",
            user_key=masked_key,
            title=payload.title,
        )
