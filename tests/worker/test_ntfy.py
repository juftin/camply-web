"""ntfy publishing and durable per-channel delivery."""

import datetime as dt
from unittest.mock import AsyncMock, patch

import httpx2
import pytest
from sqlalchemy import select

from camply.db.config import DatabaseConfig
from camply.db.models import NotificationOutbox, UniqueTarget, User, UserScan
from camply.db.notification_config import ntfy_config as ntfy_defaults
from camply.worker.engine.notifications import send_notification
from camply.worker.engine.scanner import check_target
from camply.worker.notifications.base import NotificationDTO
from camply.worker.notifications.ntfy import NtfyProvider
from camply.worker.outbox import deliver_next

from .test_outbox import fake_provider


@pytest.mark.anyio
@pytest.mark.parametrize("accepted", [True, False])
async def test_publish_custom_server(accepted: bool) -> None:
    """Preserve path prefixes, Unicode and optional auth; validate acceptance."""
    client = AsyncMock()
    client.post.return_value = httpx2.Response(
        200,
        json={
            "id": "synthetic",
            "topic": "camply-test",
            "event": "message" if accepted else "keepalive",
        },
        request=httpx2.Request("POST", "https://push.example.test/prefix/"),
    )
    payload = NotificationDTO(
        park_name="Park",
        campsite_name="Site",
        start_date=dt.date(2027, 1, 1),
        end_date=dt.date(2027, 1, 3),
        title="Campsite ⛺",
        message="Two nights",
        booking_url="https://example.test/results",
    )
    provider = NtfyProvider(client)
    assert provider.provider_id == "ntfy"
    assert (
        await provider.send_accepted(
            {
                "topic": "camply-test",
                "server_url": "https://push.example.test/prefix/",
                "subscription_url": "https://public.example.test/subscribe",
                "access_token": "synthetic",
            },
            payload,
        )
        is accepted
    )
    kwargs = client.post.call_args.kwargs
    assert kwargs["url"] == "https://push.example.test/prefix/"
    assert kwargs["headers"] == {"Authorization": "Bearer synthetic"}
    assert kwargs["json"]["title"] == payload.title
    assert kwargs["json"]["click"] == payload.booking_url
    assert kwargs["follow_redirects"] is False


@pytest.mark.anyio
@pytest.mark.parametrize("custom_server", [None, "https://custom.example.test/push"])
async def test_durable_selected_provider_and_switch(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
    monkeypatch: pytest.MonkeyPatch,
    custom_server: str | None,
) -> None:
    """Only the selected provider sends, and switching cancels old pending delivery."""
    database, target, scan = local_data
    monkeypatch.setattr(
        ntfy_defaults, "subscription_url", "https://public.example.test"
    )
    monkeypatch.setattr(ntfy_defaults, "publish_url", "http://ntfy.internal/push")
    async with database.get_session() as session:
        user = await session.get(User, scan.user_id)
        assert user is not None
        user.notification_provider = "ntfy"
        user.ntfy_server_url = custom_server
        user.ntfy_access_token = "synthetic"
        topic = user.ntfy_topic
        await session.commit()
    await check_target(
        str(target.id),
        sessions=database.get_session,
        registry={1: fake_provider(target)},
        persistent=True,
    )
    async with database.get_session() as session:
        rows = (await session.scalars(select(NotificationOutbox))).all()
        assert {row.channel for row in rows} == {"ntfy"}
        assert all("synthetic" not in str(row.payload) for row in rows)
    pushover = AsyncMock(return_value=True)
    with patch.object(NtfyProvider, "send_accepted", new_callable=AsyncMock) as ntfy:
        ntfy.side_effect = httpx2.ConnectError("synthetic")
        outcomes = [await deliver_next(database, send=pushover)]
        assert {item["outcome"] for item in outcomes if item} == {"retry"}
        assert ntfy.call_args.args[0] == {
            "topic": topic,
            "server_url": custom_server or "http://ntfy.internal/push",
            "access_token": "synthetic",
        }
    pushover.assert_not_awaited()
    async with database.get_session() as session:
        user = await session.get(User, scan.user_id)
        assert user is not None
        user.notification_provider = "pushover"
        row = await session.scalar(
            select(NotificationOutbox).where(NotificationOutbox.channel == "ntfy")
        )
        assert row is not None
        row.next_attempt_at = row.created_at
        await session.commit()
    with patch.object(NtfyProvider, "send_accepted", new_callable=AsyncMock) as ntfy:
        outcome = await deliver_next(database)
        assert outcome and outcome["outcome"] == "skipped"
        ntfy.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("publish_url", [None, "http://ntfy.internal/push"])
async def test_distributed_ntfy_without_pushover(
    local_data: tuple[DatabaseConfig, UniqueTarget, UserScan],
    monkeypatch: pytest.MonkeyPatch,
    publish_url: str | None,
) -> None:
    """ntfy needs no Pushover key and rechecks provider choice before each attempt."""
    database, _, scan = local_data
    monkeypatch.setattr(
        ntfy_defaults, "subscription_url", "https://public.example.test"
    )
    monkeypatch.setattr(ntfy_defaults, "publish_url", publish_url)
    async with database.get_session() as session:
        user = await session.get(User, scan.user_id)
        assert user is not None
        user.notification_provider = "ntfy"
        user.pushover_token = None
        await session.commit()
    payload = NotificationDTO(
        park_name="Park",
        campsite_name="Site",
        start_date=dt.date(2027, 1, 1),
        end_date=dt.date(2027, 1, 3),
        title="Alert",
        message="Opening",
        booking_url="https://example.test",
    ).model_dump(mode="json")
    with patch.object(NtfyProvider, "send_alert", new_callable=AsyncMock) as send:
        result = await send_notification(
            str(scan.user_id),
            payload,
            str(scan.id),
            sessions=database.get_session,
            channel="ntfy",
        )
        assert result["status"] == "success"
        send.assert_awaited_once()
        assert send.call_args.kwargs["user_config"]["server_url"] == (
            publish_url or "https://public.example.test"
        )
        result = await send_notification(
            str(scan.user_id),
            payload,
            str(scan.id),
            sessions=database.get_session,
        )
        assert result["reason"] == "provider_changed"
        send.assert_awaited_once()
        async with database.get_session() as session:
            user = await session.get(User, scan.user_id)
            assert user is not None
            user.scanning_enabled = False
            await session.commit()
        result = await send_notification(
            str(scan.user_id),
            payload,
            str(scan.id),
            sessions=database.get_session,
            channel="ntfy",
        )
        assert result["reason"] == "user_suspended"
        send.assert_awaited_once()
