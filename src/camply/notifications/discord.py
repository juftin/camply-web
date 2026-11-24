"""Deliver campsite alerts to a Discord incoming webhook."""

from typing import Any

import httpx2

from camply.notifications.base import BaseNotificationProvider, NotificationDTO

_HTTP_OK_MIN = 200
_HTTP_OK_MAX = 300
_EMBED_COLOR = 0x2E7D32
_MAX_TITLE_LENGTH = 256
_MAX_DESCRIPTION_LENGTH = 4096
_MAX_FIELD_LENGTH = 1024


def _clamp(text: str, limit: int, *, fallback: str = "-") -> str:
    """Ensure Discord embed strings are non-empty and within Discord length limits."""
    cleaned = text.strip()
    if not cleaned:
        return fallback
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"


class DiscordProvider(BaseNotificationProvider):
    """Send rich embed campsite notifications to a Discord webhook URL."""

    def __init__(self, client: httpx2.AsyncClient | None = None) -> None:
        self._client = client

    @property
    def provider_id(self) -> str:
        return "discord"

    async def send_alert(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> None:
        """Deliver a Discord webhook notification and require a 2xx acceptance response."""
        if not await self.send_accepted(user_config, payload):
            raise ValueError("discord did not accept the notification")

    async def send_accepted(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> bool:
        """POST a Discord webhook embed payload and require a 2xx response."""
        webhook_url = str(user_config["webhook_url"])
        embed: dict[str, Any] = {
            "title": _clamp(payload.title, _MAX_TITLE_LENGTH, fallback="Camply Alert"),
            "description": _clamp(payload.message, _MAX_DESCRIPTION_LENGTH),
            "color": _EMBED_COLOR,
            "fields": [
                {
                    "name": "Park",
                    "value": _clamp(payload.park_name, _MAX_FIELD_LENGTH),
                    "inline": True,
                },
                {
                    "name": "Campsite",
                    "value": _clamp(payload.campsite_name, _MAX_FIELD_LENGTH),
                    "inline": True,
                },
                {
                    "name": "Dates",
                    "value": f"{payload.start_date.isoformat()} to {payload.end_date.isoformat()}",
                    "inline": False,
                },
            ],
        }
        if payload.booking_url:
            embed["url"] = payload.booking_url
        body = {"username": "camply", "embeds": [embed]}

        async def publish(client: httpx2.AsyncClient) -> bool:
            response = await client.post(
                url=webhook_url,
                json=body,
                timeout=10.0,
                follow_redirects=False,
            )
            response.raise_for_status()
            return _HTTP_OK_MIN <= response.status_code < _HTTP_OK_MAX

        if self._client is not None:
            return await publish(self._client)
        async with httpx2.AsyncClient() as client:
            return await publish(client)
