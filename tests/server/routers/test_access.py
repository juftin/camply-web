"""
Tests for the ``/api/request-access`` endpoint and invitation status lookup.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from camply.db.models import AccessRequest, User
from camply.db.models.access_request import AccessRequestStatus
from camply.notifications.ntfy import NtfyProvider
from camply.notifications.pushover import PushoverProvider
from camply.server.app import app
from camply.server.auth import CurrentUser, resolve_current_user
from tests.server.conftest import maker


def _tag() -> str:
    """
    Return a short unique token so tests sharing one database stay isolated.

    Returns
    -------
    str
        Eight-character hex identifier.
    """
    return uuid.uuid4().hex[:8]


async def _add_user(
    *,
    email: str,
    is_admin: bool = False,
    scanning_enabled: bool = True,
    notification_provider: str = "pushover",
    ntfy_topic: str | None = None,
    ntfy_server_url: str | None = None,
    ntfy_access_token: str | None = None,
    pushover_token: str | None = None,
) -> User:
    """
    Persist and return a synthetic user for access notification tests.

    Parameters
    ----------
    email : str
        User email address.
    is_admin : bool
        Whether the user is an administrator.
    scanning_enabled : bool
        Whether scanning and alerts are enabled for the user.
    notification_provider : str
        Notification channel (``ntfy`` or ``pushover``).
    ntfy_topic : str or None
        Optional explicit ntfy topic.
    ntfy_server_url : str or None
        Optional custom ntfy server URL.
    ntfy_access_token : str or None
        Optional ntfy bearer access token.
    pushover_token : str or None
        Optional Pushover user key.

    Returns
    -------
    User
        Persisted user instance.
    """
    async with maker() as session:
        user = User(
            email=email,
            is_admin=is_admin,
            is_invited=True,
            scanning_enabled=scanning_enabled,
            notification_provider=notification_provider,
            ntfy_server_url=ntfy_server_url,
            ntfy_access_token=ntfy_access_token,
            pushover_token=pushover_token,
            **({"ntfy_topic": ntfy_topic} if ntfy_topic is not None else {}),
        )
        session.add(user)
        await session.commit()
        return user


async def _disable_existing_admins() -> None:
    """Ensure prior test admins do not trigger unexpected alerts in isolated assertions."""
    async with maker() as session:
        await session.execute(
            update(User).where(User.is_admin.is_(True)).values(scanning_enabled=False)
        )
        await session.commit()


@pytest.fixture(autouse=True)
def mock_notification_providers() -> Generator[tuple[AsyncMock, AsyncMock], None, None]:
    """
    Prevent external HTTP calls from notification providers during access tests.

    Yields
    ------
    tuple[AsyncMock, AsyncMock]
        Mocked ``(NtfyProvider.send_accepted, PushoverProvider.send_accepted)`` pair.
    """
    with (
        patch.object(
            NtfyProvider, "send_accepted", new_callable=AsyncMock, return_value=True
        ) as ntfy_send,
        patch.object(
            PushoverProvider,
            "send_accepted",
            new_callable=AsyncMock,
            return_value=True,
        ) as pushover_send,
    ):
        yield ntfy_send, pushover_send


class TestRequestAccess:
    """Tests for POST /api/request-access."""

    def test_request_access_creates(self, test_client: TestClient) -> None:
        """A new email should return 201 with a success message."""
        response = test_client.post(
            "/api/request-access",
            json={"email": f"test-{_tag()}@example.com", "name": "Test User"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert "Thank you" in data["message"]

    def test_request_access_duplicate_is_idempotent(
        self, test_client: TestClient
    ) -> None:
        """Submitting the same email twice should still return 201."""
        payload = {"email": f"dup-{_tag()}@example.com"}
        first = test_client.post("/api/request-access", json=payload)
        assert first.status_code == 201

        second = test_client.post("/api/request-access", json=payload)
        assert second.status_code == 201
        assert "message" in second.json()

    def test_request_access_email_only(self, test_client: TestClient) -> None:
        """Submitting without a name should succeed."""
        response = test_client.post(
            "/api/request-access",
            json={"email": f"noname-{_tag()}@example.com"},
        )
        assert response.status_code == 201

    def test_request_access_normalizes_email(self, test_client: TestClient) -> None:
        """Email should be lowercased and stripped."""
        response = test_client.post(
            "/api/request-access",
            json={"email": f"  MixedCase-{_tag()}@Example.COM  "},
        )
        assert response.status_code == 201


class TestRequestAccessAdminNotifications:
    """Tests for zero-email admin notifications on new access requests."""

    @pytest.mark.asyncio
    async def test_notifies_configured_ntfy_and_pushover_admins(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_notification_providers: tuple[AsyncMock, AsyncMock],
    ) -> None:
        """Eligible ntfy and pushover admins receive a clean NotificationDTO on new requests."""
        ntfy_send, pushover_send = mock_notification_providers
        await _disable_existing_admins()
        monkeypatch.setattr(PushoverProvider.config, "app_token", "synthetic-app-token")

        tag = _tag()
        await _add_user(
            email=f"ntfy-admin-{tag}@example.test",
            is_admin=True,
            scanning_enabled=True,
            notification_provider="ntfy",
            ntfy_topic=f"admin-topic-{tag}",
            ntfy_server_url="https://ntfy.example.test",
            ntfy_access_token="synthetic-ntfy-token",
        )
        await _add_user(
            email=f"pushover-admin-{tag}@example.test",
            is_admin=True,
            scanning_enabled=True,
            notification_provider="pushover",
            pushover_token=f"pushover-key-{tag}",
        )

        requester_email = f"requester-{tag}@example.test"
        response = test_client.post(
            "/api/request-access",
            json={"email": f"  {requester_email.upper()} ", "name": "Ada Lovelace"},
        )
        assert response.status_code == 201

        ntfy_send.assert_awaited_once()
        assert ntfy_send.call_args.args[0] == {
            "topic": f"admin-topic-{tag}",
            "server_url": "https://ntfy.example.test",
            "access_token": "synthetic-ntfy-token",
        }
        ntfy_payload = ntfy_send.call_args.args[1]
        assert ntfy_payload.title == "New Camply access request"
        assert requester_email in ntfy_payload.message
        assert "Ada Lovelace" in ntfy_payload.message
        assert ntfy_payload.booking_url == ""

        pushover_send.assert_awaited_once()
        assert pushover_send.call_args.args[0] == f"pushover-key-{tag}"
        pushover_payload = pushover_send.call_args.args[1]
        assert pushover_payload.title == "New Camply access request"
        assert requester_email in pushover_payload.message
        assert pushover_payload.booking_url == ""

    @pytest.mark.asyncio
    async def test_does_not_notify_on_duplicate_request(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_notification_providers: tuple[AsyncMock, AsyncMock],
    ) -> None:
        """Duplicate requests trigger no second notification."""
        ntfy_send, pushover_send = mock_notification_providers
        await _disable_existing_admins()
        monkeypatch.setattr(PushoverProvider.config, "app_token", "synthetic-app-token")

        tag = _tag()
        await _add_user(
            email=f"dup-ntfy-{tag}@example.test",
            is_admin=True,
            scanning_enabled=True,
            notification_provider="ntfy",
            ntfy_topic=f"dup-topic-{tag}",
        )
        await _add_user(
            email=f"dup-push-{tag}@example.test",
            is_admin=True,
            scanning_enabled=True,
            notification_provider="pushover",
            pushover_token=f"dup-push-{tag}",
        )

        payload = {"email": f"same-{tag}@example.test"}
        assert test_client.post("/api/request-access", json=payload).status_code == 201
        assert ntfy_send.await_count == 1
        assert pushover_send.await_count == 1

        assert test_client.post("/api/request-access", json=payload).status_code == 201
        assert ntfy_send.await_count == 1
        assert pushover_send.await_count == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "outcome",
        [False, RuntimeError("https://ntfy.secret.internal/ secret-token-value")],
    )
    async def test_delivery_failure_does_not_fail_request(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_notification_providers: tuple[AsyncMock, AsyncMock],
        outcome: bool | Exception,
    ) -> None:
        """Notification errors or non-acceptance still return 201 and keep notifying."""
        ntfy_send, pushover_send = mock_notification_providers
        await _disable_existing_admins()
        monkeypatch.setattr(PushoverProvider.config, "app_token", "synthetic-app-token")

        tag = _tag()
        await _add_user(
            email=f"fail-ntfy-{tag}@example.test",
            is_admin=True,
            scanning_enabled=True,
            notification_provider="ntfy",
            ntfy_topic=f"fail-topic-{tag}",
        )
        await _add_user(
            email=f"ok-push-{tag}@example.test",
            is_admin=True,
            scanning_enabled=True,
            notification_provider="pushover",
            pushover_token=f"ok-push-{tag}",
        )

        if isinstance(outcome, Exception):
            ntfy_send.side_effect = outcome
        else:
            ntfy_send.return_value = outcome

        response = test_client.post(
            "/api/request-access",
            json={"email": f"resilient-{tag}@example.test"},
        )
        assert response.status_code == 201
        ntfy_send.assert_awaited_once()
        pushover_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_disabled_non_admin_and_unconfigured_admins(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_notification_providers: tuple[AsyncMock, AsyncMock],
    ) -> None:
        """Disabled, non-admin, or unconfigured admins are never notified."""
        ntfy_send, pushover_send = mock_notification_providers
        await _disable_existing_admins()
        monkeypatch.setattr(PushoverProvider.config, "app_token", "synthetic-app-token")

        tag = _tag()
        # Non-admin with valid ntfy config.
        await _add_user(
            email=f"regular-{tag}@example.test",
            is_admin=False,
            scanning_enabled=True,
            notification_provider="ntfy",
            ntfy_topic=f"regular-topic-{tag}",
        )
        # Admin with scanning disabled.
        await _add_user(
            email=f"paused-admin-{tag}@example.test",
            is_admin=True,
            scanning_enabled=False,
            notification_provider="ntfy",
            ntfy_topic=f"paused-topic-{tag}",
        )
        # Admin with ntfy selected but empty topic.
        await _add_user(
            email=f"empty-topic-admin-{tag}@example.test",
            is_admin=True,
            scanning_enabled=True,
            notification_provider="ntfy",
            ntfy_topic="",
        )
        # Admin with pushover selected but no user key.
        await _add_user(
            email=f"empty-pushover-admin-{tag}@example.test",
            is_admin=True,
            scanning_enabled=True,
            notification_provider="pushover",
            pushover_token=None,
        )

        response = test_client.post(
            "/api/request-access",
            json={"email": f"skip-check-{tag}@example.test"},
        )
        assert response.status_code == 201
        ntfy_send.assert_not_awaited()
        pushover_send.assert_not_awaited()

        # Also skip pushover admins when server app_token is unset.
        monkeypatch.setattr(PushoverProvider.config, "app_token", "")
        await _add_user(
            email=f"no-app-token-admin-{tag}@example.test",
            is_admin=True,
            scanning_enabled=True,
            notification_provider="pushover",
            pushover_token=f"user-key-{tag}",
        )
        response_two = test_client.post(
            "/api/request-access",
            json={"email": f"skip-check-two-{tag}@example.test"},
        )
        assert response_two.status_code == 201
        pushover_send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_executes_background_notifications_with_asgi_async_client(
        self,
        test_client: TestClient,
        mock_notification_providers: tuple[AsyncMock, AsyncMock],
    ) -> None:
        """Verify BackgroundTasks execute cleanly under ``httpx2.AsyncClient`` + ``ASGITransport``."""
        ntfy_send, _ = mock_notification_providers
        await _disable_existing_admins()
        tag = _tag()
        await _add_user(
            email=f"asgi-admin-{tag}@example.test",
            is_admin=True,
            scanning_enabled=True,
            notification_provider="ntfy",
            ntfy_topic=f"asgi-topic-{tag}",
        )

        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/request-access",
                json={"email": f"asgi-req-{tag}@example.test"},
            )
        assert response.status_code == 201
        ntfy_send.assert_awaited_once()
        assert ntfy_send.call_args.args[0]["topic"] == f"asgi-topic-{tag}"


class TestMeInvitationStatus:
    """Tests for ``invitation_status`` on ``GET /api/me`` and ``PATCH /api/me``."""

    @pytest.mark.asyncio
    async def test_invitation_status_prefers_most_recently_updated_match(
        self, test_client: TestClient
    ) -> None:
        """``GET /api/me`` and ``PATCH /api/me`` return the latest matching status."""
        tag = _tag()
        user = await _add_user(
            email=f"status-user-{tag}@example.test",
            is_admin=False,
        )
        now = dt.datetime.now(dt.timezone.utc)
        async with maker() as session:
            session.add_all(
                [
                    AccessRequest(
                        email=f"older-linked-{tag}@example.test",
                        status=AccessRequestStatus.PENDING.value,
                        user_id=user.id,
                        updated_at=now - dt.timedelta(hours=2),
                    ),
                    AccessRequest(
                        email=user.email,
                        status=AccessRequestStatus.REJECTED.value,
                        user_id=None,
                        updated_at=now - dt.timedelta(hours=1),
                    ),
                ]
            )
            await session.commit()

        current = CurrentUser(
            id=user.id,
            email=user.email,
            is_invited=False,
            is_admin=False,
            scanning_enabled=True,
        )
        app.dependency_overrides[resolve_current_user] = lambda: current
        try:
            get_res = test_client.get("/api/me")
            assert get_res.status_code == 200
            assert get_res.json()["invitation_status"] == "rejected"

            patch_res = test_client.patch(
                "/api/me", json={"pushover_token": "updated-token"}
            )
            assert patch_res.status_code == 200
            assert patch_res.json()["invitation_status"] == "rejected"
        finally:
            app.dependency_overrides.pop(resolve_current_user, None)
