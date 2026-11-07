"""Authenticated test sends use draft settings without saving them or loading workers."""

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from camply.db.models import User
from camply.db.notification_config import ntfy_config
from camply.notifications.ntfy import NtfyProvider
from camply.notifications.pushover import PushoverProvider
from camply.server.app import app
from camply.server.auth import CurrentUser, resolve_current_user
from camply.server.config import AuthMode, backend_config
from tests.server.conftest import maker

PATH = "/api/me/notifications/test"


@pytest.mark.parametrize("custom_server", [None, "https://custom.example.test/prefix"])
def test_ntfy_draft_send_without_persisting(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch, custom_server: str | None
) -> None:
    monkeypatch.setattr(ntfy_config, "publish_url", "http://ntfy.internal/publish")
    monkeypatch.setattr(ntfy_config, "subscription_url", "https://public.example.test")
    before = test_client.get("/api/me").json()
    with patch.object(
        NtfyProvider, "send_accepted", new_callable=AsyncMock, return_value=True
    ) as send:
        response = test_client.post(
            PATH,
            json={
                "notification_provider": "ntfy",
                "ntfy_topic": "draft-test-topic",
                "ntfy_server_url": custom_server,
                "ntfy_access_token": "synthetic",
            },
        )
    assert response.status_code == 200
    assert response.json() == {"status": "sent", "provider": "ntfy"}
    send.assert_awaited_once()
    assert send.call_args.args[0] == {
        "topic": "draft-test-topic",
        "server_url": custom_server or "http://ntfy.internal/publish",
        "access_token": "synthetic",
    }
    assert send.call_args.args[1].title == "Camply test notification"
    assert send.call_args.args[1].booking_url == ""
    assert test_client.get("/api/me").json() == before
    assert "ntfy.internal" not in response.text


def test_pushover_draft_send(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(PushoverProvider.config, "app_token", "synthetic-app")
    before = test_client.get("/api/me").json()
    with patch.object(
        PushoverProvider, "send_accepted", new_callable=AsyncMock, return_value=True
    ) as send:
        response = test_client.post(
            PATH,
            json={"notification_provider": "pushover", "pushover_token": "draft-key"},
        )
    assert response.status_code == 200
    assert response.json()["provider"] == "pushover"
    send.assert_awaited_once()
    assert send.call_args.args[0] == "draft-key"
    assert test_client.get("/api/me").json() == before


@pytest.mark.parametrize(
    "user_key,app_token,expected", [(None, "app", 400), ("user", "", 503)]
)
def test_missing_pushover_credentials(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    user_key: str | None,
    app_token: str,
    expected: int,
) -> None:
    monkeypatch.setattr(PushoverProvider.config, "app_token", app_token)
    with patch.object(
        PushoverProvider, "send_accepted", new_callable=AsyncMock
    ) as send:
        response = test_client.post(
            PATH, json={"notification_provider": "pushover", "pushover_token": user_key}
        )
    assert response.status_code == expected
    send.assert_not_awaited()


@pytest.mark.parametrize(
    "failure", [False, RuntimeError("http://private.example.test/ synthetic-secret")]
)
def test_failure_does_not_expose_upstream_details(
    test_client: TestClient, failure: bool | Exception
) -> None:
    with patch.object(NtfyProvider, "send_accepted", new_callable=AsyncMock) as send:
        if isinstance(failure, Exception):
            send.side_effect = failure
        else:
            send.return_value = failure
        response = test_client.post(
            PATH, json={"notification_provider": "ntfy", "ntfy_topic": "test-error"}
        )
    assert response.status_code == 502
    assert "private.example.test" not in response.text
    assert "synthetic-secret" not in response.text


@pytest.mark.parametrize("gate", ["suspended", "password", "invite"])
def test_account_eligibility(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch, gate: str
) -> None:
    monkeypatch.setattr(backend_config, "invite_only", gate == "invite")
    user = CurrentUser(
        id=uuid.uuid4(),
        email="guard@example.test",
        is_invited=gate != "invite",
        scanning_enabled=gate != "suspended",
        must_change_password=gate == "password",
    )
    app.dependency_overrides[resolve_current_user] = lambda: user
    try:
        with patch.object(
            NtfyProvider, "send_accepted", new_callable=AsyncMock
        ) as send:
            response = test_client.post(PATH, json={"notification_provider": "ntfy"})
        assert response.status_code == 403
        send.assert_not_awaited()
    finally:
        app.dependency_overrides.pop(resolve_current_user)


def test_authentication_required(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.AUTH0)
    assert (
        test_client.post(PATH, json={"notification_provider": "ntfy"}).status_code
        == 401
    )


def test_cannot_test_a_topic_claimed_by_another_account(
    test_client: TestClient,
) -> None:
    async def seed() -> None:
        async with maker() as session:
            session.add(
                User(
                    email="test-topic-owner@example.test",
                    ntfy_topic="claimed-test-topic",
                )
            )
            await session.commit()

    asyncio.run(seed())
    with patch.object(NtfyProvider, "send_accepted", new_callable=AsyncMock) as send:
        response = test_client.post(
            PATH,
            json={"notification_provider": "ntfy", "ntfy_topic": "claimed-test-topic"},
        )
    assert response.status_code == 409
    send.assert_not_awaited()


@pytest.mark.parametrize(
    "settings", [{"ntfy_topic": "bad/topic"}, {"ntfy_server_url": "ftp://example.test"}]
)
def test_invalid_draft_settings(
    test_client: TestClient, settings: dict[str, str]
) -> None:
    with patch.object(NtfyProvider, "send_accepted", new_callable=AsyncMock) as send:
        response = test_client.post(
            PATH, json={"notification_provider": "ntfy", **settings}
        )
    assert response.status_code == 422
    send.assert_not_awaited()
