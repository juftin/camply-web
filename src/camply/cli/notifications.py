"""Stateless CLI notification configuration, deduplication, capping, and delivery."""

import json
import os
import re
import stat
import tempfile
from collections.abc import Sequence
from contextlib import suppress
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast
from urllib.parse import urlsplit

import click
from pydantic import BaseModel, ConfigDict, Field

from camply.cli import options
from camply.cli.execution import run
from camply.cli.options import resolve_debug
from camply.cli.output import diagnostic, logger, stay_booking_url
from camply.core.search import utc_today
from camply.db.notification_config import validate_ntfy_url
from camply.notifications.base import NotificationDTO
from camply.notifications.discord import DiscordProvider
from camply.notifications.ntfy import NtfyProvider
from camply.notifications.pushover import PushoverProvider
from camply.notifications.slack import SlackProvider
from camply.notifications.telegram import TelegramProvider
from camply.notifications.webhook import WebhookProvider

if TYPE_CHECKING:
    from camply.core.search import AvailabilityStay

ChannelName = Literal["pushover", "ntfy", "webhook", "discord", "slack", "telegram"]
SUPPORTED_CHANNELS: tuple[ChannelName, ...] = (
    "pushover",
    "ntfy",
    "webhook",
    "discord",
    "slack",
    "telegram",
)
DEFAULT_MAX_NOTIFICATIONS = 5
MAX_NOTIFICATIONS_LIMIT = 100
_NTFY_TOPIC_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_HTTP_HEADER_NAME_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_FORBIDDEN_WEBHOOK_HEADERS = frozenset(
    {"host", "content-length", "transfer-encoding", "connection"}
)
_TELEGRAM_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9:_-]+$")
_DEFAULT_NTFY_SERVER = "https://ntfy.sh"


class CLINotificationConfig(BaseModel):
    """Validated CLI notification channels and redacted credentials."""

    model_config = ConfigDict(frozen=True)

    channels: tuple[ChannelName, ...] = ()
    pushover_user_key: str | None = Field(default=None, repr=False)
    pushover_app_token: str | None = Field(default=None, repr=False)
    ntfy_topic: str | None = None
    ntfy_server_url: str = _DEFAULT_NTFY_SERVER
    ntfy_access_token: str | None = Field(default=None, repr=False)
    webhook_url: str | None = Field(default=None, repr=False)
    webhook_headers: dict[str, str] = Field(default_factory=dict, repr=False)
    discord_webhook_url: str | None = Field(default=None, repr=False)
    slack_webhook_url: str | None = Field(default=None, repr=False)
    telegram_bot_token: str | None = Field(default=None, repr=False)
    telegram_chat_id: str | None = None


def _validate_http_url(raw: str, env_name: str) -> str:
    """Validate an HTTP(S) webhook URL without embedded userinfo, invalid ports, or whitespace."""
    value = raw.strip()
    if not value or any(ch.isspace() or not ch.isprintable() for ch in value):
        raise ValueError(f"{env_name} must be a valid HTTP(S) URL.")
    parsed = urlsplit(value)
    try:
        _ = parsed.port
    except ValueError:
        raise ValueError(
            f"{env_name} must be a valid HTTP(S) URL with a valid port."
        ) from None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(
            f"{env_name} must be a valid HTTP(S) URL without embedded credentials."
        )
    return value


def _resolve_pushover_credentials() -> tuple[str, str]:
    """Read and validate Pushover user and application tokens from the environment."""
    user_key = os.environ.get("PUSHOVER_USER_KEY", "").strip()
    app_token = os.environ.get("PUSHOVER_APP_TOKEN", "").strip()
    missing = [
        name
        for name, val in (
            ("PUSHOVER_USER_KEY", user_key),
            ("PUSHOVER_APP_TOKEN", app_token),
        )
        if not val
    ]
    if missing:
        raise ValueError(
            f"Pushover notifications require {', '.join(missing)} environment variable(s)."
        )
    return user_key, app_token


