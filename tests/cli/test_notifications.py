"""Unit and Click runner tests for stateless CLI notifications and deduplication."""

import asyncio
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from camply.cli.main import cli
from camply.cli.notifications import (
    StayDeduplicationState,
    resolve_notification_config,
    stay_key,
)
from camply.core.search import AvailabilityStay
from camply.notifications.base import NotificationDTO
from camply.notifications.ntfy import NtfyProvider
from camply.notifications.pushover import PushoverProvider
from camply.providers import PROVIDERS
from camply.providers.base import BaseProvider
from camply.providers.dto import CampgroundSearchResult, CampsiteDTO, CampsiteType


def _sample_stay(
    campsite_id: str = "101",
    arrival: date = date(2027, 7, 10),
    checkout: date = date(2027, 7, 12),
) -> AvailabilityStay:
    """Construct a deterministic AvailabilityStay for notification tests."""
    return AvailabilityStay(
        campground=CampgroundSearchResult(
            provider_id=1,
            provider_name="Recreation.gov",
            campground_id="232450",
            campground_name="Lower Pines",
            recreation_area_id="2991",
            recreation_area_name="Yosemite National Park",
            state="CA",
            booking_url="https://www.recreation.gov/camping/campgrounds/232450",
        ),
        campsite_id=campsite_id,
        campsite_name=f"Site {campsite_id}",
        arrival=arrival,
        checkout=checkout,
        booking_url=f"https://www.recreation.gov/camping/campsites/{campsite_id}",
    )


