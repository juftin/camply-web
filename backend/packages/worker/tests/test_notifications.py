"""
Tests for the send_pushover_notification task.
"""

import uuid as uuid_mod
from unittest.mock import AsyncMock, MagicMock, patch

from db.models import User
from worker.notifications.pushover import PushoverProvider
from worker.tasks.notifications import send_pushover_notification


def _make_mock_session(user: User | None) -> AsyncMock:
    """Create a mock async DB session that returns the given user."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    return mock_session


def _make_mock_db(session: AsyncMock) -> MagicMock:
    """Create a mock db config that returns the given session."""
    mock_db = MagicMock()
    mock_db.get_session.return_value = session
    return mock_db


class TestSendPushoverNotification:
    """Tests for the Pushover notification delivery task."""

    def test_user_not_found(self) -> None:
        """Task should return error for non-existent user."""
        fake_user_id = str(uuid_mod.uuid4())
        notification = {
            "title": "Test",
            "message": "Test message",
            "booking_url": "https://example.com",
            "park_name": "Test Park",
            "campsite_name": "Test Site",
            "start_date": "2026-09-01",
            "end_date": "2026-09-03",
            "metadata": {},
        }

        mock_session = _make_mock_session(user=None)
        mock_db = _make_mock_db(mock_session)

        with patch("worker.tasks.notifications.db", mock_db):
            result = send_pushover_notification(fake_user_id, notification)

        assert result["status"] == "error"
        assert result["reason"] == "user_not_found"

    def test_no_pushover_token_skips(self) -> None:
        """Task should skip when user has no pushover_token."""
        user = User(
            id=uuid_mod.uuid4(),
            email="no-token@example.com",
            pushover_token=None,
        )

        mock_session = _make_mock_session(user=user)
        mock_db = _make_mock_db(mock_session)

        notification = {
            "title": "Test",
            "message": "Test message",
            "booking_url": "https://example.com",
            "park_name": "Test Park",
            "campsite_name": "Test Site",
            "start_date": "2026-09-01",
            "end_date": "2026-09-03",
            "metadata": {},
        }

        with patch("worker.tasks.notifications.db", mock_db):
            result = send_pushover_notification(str(user.id), notification)

        assert result["status"] == "skipped"
        assert result["reason"] == "no_pushover_token"

    def test_successful_send(self) -> None:
        """Task should send notification when user has pushover_token."""
        user = User(
            id=uuid_mod.uuid4(),
            email="has-token@example.com",
            pushover_token="valid_pushover_user_key",
        )

        mock_session = _make_mock_session(user=user)
        mock_db = _make_mock_db(mock_session)

        notification = {
            "title": "Test Alert",
            "message": "A campsite is available!",
            "booking_url": "https://recreation.gov/camping/123",
            "park_name": "Yosemite",
            "campsite_name": "Lower Pines 042",
            "start_date": "2026-09-01",
            "end_date": "2026-09-03",
            "metadata": {},
        }

        with patch("worker.tasks.notifications.db", mock_db):
            with patch.object(
                PushoverProvider,
                "send_alert",
                new_callable=AsyncMock,
            ) as mock_send:
                result = send_pushover_notification(
                    str(user.id), notification
                )

        assert result["status"] == "success"
        mock_send.assert_called_once()

        call_args = mock_send.call_args
        assert call_args.kwargs["user_config"]["user_key"] == (
            "valid_pushover_user_key"
        )
        assert call_args.kwargs["payload"].title == "Test Alert"

    def test_invalid_notification_dto(self) -> None:
        """Task should handle malformed notification dicts."""
        user = User(
            id=uuid_mod.uuid4(),
            email="test@example.com",
            pushover_token="token123",
        )
        bad_notification = {"title": "Incomplete"}

        mock_session = _make_mock_session(user=user)
        mock_db = _make_mock_db(mock_session)

        with patch("worker.tasks.notifications.db", mock_db):
            result = send_pushover_notification(
                str(user.id), bad_notification
            )

        assert result["status"] == "error"