def _resolve_ntfy_settings() -> tuple[str, str, str | None]:
    """Resolve and validate ntfy topic, server URL, and optional access token from env vars."""
    raw_topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not raw_topic or _NTFY_TOPIC_PATTERN.fullmatch(raw_topic) is None:
        raise ValueError(
            "ntfy notifications require a valid NTFY_TOPIC environment variable (1-64 letters, digits, '_' or '-')."
        )
    raw_server = os.environ.get("NTFY_SERVER_URL", "").strip()
    try:
        server_url = (
            validate_ntfy_url(raw_server) if raw_server else _DEFAULT_NTFY_SERVER
        )
    except ValueError:
        raise ValueError(
            "NTFY_SERVER_URL must be a valid HTTP(S) server URL without credentials, query or fragment."
        ) from None
    raw_token = os.environ.get("NTFY_ACCESS_TOKEN", "")
    if raw_token and any(
        not char.isprintable() or not char.isascii() for char in raw_token
    ):
        raise ValueError("NTFY_ACCESS_TOKEN must contain printable ASCII characters.")
    return raw_topic, server_url, raw_token or None


def _resolve_webhook_settings() -> tuple[str, dict[str, str]]:
    """Resolve and validate generic webhook URL and optional JSON headers."""
    raw_url = os.environ.get("WEBHOOK_URL", "").strip()
    if not raw_url:
        raise ValueError(
            "Webhook notifications require the WEBHOOK_URL environment variable."
        )
    url = _validate_http_url(raw_url, "WEBHOOK_URL")
    raw_headers = os.environ.get("WEBHOOK_HEADERS", "").strip()
    if not raw_headers:
        return url, {}
    try:
        parsed = json.loads(raw_headers)
    except ValueError:
        raise ValueError(
            "WEBHOOK_HEADERS must be a valid JSON object of header names and values."
        ) from None
    if not isinstance(parsed, dict):
        raise ValueError(
            "WEBHOOK_HEADERS must be a valid JSON object of header names and values."
        )
    headers: dict[str, str] = {}
    for key, val in parsed.items():
        if not isinstance(key, str) or not isinstance(val, str):
            raise ValueError(
                "WEBHOOK_HEADERS must map valid HTTP header names to printable ASCII values."
            )
        header_name = key.strip()
        if (
            _HTTP_HEADER_NAME_PATTERN.fullmatch(header_name) is None
            or header_name.lower() in _FORBIDDEN_WEBHOOK_HEADERS
            or any(not ch.isprintable() or not ch.isascii() for ch in val)
        ):
            raise ValueError(
                "WEBHOOK_HEADERS must map valid HTTP header names to printable ASCII values."
            )
        headers[header_name] = val
    return url, headers


def _resolve_discord_webhook() -> str:
    """Resolve and validate the Discord webhook URL from the environment."""
    raw_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not raw_url:
        raise ValueError(
            "Discord notifications require the DISCORD_WEBHOOK_URL environment variable."
        )
    return _validate_http_url(raw_url, "DISCORD_WEBHOOK_URL")


def _resolve_slack_webhook() -> str:
    """Resolve and validate the Slack incoming webhook URL from the environment."""
    raw_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not raw_url:
        raise ValueError(
            "Slack notifications require the SLACK_WEBHOOK_URL environment variable."
        )
    return _validate_http_url(raw_url, "SLACK_WEBHOOK_URL")


