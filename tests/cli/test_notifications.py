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
