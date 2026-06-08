"""
Extended tests for the Pushover notification provider.
"""

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from worker.notifications.base import NotificationDTO
from worker.notifications.pushover import PushoverConfig, PushoverProvider


class TestPushoverConfig:
    """Tests for PushoverConfig settings."""

    def test_default_app_token_empty(self) -> None:
        config = PushoverConfig()
        assert config.app_token == ""

    def test_default_api_url(self) -> None:
        config = PushoverConfig()
        assert config.api_url == "https://api.pushover.net/1/messages.json"


class TestPushoverProvider:
    """Tests for PushoverProvider notification sending."""

    @pytest.mark.anyio
    async def test_send_alert_success(self) -> None:
        """send_alert should POST to Pushover API and log success."""
        provider = PushoverProvider()
        user_config = {"user_key": "test_user_key_abc123"}

        payload = NotificationDTO(
            title="Test Alert",
            message="A test notification",
            booking_url="https://example.com/book",
            park_name="Test Park",
            campsite_name="Site 1",
            start_date=datetime.date(2026, 9, 1),
            end_date=datetime.date(2026, 9, 3),
        )

        with patch.object(provider.config, "app_token", "test_app_token"):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.raise_for_status = AsyncMock()
                mock_client.post.return_value = mock_response
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                await provider.send_alert(user_config, payload)

                # Verify POST was called with correct data
                mock_client.post.assert_called_once()
                call_kwargs = mock_client.post.call_args.kwargs
                assert call_kwargs["url"] == "https://api.pushover.net/1/messages.json"
                assert call_kwargs["json"]["token"] == "test_app_token"
                assert call_kwargs["json"]["user"] == "test_user_key_abc123"
                assert call_kwargs["json"]["title"] == "Test Alert"

    @pytest.mark.anyio
    async def test_send_alert_no_user_key_skips(self) -> None:
        """send_alert should skip when no user_key is provided."""
        provider = PushoverProvider()
        payload = NotificationDTO(
            title="Test",
            message="Test message",
            booking_url="",
            park_name="Test",
            campsite_name="Test",
            start_date=datetime.date(2026, 9, 1),
            end_date=datetime.date(2026, 9, 3),
        )

        with patch("httpx.AsyncClient") as mock_client:
            await provider.send_alert({"user_key": ""}, payload)
            mock_client.assert_not_called()

    @pytest.mark.anyio
    async def test_send_alert_no_app_token_skips(self) -> None:
        """send_alert should skip when app_token is not configured."""
        provider = PushoverProvider()
        user_config = {"user_key": "test_key"}

        payload = NotificationDTO(
            title="Test",
            message="Test message",
            booking_url="",
            park_name="Test",
            campsite_name="Test",
            start_date=datetime.date(2026, 9, 1),
            end_date=datetime.date(2026, 9, 3),
        )

        with patch.object(provider.config, "app_token", ""):
            with patch("httpx.AsyncClient") as mock_client:
                await provider.send_alert(user_config, payload)
                mock_client.assert_not_called()

    @pytest.mark.anyio
    async def test_provider_id(self) -> None:
        provider = PushoverProvider()
        assert provider.provider_id == "pushover"

    @pytest.mark.anyio
    async def test_send_alert_http_error(self) -> None:
        """send_alert should propagate HTTP errors."""
        provider = PushoverProvider()
        user_config = {"user_key": "test_key"}

        payload = NotificationDTO(
            title="Test",
            message="Test",
            booking_url="",
            park_name="Test",
            campsite_name="Test",
            start_date=datetime.date(2026, 9, 1),
            end_date=datetime.date(2026, 9, 3),
        )

        with patch.object(provider.config, "app_token", "token"):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post.side_effect = Exception("HTTP Error")
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                with pytest.raises(Exception, match="HTTP Error"):
                    await provider.send_alert(user_config, payload)
