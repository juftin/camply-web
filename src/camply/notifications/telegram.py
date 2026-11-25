"""Deliver campsite alerts via the Telegram Bot API."""

import re
from typing import Any, ClassVar

import httpx2
import jiter

from camply.notifications.base import BaseNotificationProvider, NotificationDTO

_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9:_-]+$")


class TelegramProvider(BaseNotificationProvider):
    """Send campsite notifications to a Telegram chat using a bot token."""

    api_base_url: ClassVar[str] = "https://api.telegram.org"

    def __init__(self, client: httpx2.AsyncClient | None = None) -> None:
        self._client = client

    @property
    def provider_id(self) -> str:
        return "telegram"

    async def send_alert(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> None:
        """Deliver a Telegram message and require explicit Bot API acceptance."""
        if not await self.send_accepted(user_config, payload):
            raise ValueError("telegram did not accept the notification")

    async def send_accepted(
        self, user_config: dict[str, Any], payload: NotificationDTO
    ) -> bool:
        """POST a Telegram sendMessage payload and require ``{"ok": true}``."""
        bot_token = str(user_config["bot_token"]).strip()
        if _TOKEN_PATTERN.fullmatch(bot_token) is None:
            raise ValueError("Invalid Telegram bot token format")
        chat_id = str(user_config["chat_id"]).strip()
        lines = [payload.title, payload.message]
        if payload.booking_url:
            lines.append(payload.booking_url)
        data = {
            "chat_id": chat_id,
            "text": "\n".join(lines),
        }
        url = f"{self.api_base_url.rstrip('/')}/bot{bot_token}/sendMessage"

        async def publish(client: httpx2.AsyncClient) -> bool:
            response = await client.post(
                url=url,
                json=data,
                timeout=10.0,
                follow_redirects=False,
            )
            response.raise_for_status()
            body = jiter.from_json(response.content)
            return isinstance(body, dict) and body.get("ok") is True

        if self._client is not None:
            return await publish(self._client)
        async with httpx2.AsyncClient() as client:
            return await publish(client)
