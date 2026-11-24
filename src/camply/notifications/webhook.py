"""Deliver campsite alerts as structured JSON HTTP POST webhooks."""

from datetime import datetime, timezone
from typing import Any

import httpx2

from camply.notifications.base import BaseNotificationProvider, NotificationDTO

_HTTP_OK_MIN = 200
_HTTP_OK_MAX = 300


class WebhookProvider(BaseNotificationProvider):
    """Send structured JSON stay notifications to a custom HTTP(S) webhook."""

    def __init__(self, client: httpx2.AsyncClient | None = None) -> None:
        self._client = client

    @property
    def provider_id(self) -> str:
        return "webhook"

    async def send_alert(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> None:
        """Deliver a webhook notification and require a 2xx acceptance response."""
        if not await self.send_accepted(user_config, payload):
            raise ValueError("webhook did not accept the notification")

    async def send_accepted(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> bool:
        """POST a JSON payload to the configured webhook URL and require a 2xx response."""
        url = str(user_config["url"])
        headers = {
            str(key): str(value)
            for key, value in (user_config.get("headers") or {}).items()
        }
        body: dict[str, Any] = {
            "title": payload.title,
            "message": payload.message,
            "booking_url": payload.booking_url,
            "url_title": payload.url_title,
            "park_name": payload.park_name,
            "campsite_name": payload.campsite_name,
            "start_date": payload.start_date.isoformat(),
            "end_date": payload.end_date.isoformat(),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "metadata": payload.metadata,
        }

        async def publish(client: httpx2.AsyncClient) -> bool:
            response = await client.post(
                url=url,
                json=body,
                headers=headers,
                timeout=10.0,
                follow_redirects=False,
            )
            response.raise_for_status()
            return _HTTP_OK_MIN <= response.status_code < _HTTP_OK_MAX

        if self._client is not None:
            return await publish(self._client)
        async with httpx2.AsyncClient() as client:
            return await publish(client)
