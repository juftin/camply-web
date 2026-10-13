"""
Tests for PushoverClient in camply_core.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camply_core.errors import NotificationError
from camply_core.models import NotificationDTO
from camply_core.notifications import PushoverClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_pushover_missing_credentials() -> None:
    """Test error raised when credentials are missing."""
    client = PushoverClient()
    payload = NotificationDTO(
        title="Title",
        message="Message",
        booking_url="https://booking.com",
        park_name="Park",
        campsite_name="Site 1",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 2),
    )
    with pytest.raises(NotificationError, match="application token is required"):
        await client.send_alert(user_key="u1", payload=payload, app_token="")

    with pytest.raises(NotificationError, match="user key is required"):
        await client.send_alert(user_key="", payload=payload, app_token="token")


@pytest.mark.anyio
async def test_pushover_send_success() -> None:
    """Test successful alert delivery."""
    client = PushoverClient(app_token="app123")
    payload = NotificationDTO(
        title="Title",
        message="Message",
        booking_url="https://booking.com",
        park_name="Park",
        campsite_name="Site 1",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 2),
    )

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        await client.send_alert(user_key="user456", payload=payload)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["token"] == "app123"
        assert kwargs["json"]["user"] == "user456"
        assert kwargs["json"]["title"] == "Title"
