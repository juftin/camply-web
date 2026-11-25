"""Deliver campsite alerts to a Slack incoming webhook."""

from typing import Any

import httpx2

from camply.notifications.base import BaseNotificationProvider, NotificationDTO

_HTTP_OK_MIN = 200
_HTTP_OK_MAX = 300


def _escape_mrkdwn(text: str) -> str:
    """Escape Slack mrkdwn control characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class SlackProvider(BaseNotificationProvider):
    """Send formatted campsite notifications to a Slack incoming webhook URL."""

    def __init__(self, client: httpx2.AsyncClient | None = None) -> None:
        self._client = client

    @property
    def provider_id(self) -> str:
        return "slack"

    async def send_alert(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> None:
        """Deliver a Slack webhook notification and require a 2xx acceptance response."""
        if not await self.send_accepted(user_config, payload):
            raise ValueError("slack did not accept the notification")

    async def send_accepted(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> bool:
        """POST a formatted Slack message payload and require a 2xx response."""
        webhook_url = str(user_config["webhook_url"])
        lines = [f"*{_escape_mrkdwn(payload.title)}*", _escape_mrkdwn(payload.message)]
        if payload.booking_url:
            label = _escape_mrkdwn(payload.url_title).replace("|", "/")
            lines.append(f"<{payload.booking_url}|{label}>")
        body = {"text": "\n".join(lines)}

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
