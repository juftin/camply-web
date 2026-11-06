"""Publish campsite alerts to the user's ntfy server."""

from typing import Any

import httpx2
import jiter

from camply.worker.notifications.base import BaseNotificationProvider, NotificationDTO


class NtfyProvider(BaseNotificationProvider):
    """Use JSON publishing to preserve Unicode titles and messages."""

    def __init__(self, client: httpx2.AsyncClient | None = None) -> None:
        self._client = client

    @property
    def provider_id(self) -> str:
        return "ntfy"

    async def send_alert(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> None:
        """Publish an alert and require explicit upstream acceptance."""
        if not await self.send_accepted(user_config, payload):
            raise ValueError("ntfy did not accept the notification")

    async def send_accepted(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> bool:
        """Return true only for an accepted message on the intended topic."""
        topic = user_config["topic"]
        data = {
            "topic": topic,
            "title": payload.title,
            "message": payload.message,
            "click": payload.booking_url,
            "priority": 4,
        }
        headers = {}
        if token := user_config.get("access_token"):
            headers["Authorization"] = f"Bearer {token}"

        async def publish(client: httpx2.AsyncClient) -> bool:
            response = await client.post(
                url=user_config["server_url"].rstrip("/") + "/",
                json=data,
                headers=headers,
                timeout=10.0,
                follow_redirects=False,
            )
            response.raise_for_status()
            body = jiter.from_json(response.content)
            return (
                isinstance(body, dict)
                and body.get("event") == "message"
                and body.get("topic") == topic
                and bool(body.get("id"))
            )

        if self._client is not None:
            return await publish(self._client)
        async with httpx2.AsyncClient() as client:
            return await publish(client)
