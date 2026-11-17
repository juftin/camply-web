"""Stateless CLI Pushover and ntfy notification configuration, deduplication, and delivery."""

import json
import os
import re
import tempfile
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

import click
from pydantic import BaseModel, ConfigDict, Field

from camply.cli import options
from camply.cli.execution import run
from camply.cli.options import resolve_debug
from camply.cli.output import diagnostic, logger, stay_booking_url
from camply.core.search import utc_today
from camply.db.notification_config import validate_ntfy_url
from camply.notifications.base import NotificationDTO
from camply.notifications.ntfy import NtfyProvider
from camply.notifications.pushover import PushoverProvider

if TYPE_CHECKING:
    from camply.core.search import AvailabilityStay

ChannelName = Literal["pushover", "ntfy"]
_NTFY_TOPIC_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
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


def _resolve_ntfy_settings(
    ntfy_topic: str | None,
    ntfy_server: str | None,
) -> tuple[str, str, str | None]:
    """Resolve and validate ntfy topic, server URL, and optional access token."""
    raw_topic = (
        ntfy_topic if ntfy_topic is not None else os.environ.get("NTFY_TOPIC", "")
    ).strip()
    if not raw_topic or _NTFY_TOPIC_PATTERN.fullmatch(raw_topic) is None:
        raise ValueError(
            "ntfy notifications require a valid ntfy topic (1-64 letters, digits, '_' or '-') via --ntfy-topic or NTFY_TOPIC."
        )
    raw_server = (
        ntfy_server
        if ntfy_server is not None
        else os.environ.get("NTFY_SERVER_URL", "")
    ).strip()
    server_url = validate_ntfy_url(raw_server) if raw_server else _DEFAULT_NTFY_SERVER
    raw_token = os.environ.get("NTFY_ACCESS_TOKEN", "")
    if raw_token and any(
        not char.isprintable() or not char.isascii() for char in raw_token
    ):
        raise ValueError("NTFY_ACCESS_TOKEN must contain printable ASCII characters.")
    return raw_topic, server_url, raw_token or None


def resolve_notification_config(
    channels: Sequence[str],
    ntfy_topic: str | None,
    ntfy_server: str | None,
) -> CLINotificationConfig:
    """Resolve and validate CLI notification settings without database access.

    When ``channels`` is empty, environment variables are not read or validated.
    """
    normalized: list[ChannelName] = []
    for raw in channels:
        key = raw.strip().lower()
        if key not in ("pushover", "ntfy"):
            raise ValueError(
                f"Unsupported notification channel {raw!r}; choose 'pushover' or 'ntfy'."
            )
        channel = cast(ChannelName, key)
        if channel not in normalized:
            normalized.append(channel)

    if not normalized:
        return CLINotificationConfig()

    user_key, app_token = (
        _resolve_pushover_credentials() if "pushover" in normalized else (None, None)
    )
    topic, server_url, access_token = (
        _resolve_ntfy_settings(ntfy_topic, ntfy_server)
        if "ntfy" in normalized
        else (None, _DEFAULT_NTFY_SERVER, None)
    )

    return CLINotificationConfig(
        channels=tuple(normalized),
        pushover_user_key=user_key,
        pushover_app_token=app_token,
        ntfy_topic=topic,
        ntfy_server_url=server_url,
        ntfy_access_token=access_token,
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


class StayDeduplicationState:
    """Track seen stay keys across poll cycles and optional JSON state-file persistence."""

    def __init__(
        self,
        seen: set[str] | None = None,
        *,
        state_file: Path | None = None,
    ) -> None:
        self.seen: set[str] = set(seen) if seen else set()
        self.state_file = state_file

    @classmethod
    def load(cls, state_file: Path | None = None) -> "StayDeduplicationState":
        """Load initial seen stays from ``state_file`` if present, recovering on corruption."""
        if state_file is None or not state_file.exists():
            return cls(state_file=state_file)
        try:
            payload = json.loads(state_file.read_text(encoding="utf-8"))
            entries = payload.get("seen_stays") if isinstance(payload, dict) else None
            if not isinstance(entries, list) or not all(
                isinstance(item, str) for item in entries
            ):
                raise ValueError("Invalid state file schema")
            return cls(seen=set(entries), state_file=state_file)
        except Exception as exc:
            logger.warning(
                "Warning: Could not read state file %s (%s); starting with empty state.",
                state_file,
                type(exc).__name__,
            )
            return cls(state_file=state_file)

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
                handle.write(content)
                temp_path = Path(handle.name)
            temp_path.replace(self.state_file)
        except OSError as exc:
            logger.warning(
                "Warning: Could not write state file %s (%s).",
                self.state_file,
                type(exc).__name__,
            )


async def _deliver_payload(
    config: CLINotificationConfig,
    payload: NotificationDTO,
    *,
    strict: bool,
) -> None:
    """Deliver ``payload`` to each configured channel, redacting secrets on errors."""
    for channel in config.channels:
        try:
            if channel == "pushover":
                assert config.pushover_user_key is not None
                assert config.pushover_app_token is not None
                PushoverProvider.config.app_token = config.pushover_app_token
                accepted = await PushoverProvider().send_accepted(
                    config.pushover_user_key, payload
                )
            else:
                assert config.ntfy_topic is not None
                accepted = await NtfyProvider().send_accepted(
                    {
                        "topic": config.ntfy_topic,
                        "server_url": config.ntfy_server_url,
                        "access_token": config.ntfy_access_token,
                    },
                    payload,
                )
            if accepted is not True:
                raise ValueError(f"{channel} did not accept the notification")
        except Exception as exc:
            if strict:
                raise click.ClickException(
                    f"Could not send {channel} notification ({type(exc).__name__}); check credentials and server settings."
                ) from None
            logger.warning(
                "Warning: %s notification delivery failed (%s); continuing watch.",
                channel,
                type(exc).__name__,
            )


async def send_stay_notifications(
    config: CLINotificationConfig,
    stays: Sequence["AvailabilityStay"],
) -> None:
    """Send direct provider booking alerts for each newly observed stay."""
    if not config.channels or not stays:
        return
    for stay in stays:
        nights = (stay.checkout - stay.arrival).days
        suffix = "s" if nights != 1 else ""
        park = (
            f"{stay.campground.recreation_area_name} - {stay.campground.campground_name}"
            if stay.campground.recreation_area_name
            else stay.campground.campground_name
        )
        payload = NotificationDTO(
            title=f"⛺ {stay.campground.campground_name} ({stay.arrival.isoformat()})",
            message=(
                f"{stay.campsite_name} (#{stay.campsite_id}) available at {park} "
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
        await _deliver_payload(config, payload, strict=False)


@click.command(name="test-notifications")
@options.debug()
@options.notifications(required=True)
@options.ntfy_topic()
@options.ntfy_server()
@click.pass_context
def test_notifications_cmd(
    ctx: click.Context,
    debug: bool | None,
    notifications: tuple[str, ...],
    ntfy_topic: str | None,
    ntfy_server: str | None,
) -> None:
    """Send a test notification to verify Pushover or ntfy configuration."""
    try:
        config = resolve_notification_config(notifications, ntfy_topic, ntfy_server)
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