def test_notification_config_resolution_and_secret_redaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolve channels, validate required env credentials, and hide secrets in repr."""
    monkeypatch.setenv("PUSHOVER_USER_KEY", "malformed-user-secret")
    monkeypatch.setenv("PUSHOVER_APP_TOKEN", "")
    # No channels selected: env vars are ignored completely
    empty = resolve_notification_config(())
    assert empty.channels == ()
    assert empty.pushover_user_key is None

    # Pushover requires both PUSHOVER_USER_KEY and PUSHOVER_APP_TOKEN
    with pytest.raises(ValueError, match="PUSHOVER_APP_TOKEN"):
        resolve_notification_config(("pushover",))

    monkeypatch.setenv("PUSHOVER_APP_TOKEN", "super-secret-app-token")
    pushover_cfg = resolve_notification_config(("Pushover", "pushover"))
    assert pushover_cfg.channels == ("pushover",)
    assert "super-secret-app-token" not in repr(pushover_cfg)
    assert "malformed-user-secret" not in repr(pushover_cfg)

    # ntfy requires valid NTFY_TOPIC and HTTP(S) NTFY_SERVER_URL
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    monkeypatch.delenv("NTFY_SERVER_URL", raising=False)
    monkeypatch.delenv("NTFY_ACCESS_TOKEN", raising=False)
    with pytest.raises(ValueError, match="NTFY_TOPIC"):
        resolve_notification_config(("ntfy",))

    monkeypatch.setenv("NTFY_TOPIC", "invalid topic spaces!")
    with pytest.raises(ValueError, match="NTFY_TOPIC"):
        resolve_notification_config(("ntfy",))

    monkeypatch.setenv("NTFY_TOPIC", "camply-topic")
    monkeypatch.setenv("NTFY_SERVER_URL", "ftp://bad.example")
    with pytest.raises(ValueError, match="HTTP"):
        resolve_notification_config(("ntfy",))

    monkeypatch.setenv("NTFY_SERVER_URL", "")
    monkeypatch.setenv("NTFY_ACCESS_TOKEN", "bad\ncontrol")
    with pytest.raises(ValueError, match="printable ASCII"):
        resolve_notification_config(("ntfy",))

    monkeypatch.setenv("NTFY_ACCESS_TOKEN", "tk_secret_ntfy_token")
    monkeypatch.setenv("NTFY_TOPIC", "env-topic")
    monkeypatch.setenv("NTFY_SERVER_URL", "https://ntfy.example.com/")
    ntfy_cfg = resolve_notification_config(("ntfy",))
    assert ntfy_cfg.ntfy_topic == "env-topic"
    assert ntfy_cfg.ntfy_server_url == "https://ntfy.example.com"
    assert "tk_secret_ntfy_token" not in repr(ntfy_cfg)


def test_stay_deduplication_in_memory_and_state_file(tmp_path: Path) -> None:
    """Suppress unchanged openings, re-alert on reopened stays, and persist state."""
    stay_a = _sample_stay("101")
    stay_b = _sample_stay("102")
    assert stay_key(stay_a) == "1:232450:101:2027-07-10:2027-07-12"

    state_path = tmp_path / "seen.json"
    state = StayDeduplicationState.load(state_path)

    # Cycle 1: stay_a opens -> alerts and persists to file
    assert state.record_cycle([stay_a]) == [stay_a]
    assert state_path.is_file()

    # Cycle 2 (new process loading same state file): stay_a still open, stay_b opens
    reloaded = StayDeduplicationState.load(state_path)
    assert reloaded.record_cycle([stay_a, stay_b]) == [stay_b]

    # Cycle 3: stay_a closes, stay_b remains open -> no new alerts
    assert reloaded.record_cycle([stay_b]) == []

    # Cycle 4: stay_a reopens -> alerts on stay_a only
    assert reloaded.record_cycle([stay_a, stay_b]) == [stay_a]

    # Corrupted state file logs warning and recovers with empty state
    state_path.write_text("{not-valid-json")
    recovered = StayDeduplicationState.load(state_path)
    assert recovered.record_cycle([stay_a]) == [stay_a]


def test_test_notifications_command_success_and_sanitized_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify camply test-notifications dispatches to selected channels and redacts secrets."""
    monkeypatch.setenv("PUSHOVER_USER_KEY", "user-secret-123")
    monkeypatch.setenv("PUSHOVER_APP_TOKEN", "app-secret-456")
    monkeypatch.setenv("NTFY_TOPIC", "camply-test")
    monkeypatch.setenv("NTFY_ACCESS_TOKEN", "ntfy-secret-789")

    pushover_calls: list[tuple[str, NotificationDTO]] = []
    ntfy_calls: list[tuple[dict[str, object], NotificationDTO]] = []

    async def fake_pushover(
        self: PushoverProvider, user_key: str, payload: NotificationDTO
    ) -> bool:
        pushover_calls.append((user_key, payload))
        return True

    async def fake_ntfy(
        self: NtfyProvider, config: dict[str, object], payload: NotificationDTO
    ) -> bool:
        ntfy_calls.append((config, payload))
        return True

    monkeypatch.setattr(PushoverProvider, "send_accepted", fake_pushover)
    monkeypatch.setattr(NtfyProvider, "send_accepted", fake_ntfy)

    result = CliRunner().invoke(
        cli,
        [
            "test-notifications",
            "--notifications",
            "pushover",
            "--notifications",
            "ntfy",
        ],
    )
    assert result.exit_code == 0, result.output
    assert len(pushover_calls) == 1
    assert len(ntfy_calls) == 1
    assert ntfy_calls[0][0]["topic"] == "camply-test"
    assert "user-secret-123" not in result.output
    assert "app-secret-456" not in result.output
    assert "ntfy-secret-789" not in result.output

    # Simulate upstream failure containing secret tokens in exception message
    async def failing_pushover(
        self: PushoverProvider, user_key: str, payload: NotificationDTO
    ) -> bool:
        raise RuntimeError("Upstream error for user-secret-123 and app-secret-456")

    monkeypatch.setattr(PushoverProvider, "send_accepted", failing_pushover)
    failed = CliRunner().invoke(
        cli, ["test-notifications", "--notifications", "pushover"]
    )
    assert failed.exit_code == 1
    assert "Could not send pushover notification (RuntimeError)" in failed.stderr
    assert "user-secret-123" not in failed.output + failed.stderr
    assert "app-secret-456" not in failed.output + failed.stderr