def _resolve_telegram_settings() -> tuple[str, str]:
    """Resolve and validate Telegram Bot API credentials from the environment."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    missing = [
        name
        for name, val in (
            ("TELEGRAM_BOT_TOKEN", bot_token),
            ("TELEGRAM_CHAT_ID", chat_id),
        )
        if not val
    ]
    if missing:
        raise ValueError(
            f"Telegram notifications require {', '.join(missing)} environment variable(s)."
        )
    if _TELEGRAM_TOKEN_PATTERN.fullmatch(bot_token) is None:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN must contain only letters, digits, ':', '_', or '-'."
        )
    return bot_token, chat_id


def resolve_notification_config(
    channels: Sequence[str],
) -> CLINotificationConfig:
    """Resolve and validate CLI notification settings without database access.

    When ``channels`` is empty, environment variables are not read or validated.
    """
    normalized: list[ChannelName] = []
    for raw in channels:
        key = raw.strip().lower()
        if key not in SUPPORTED_CHANNELS:
            choices = ", ".join(f"'{name}'" for name in SUPPORTED_CHANNELS)
            raise ValueError(f"Unsupported notification channel; choose {choices}.")
        channel = cast(ChannelName, key)
        if channel not in normalized:
            normalized.append(channel)

    if not normalized:
        return CLINotificationConfig()

    user_key, app_token = (
        _resolve_pushover_credentials() if "pushover" in normalized else (None, None)
    )
    topic, server_url, access_token = (
        _resolve_ntfy_settings()
        if "ntfy" in normalized
        else (None, _DEFAULT_NTFY_SERVER, None)
    )
    webhook_url, webhook_headers = (
        _resolve_webhook_settings() if "webhook" in normalized else (None, {})
    )
    discord_url = _resolve_discord_webhook() if "discord" in normalized else None
    slack_url = _resolve_slack_webhook() if "slack" in normalized else None
    telegram_token, telegram_chat_id = (
        _resolve_telegram_settings() if "telegram" in normalized else (None, None)
    )

    return CLINotificationConfig(
        channels=tuple(normalized),
        pushover_user_key=user_key,
        pushover_app_token=app_token,
        ntfy_topic=topic,
        ntfy_server_url=server_url,
        ntfy_access_token=access_token,
        webhook_url=webhook_url,
        webhook_headers=webhook_headers,
        discord_webhook_url=discord_url,
        slack_webhook_url=slack_url,
        telegram_bot_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
    )


def stay_key(stay: "AvailabilityStay") -> str:
    """Return the canonical deduplication key for a qualifying stay."""
    return (
        f"{stay.campground.provider_id}:"
        f"{stay.campground.campground_id}:"
        f"{stay.campsite_id}:"
        f"{stay.arrival.isoformat()}:"
        f"{stay.checkout.isoformat()}"
    )


class _NonRegularStateFileError(OSError):
    """A configured state path points to a special file or directory."""


def _require_regular_state_file(mode: int) -> None:
    if not stat.S_ISREG(mode):
        raise _NonRegularStateFileError("State path must point to a regular file.")


class StayDeduplicationState:
    """Track seen stay keys across poll cycles and optional JSON state-file persistence."""

    def __init__(
        self,
        seen: set[str] | None = None,
        *,
        state_file: Path | None = None,
        label: str | None = None,
    ) -> None:
        self.seen: set[str] = set(seen) if seen else set()
        self.state_file = state_file
        self.label = label

    @classmethod
    def load(
        cls, state_file: Path | None = None, *, label: str | None = None
    ) -> "StayDeduplicationState":
        """Load initial seen stays from ``state_file`` if present, recovering on corruption."""
        if state_file is None:
            return cls(label=label)
        try:
            _require_regular_state_file(state_file.stat().st_mode)
            # A path can change after stat. Open without waiting for a FIFO writer
            # and check the actual descriptor before reading any data.
            flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
            descriptor = os.open(state_file, flags)
            try:
                _require_regular_state_file(os.fstat(descriptor).st_mode)
                with os.fdopen(descriptor, encoding="utf-8", closefd=False) as stream:
                    payload = json.load(stream)
            finally:
                os.close(descriptor)
            entries = payload.get("seen_stays") if isinstance(payload, dict) else None
            if not isinstance(entries, list) or not all(
                isinstance(item, str) for item in entries
            ):
                raise ValueError("Invalid state file schema")
            return cls(seen=set(entries), state_file=state_file, label=label)
        except FileNotFoundError:
            return cls(state_file=state_file, label=label)
        except Exception as exc:
            logger.warning(
                "%sWarning: Could not read state file%s (%s); starting with empty state.",
                f"{label}: " if label else "",
                "" if label else f" {state_file}",
                type(exc).__name__,
            )
            if isinstance(exc, _NonRegularStateFileError):
                state_file = None
            return cls(state_file=state_file, label=label)

    def record_cycle(
        self, stays: Sequence["AvailabilityStay"]
    ) -> list["AvailabilityStay"]:
        """Return newly opened or reopened stays and update seen state after a successful check."""
        new_stays = [stay for stay in stays if stay_key(stay) not in self.seen]
        self.seen = {stay_key(stay) for stay in stays}
        if self.state_file is not None:
            self._save()
        return new_stays

    def _save(self) -> None:
        """Atomically persist the current seen stay set to ``self.state_file``."""
        if self.state_file is None:
            return
        temp_path = None
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(
                {"version": 1, "seen_stays": sorted(self.seen)},
                indent=2,
                sort_keys=True,
            )
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=str(self.state_file.parent),
                delete=False,
                prefix=".camply-state-",
                suffix=".tmp",
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(content)
            with suppress(FileNotFoundError):
                _require_regular_state_file(self.state_file.stat().st_mode)
            temp_path.replace(self.state_file)
            temp_path = None
        except OSError as exc:
            logger.warning(
                "%sWarning: Could not write state file%s (%s).",
                f"{self.label}: " if self.label else "",
                "" if self.label else f" {self.state_file}",
                type(exc).__name__,
            )
            if isinstance(exc, _NonRegularStateFileError):
                self.state_file = None
        finally:
            if temp_path is not None:
                with suppress(OSError):
                    temp_path.unlink(missing_ok=True)


async def _send_to_channel(
    channel: ChannelName,
    config: CLINotificationConfig,
    payload: NotificationDTO,
) -> bool:
    """Dispatch ``payload`` to one configured channel and return upstream acceptance."""
    if channel == "pushover":
        assert config.pushover_user_key is not None
        assert config.pushover_app_token is not None
        PushoverProvider.config.app_token = config.pushover_app_token
        return await PushoverProvider().send_accepted(config.pushover_user_key, payload)
    if channel == "ntfy":
        assert config.ntfy_topic is not None
        return await NtfyProvider().send_accepted(
            {
                "topic": config.ntfy_topic,
                "server_url": config.ntfy_server_url,
                "access_token": config.ntfy_access_token,
            },
            payload,
        )
    if channel == "webhook":
        assert config.webhook_url is not None
        return await WebhookProvider().send_accepted(
            {"url": config.webhook_url, "headers": config.webhook_headers},
            payload,
        )
    if channel == "discord":
        assert config.discord_webhook_url is not None
        return await DiscordProvider().send_accepted(
            {"webhook_url": config.discord_webhook_url}, payload
        )
    if channel == "slack":
        assert config.slack_webhook_url is not None
        return await SlackProvider().send_accepted(
            {"webhook_url": config.slack_webhook_url}, payload
        )
    assert config.telegram_bot_token is not None
    assert config.telegram_chat_id is not None
    return await TelegramProvider().send_accepted(
        {
            "bot_token": config.telegram_bot_token,
            "chat_id": config.telegram_chat_id,
        },
        payload,
    )


async def _deliver_payload(
    config: CLINotificationConfig,
    payload: NotificationDTO,
    *,
    strict: bool,
    label: str | None = None,
) -> None:
    """Deliver ``payload`` to each configured channel, redacting secrets on errors."""
    for channel in config.channels:
        try:
            accepted = await _send_to_channel(channel, config, payload)
            if accepted is not True:
                raise ValueError(f"{channel} did not accept the notification")
        except Exception as exc:
            if strict:
                raise click.ClickException(
                    f"Could not send {channel} notification ({type(exc).__name__}); check credentials and server settings."
                ) from None
            logger.warning(
                "%sWarning: %s notification delivery failed (%s); continuing watch.",
                f"{label}: " if label else "",
                channel,
                type(exc).__name__,
            )


def _build_stay_payload(
    stay: "AvailabilityStay", *, label: str | None = None
) -> NotificationDTO:
    """Construct a direct per-stay notification payload."""
    nights = (stay.checkout - stay.arrival).days
    suffix = "s" if nights != 1 else ""
    park = (
        f"{stay.campground.recreation_area_name} - {stay.campground.campground_name}"
        if stay.campground.recreation_area_name
        else stay.campground.campground_name
    )
    return NotificationDTO(
        title=f"⛺ {stay.campground.campground_name} ({stay.arrival.isoformat()})",
        message=(
            (f"{label}: " if label else "")
            + f"{stay.campsite_name} (#{stay.campsite_id}) available at {park} "
            f"from {stay.arrival.isoformat()} to {stay.checkout.isoformat()} "
            f"({nights} night{suffix})."
        ),
        booking_url=stay_booking_url(stay),
        url_title="Book Campsite",
        park_name=park,
        campsite_name=stay.campsite_name,
        start_date=stay.arrival,
        end_date=stay.checkout,
    )


def _build_overflow_summary_payload(
    overflow_stays: Sequence["AvailabilityStay"],
    *,
    direct_count: int,
    label: str | None = None,
) -> NotificationDTO:
    """Collapse capped or digest stays into a single summary notification."""
    campgrounds = list(
        dict.fromkeys(stay.campground.campground_name for stay in overflow_stays)
    )
    if len(campgrounds) == 1:
        park_summary = campgrounds[0]
    elif len(campgrounds) == 2:  # noqa: PLR2004
        park_summary = f"{campgrounds[0]} and {campgrounds[1]}"
    else:
        park_summary = f"{campgrounds[0]} +{len(campgrounds) - 1} more"
    earliest = min(stay.arrival for stay in overflow_stays)
    latest = max(stay.checkout for stay in overflow_stays)
    count = len(overflow_stays)
    prefix = f"{label}: " if label else ""
    first_campground = overflow_stays[0].campground
    if direct_count == 0:
        title = f"⛺ {count} stays available ({park_summary})"
        message = (
            f"{prefix}{count} matching campsite stays available at {park_summary} "
            f"between {earliest.isoformat()} and {latest.isoformat()}."
        )
    else:
        title = f"⛺ +{count} more stays available ({park_summary})"
        message = (
            f"{prefix}{count} additional matching campsite stays available at {park_summary} "
            f"between {earliest.isoformat()} and {latest.isoformat()}."
        )
    return NotificationDTO(
        title=title,
        message=message,
        booking_url=first_campground.booking_url,
        url_title="View Campground",
        park_name=park_summary,
        campsite_name=f"{count} stays",
        start_date=earliest,
        end_date=latest,
        metadata={"summary": True, "stay_count": count},
    )


async def send_stay_notifications(
    config: CLINotificationConfig,
    stays: Sequence["AvailabilityStay"],
    *,
    label: str | None = None,
    max_notifications: int = DEFAULT_MAX_NOTIFICATIONS,
) -> None:
    """Send direct booking alerts up to ``max_notifications``, summarizing any overflow."""
    if max_notifications < 1:
        raise ValueError("max_notifications must be at least 1.")
    if not config.channels or not stays:
        return
    if len(stays) <= max_notifications:
        for stay in stays:
            await _deliver_payload(
                config,
                _build_stay_payload(stay, label=label),
                strict=False,
                label=label,
            )
        return

    direct_count = max_notifications - 1
    for stay in stays[:direct_count]:
        await _deliver_payload(
            config,
            _build_stay_payload(stay, label=label),
            strict=False,
            label=label,
        )
    overflow = stays[direct_count:]
    await _deliver_payload(
        config,
        _build_overflow_summary_payload(
            overflow, direct_count=direct_count, label=label
        ),
        strict=False,
        label=label,
    )
    prefix = f"{label}: " if label else ""
    if direct_count == 0:
        logger.warning(
            "%sNotification cap (1) active: sent 1 summary alert covering %s matching stay(s).",
            prefix,
            len(overflow),
        )
    else:
        logger.warning(
            "%sNotification cap (%s) reached: sent %s direct alert(s) and 1 summary covering %s additional stay(s).",
            prefix,
            max_notifications,
            direct_count,
            len(overflow),
        )


@click.command(name="test-notifications")
@options.debug()
@options.notifications(required=True)
@click.pass_context
def test_notifications_cmd(
    ctx: click.Context,
    debug: bool | None,
    notifications: tuple[str, ...],
) -> None:
    """Send a test notification to verify configured CLI alert channels."""
    try:
        config = resolve_notification_config(notifications)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    diagnostic(
        f"Testing notification channels: {', '.join(config.channels)}.",
        resolve_debug(ctx, debug),
    )
    today = utc_today()
    payload = NotificationDTO(
        title="Camply test notification",
        message="Your Camply CLI notifications are working.",
        booking_url="",
        url_title="Open Camply",
        park_name="Notification test",
        campsite_name="Test",
        start_date=today,
        end_date=today + timedelta(days=1),
    )

    async def send_test() -> None:
        await _deliver_payload(config, payload, strict=True)
        for channel in config.channels:
            logger.info('Sent test notification via "%s".', channel)

    run(send_test)