def test_campsites_notifications_deduplicate_and_survive_transient_delivery_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify camply campsites sends deduplicated alerts and survives delivery errors."""
    from camply.core import search as core

    monkeypatch.setattr(core, "POLL_INTERVAL_SECONDS", 0.0001)
    monkeypatch.setattr(core, "utc_today", lambda: date(2027, 7, 1))
    monkeypatch.setenv("NTFY_TOPIC", "camply-alerts")
    monkeypatch.setenv("NTFY_ACCESS_TOKEN", "ntfy-secret-xyz")

    provider_cls = PROVIDERS[1]
    monkeypatch.setattr(
        provider_cls,
        "__init__",
        lambda self: setattr(self, "async_client", AsyncMock()),
    )

    async def lookup(_: BaseProvider, identifier: str) -> CampgroundSearchResult:
        return _sample_stay().campground

    cycles = [
        # Cycle 1: Site 101 open
        [
            CampsiteDTO(
                campsite_id="101",
                campsite_name="Site 101",
                campsite_type=CampsiteType.TENT,
                capacity=4,
                available_dates=[date(2027, 7, 10), date(2027, 7, 11)],
                is_electric=False,
                is_accessible=False,
            )
        ],
        # Cycle 2: Site 101 still open (unchanged -> should not re-notify)
        [
            CampsiteDTO(
                campsite_id="101",
                campsite_name="Site 101",
                campsite_type=CampsiteType.TENT,
                capacity=4,
                available_dates=[date(2027, 7, 10), date(2027, 7, 11)],
                is_electric=False,
                is_accessible=False,
            )
        ],
        # Cycle 3: Empty (Site 101 closes)
        [],
        # Cycle 4: Site 101 reopens -> should notify again!
        [
            CampsiteDTO(
                campsite_id="101",
                campsite_name="Site 101",
                campsite_type=CampsiteType.TENT,
                capacity=4,
                available_dates=[date(2027, 7, 10), date(2027, 7, 11)],
                is_electric=False,
                is_accessible=False,
            )
        ],
    ]
    call_idx = 0

    async def find_availabilities(
        _: BaseProvider, identifier: str, start: date, end: date
    ) -> list[CampsiteDTO]:
        nonlocal call_idx
        if call_idx >= len(cycles):
            raise asyncio.CancelledError
        data = cycles[call_idx]
        call_idx += 1
        return data

    monkeypatch.setattr(provider_cls, "get_campground", lookup)
    monkeypatch.setattr(provider_cls, "find_availabilities", find_availabilities)

    sent_alerts: list[NotificationDTO] = []

    async def fake_ntfy(
        self: NtfyProvider, config: dict[str, object], payload: NotificationDTO
    ) -> bool:
        sent_alerts.append(payload)
        if len(sent_alerts) == 1:
            # Simulate a transient delivery error on the first alert to prove
            # monitoring continues and redacts tokens
            raise RuntimeError("Transient error with token ntfy-secret-xyz")
        return True

    monkeypatch.setattr(NtfyProvider, "send_accepted", fake_ntfy)

    state_file = tmp_path / "watch-state.json"
    result = CliRunner().invoke(
        cli,
        [
            "campsites",
            "--campground",
            "232450",
            "--start-date",
            "2027-07-10",
            "--end-date",
            "2027-07-12",
            "--nights",
            "2",
            "--notifications",
            "ntfy",
            "--state-file",
            str(state_file),
        ],
    )
    assert result.exit_code == 1  # Cancelled after 4 cycles
    # Alert attempted on Cycle 1 (newly opened) and Cycle 4 (reopened), skipped on Cycle 2
    assert len(sent_alerts) == 2
    assert "ntfy-secret-xyz" not in result.output + result.stderr
    assert state_file.is_file()


def test_extra_notification_channels_config_and_secret_redaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate env vars and secret redaction for webhook, discord, slack, and telegram."""
    for var in (
        "WEBHOOK_URL",
        "WEBHOOK_HEADERS",
        "DISCORD_WEBHOOK_URL",
        "SLACK_WEBHOOK_URL",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ):
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError, match="WEBHOOK_URL"):
        resolve_notification_config(("webhook",))
    with pytest.raises(ValueError, match="DISCORD_WEBHOOK_URL"):
        resolve_notification_config(("discord",))
    with pytest.raises(ValueError, match="SLACK_WEBHOOK_URL"):
        resolve_notification_config(("slack",))
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        resolve_notification_config(("telegram",))

    monkeypatch.setenv("WEBHOOK_URL", "https://hooks.example.test/secret-hook")
    monkeypatch.setenv("WEBHOOK_HEADERS", "not-json")
    with pytest.raises(ValueError, match="WEBHOOK_HEADERS"):
        resolve_notification_config(("webhook",))

    monkeypatch.setenv(
        "WEBHOOK_HEADERS", '{"Authorization": "Bearer secret-webhook-token"}'
    )
    monkeypatch.setenv(
        "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/secret-discord"
    )
    monkeypatch.setenv(
        "SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/secret-slack"
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:secret-telegram-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100999")

    cfg = resolve_notification_config(("webhook", "discord", "slack", "telegram"))
    assert cfg.channels == ("webhook", "discord", "slack", "telegram")
    assert cfg.webhook_headers == {"Authorization": "Bearer secret-webhook-token"}
    text = repr(cfg)
    for secret in (
        "secret-hook",
        "secret-webhook-token",
        "secret-discord",
        "secret-slack",
        "secret-telegram-token",
    ):
        assert secret not in text


@pytest.mark.asyncio
async def test_extra_notification_providers_http_contracts() -> None:
    """Verify HTTP request payloads and acceptance checks for webhook, discord, slack, and telegram."""
    import json

    import httpx2

    from camply.notifications.discord import DiscordProvider
    from camply.notifications.slack import SlackProvider
    from camply.notifications.telegram import TelegramProvider
    from camply.notifications.webhook import WebhookProvider

    payload = NotificationDTO(
        title="⛺ Lower Pines (2027-07-10)",
        message="Site 101 available.",
        booking_url="https://www.recreation.gov/camping/campsites/101",
        url_title="Book Campsite",
        park_name="Yosemite National Park - Lower Pines",
        campsite_name="Site 101",
        start_date=date(2027, 7, 10),
        end_date=date(2027, 7, 12),
    )

    recorded: list[tuple[str, dict[str, str], dict[str, object]]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        recorded.append((str(request.url), dict(request.headers), body))
        if "api.telegram.org" in str(request.url):
            return httpx2.Response(200, json={"ok": True, "result": {"message_id": 1}})
        if "discord.com" in str(request.url):
            return httpx2.Response(204)
        return httpx2.Response(200, text="ok")

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
        assert await WebhookProvider(client).send_accepted(
            {
                "url": "https://hooks.example.test/camply",
                "headers": {"X-Camply-Auth": "secret-hdr"},
            },
            payload,
        )
        assert await DiscordProvider(client).send_accepted(
            {"webhook_url": "https://discord.com/api/webhooks/1/tok"}, payload
        )
        assert await SlackProvider(client).send_accepted(
            {"webhook_url": "https://hooks.slack.com/services/T/B/X"}, payload
        )
        assert await TelegramProvider(client).send_accepted(
            {"bot_token": "123:abc", "chat_id": "42"}, payload
        )

    assert len(recorded) == 4
    # Webhook
    assert recorded[0][0] == "https://hooks.example.test/camply"
    assert recorded[0][1]["x-camply-auth"] == "secret-hdr"
    assert recorded[0][2]["campsite_name"] == "Site 101"
    assert recorded[0][2]["start_date"] == "2027-07-10"
    assert "timestamp" in recorded[0][2]
    # Discord
    embeds = recorded[1][2]["embeds"]
    assert isinstance(embeds, list)
    assert embeds[0]["url"] == payload.booking_url
    # Slack
    assert payload.booking_url in str(recorded[2][2]["text"])
    # Telegram
    assert recorded[3][0] == "https://api.telegram.org/bot123:abc/sendMessage"
    assert recorded[3][2]["chat_id"] == "42"


@pytest.mark.asyncio
async def test_notification_cap_and_overflow_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce max_notifications per cycle and collapse overflow stays into one summary alert."""
    from camply.cli.notifications import send_stay_notifications

    monkeypatch.setenv("NTFY_TOPIC", "camply-cap")
    config = resolve_notification_config(("ntfy",))
    stays = [_sample_stay(f"10{i}") for i in range(1, 9)]  # 8 stays

    sent: list[NotificationDTO] = []

    async def fake_ntfy(
        self: NtfyProvider, cfg: dict[str, object], payload: NotificationDTO
    ) -> bool:
        sent.append(payload)
        return True

    monkeypatch.setattr(NtfyProvider, "send_accepted", fake_ntfy)

    # Default cap = 5 -> 4 direct + 1 summary = 5 total notifications
    await send_stay_notifications(config, stays, max_notifications=5)
    assert len(sent) == 5
    assert sent[0].campsite_name == "Site 101"
    assert sent[3].campsite_name == "Site 104"
    assert "+4 more stays available" in sent[4].title
    assert sent[4].metadata == {"summary": True, "stay_count": 4}

    # Digest mode cap = 1 -> 1 summary notification covering all 8 stays
    sent.clear()
    await send_stay_notifications(config, stays, max_notifications=1)
    assert len(sent) == 1
    assert "8 stays available" in sent[0].title
    assert sent[0].metadata == {"summary": True, "stay_count": 8}

    # Within cap -> all individual direct alerts
    sent.clear()
    await send_stay_notifications(config, stays[:3], max_notifications=5)
    assert len(sent) == 3
    assert all(not item.metadata.get("summary") for item in sent)


def test_campsites_max_notifications_cli_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify --max-notifications validates 1..100 before provider IO."""
    for bad in ("0", "-1", "101"):
        res = CliRunner().invoke(
            cli,
            [
                "campsites",
                "--campground",
                "232450",
                "--start-date",
                "2027-07-10",
                "--end-date",
                "2027-07-12",
                "--max-notifications",
                bad,
            ],
        )
        assert res.exit_code == 2


def test_notification_preflight_hardening_and_edge_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject malformed ports, embedded credentials, bad webhook headers, and unsafe Telegram tokens."""
    monkeypatch.setenv("WEBHOOK_URL", "https://hooks.example.test:notaport/x")
    with pytest.raises(ValueError, match="valid port"):
        resolve_notification_config(("webhook",))

    monkeypatch.setenv("WEBHOOK_URL", "https://user:pass@hooks.example.test/x")
    with pytest.raises(ValueError, match="embedded credentials"):
        resolve_notification_config(("webhook",))

    monkeypatch.setenv("WEBHOOK_URL", "https://hooks.example.test/x")
    for bad_headers in (
        '{"Bad Header": "value"}',
        '{"X-Foo:Bar": "value"}',
        '{"Host": "evil.example"}',
        '["not-an-object"]',
    ):
        monkeypatch.setenv("WEBHOOK_HEADERS", bad_headers)
        with pytest.raises(ValueError, match="WEBHOOK_HEADERS"):
            resolve_notification_config(("webhook",))

    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    for bad_token in ("123:abc/evil", "123:abc%2f..", "123:abc\\evil", "123:abc@host"):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", bad_token)
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            resolve_notification_config(("telegram",))


@pytest.mark.asyncio
async def test_extra_providers_rejection_escaping_and_clamping() -> None:
    """Verify non-acceptance, mrkdwn escaping, Discord field clamping, and invalid Telegram token."""
    import json

    import httpx2

    from camply.notifications.discord import DiscordProvider
    from camply.notifications.slack import SlackProvider
    from camply.notifications.telegram import TelegramProvider
    from camply.notifications.webhook import WebhookProvider

    edge_payload = NotificationDTO(
        title="A < B & C > D",
        message="Msg <tag> & details",
        booking_url="https://example.invalid/site/1",
        url_title="Book | Now",
        park_name="",
        campsite_name="X" * 1200,
        start_date=date(2027, 7, 10),
        end_date=date(2027, 7, 12),
    )

    bodies: list[dict[str, object]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        bodies.append(json.loads(request.content))
        url = str(request.url)
        if "redirect" in url:
            return httpx2.Response(302, headers={"Location": "https://other.invalid"})
        if "telegram" in url:
            return httpx2.Response(200, json={"ok": False, "description": "bad chat"})
        return httpx2.Response(200, text="ok")

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
        assert await DiscordProvider(client).send_accepted(
            {"webhook_url": "https://discord.com/api/webhooks/1/tok"}, edge_payload
        )
        assert await SlackProvider(client).send_accepted(
            {"webhook_url": "https://hooks.slack.com/services/T/B/X"}, edge_payload
        )
        assert not await TelegramProvider(client).send_accepted(
            {"bot_token": "123:abc", "chat_id": "42"}, edge_payload
        )
        with pytest.raises(httpx2.HTTPStatusError):
            await WebhookProvider(client).send_accepted(
                {"url": "https://redirect.example.invalid/hook"}, edge_payload
            )
        with pytest.raises(ValueError, match="Invalid Telegram bot token"):
            await TelegramProvider(client).send_accepted(
                {"bot_token": "123:abc/../evil", "chat_id": "42"}, edge_payload
            )

    discord_embed = bodies[0]["embeds"]
    assert isinstance(discord_embed, list)
    fields = discord_embed[0]["fields"]
    assert fields[0]["value"] == "-"
    assert len(fields[1]["value"]) == 1024
    assert fields[1]["value"].endswith("…")

    slack_text = str(bodies[1]["text"])
    assert "A &lt; B &amp; C &gt; D" in slack_text
    assert "<https://example.invalid/site/1|Book / Now>" in slack_text


@pytest.mark.asyncio
async def test_overflow_summary_multi_campground_and_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify overflow summary labels across 1/2/3 campgrounds, single-stay cap=1, and cap<1 guard."""
    from camply.cli.notifications import send_stay_notifications

    monkeypatch.setenv("NTFY_TOPIC", "camply-summary")
    config = resolve_notification_config(("ntfy",))
    sent: list[NotificationDTO] = []

    async def fake_ntfy(
        self: NtfyProvider, cfg: dict[str, object], payload: NotificationDTO
    ) -> bool:
        sent.append(payload)
        return True

    monkeypatch.setattr(NtfyProvider, "send_accepted", fake_ntfy)

    with pytest.raises(ValueError, match="at least 1"):
        await send_stay_notifications(config, [_sample_stay("1")], max_notifications=0)

    # max_notifications=1 with exactly 1 stay -> direct alert, not summary
    await send_stay_notifications(config, [_sample_stay("1")], max_notifications=1)
    assert len(sent) == 1
    assert not sent[0].metadata.get("summary")

    # 2 distinct campgrounds -> "Camp A and Camp B"
    stay_a = _sample_stay("1")
    stay_b = stay_a.model_copy(
        update={
            "campsite_id": "2",
            "campground": stay_a.campground.model_copy(
                update={"campground_id": "2", "campground_name": "Upper Pines"}
            ),
        }
    )
    stay_c = stay_a.model_copy(
        update={
            "campsite_id": "3",
            "campground": stay_a.campground.model_copy(
                update={"campground_id": "3", "campground_name": "North Pines"}
            ),
        }
    )
    sent.clear()
    await send_stay_notifications(config, [stay_a, stay_b], max_notifications=1)
    assert "Lower Pines and Upper Pines" in sent[0].title

    sent.clear()
    await send_stay_notifications(config, [stay_a, stay_b, stay_c], max_notifications=1)
    assert "Lower Pines +2 more" in sent[0].title


def test_deduplication_survives_transient_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient provider failure between open cycles does not trigger a duplicate alert."""
    from camply.core import search as core

    monkeypatch.setattr(core, "POLL_INTERVAL_SECONDS", 0.0001)
    monkeypatch.setattr(core, "utc_today", lambda: date(2027, 7, 1))
    monkeypatch.setenv("NTFY_TOPIC", "camply-retry-dedup")

    provider_cls = PROVIDERS[1]
    monkeypatch.setattr(
        provider_cls,
        "__init__",
        lambda self: setattr(self, "async_client", AsyncMock()),
    )
    monkeypatch.setattr(
        provider_cls,
        "get_campground",
        AsyncMock(return_value=_sample_stay().campground),
    )

    open_site = [
        CampsiteDTO(
            campsite_id="101",
            campsite_name="Site 101",
            campsite_type=CampsiteType.TENT,
            capacity=4,
            available_dates=[date(2027, 7, 10), date(2027, 7, 11)],
            is_electric=False,
            is_accessible=False,
        )
    ]
    step = 0

    async def flaky_cycles(*_args: object) -> list[CampsiteDTO]:
        nonlocal step
        step += 1
        if step == 1:
            return open_site
        if step == 2:
            raise RuntimeError("transient outage")
        if step == 3:
            return open_site
        raise asyncio.CancelledError

    monkeypatch.setattr(provider_cls, "find_availabilities", flaky_cycles)
    sent: list[NotificationDTO] = []

    async def fake_ntfy(
        self: NtfyProvider, cfg: dict[str, object], payload: NotificationDTO
    ) -> bool:
        sent.append(payload)
        return True

    monkeypatch.setattr(NtfyProvider, "send_accepted", fake_ntfy)
    result = CliRunner().invoke(
        cli,
        [
            "campsites",
            "--campground",
            "232450",
            "--start-date",
            "2027-07-10",
            "--end-date",
            "2027-07-12",
            "--nights",
            "2",
            "--notifications",
            "ntfy",
        ],
    )
    assert result.exit_code == 1
    assert step == 4
    assert len(sent) == 1
    assert "Provider request failed (RuntimeError); retrying" in result.stderr
