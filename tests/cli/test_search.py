"""Exercise the public discovery and foreground-search Click contracts."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import date
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from camply.cli.main import cli
from camply.cli.providers import provider_entries
from camply.core import search as core
from camply.providers import PROVIDERS
from camply.providers.base import BaseProvider
from camply.providers.dto import (
    CampgroundSearchResult,
    CampsiteDTO,
    CampsiteType,
    ProviderSearchQuery,
    ProviderSearchResult,
    RecreationAreaSearchResult,
)

_START = "2027-07-09"
_END = "2027-07-13"
_DATES = ["--start-date", _START, "--end-date", _END]


def campground(
    identifier: str = "001", *, name: str = "Pine Camp", state: str = "CA"
) -> CampgroundSearchResult:
    return CampgroundSearchResult(
        provider_id=1,
        provider_name="Recreation.gov",
        campground_id=identifier,
        campground_name=name,
        recreation_area_id="parent",
        recreation_area_name="National Park",
        state=state,
        booking_url=f"https://booking.example.invalid/campgrounds/{identifier}",
    )


@dataclass
class Transcript:
    """Record provider interactions without touching HTTP or a database."""

    constructed: list[str] = field(default_factory=list)
    clients: list[AsyncMock] = field(default_factory=list)
    searches: list[tuple[str, str, dict[str, object]]] = field(default_factory=list)
    lookups: list[str] = field(default_factory=list)
    areas: list[str] = field(default_factory=list)
    checks: list[tuple[str, date, date]] = field(default_factory=list)
    results: list[ProviderSearchResult] = field(default_factory=lambda: [campground()])
    targets: list[CampgroundSearchResult] = field(
        default_factory=lambda: [campground()]
    )
    fail: Exception | None = None
    cycles: int = 2
    empty: bool = False


async def _filter_results(
    _: BaseProvider,
    candidates: list[CampgroundSearchResult],
    *,
    query: str = "",
    state: str | None = None,
) -> list[CampgroundSearchResult]:
    request = ProviderSearchQuery(query=query, state=state)
    return [candidate for candidate in candidates if candidate.matches(request)]


@pytest.fixture
def transcript(monkeypatch: pytest.MonkeyPatch) -> Transcript:
    record = Transcript()
    monkeypatch.delenv("CAMPLY_PROVIDER", raising=False)
    monkeypatch.setattr(core, "POLL_INTERVAL_SECONDS", 0.0001)
    monkeypatch.setattr(core, "utc_today", lambda: date(2027, 7, 1))

    def initialize(instance: BaseProvider) -> None:
        record.constructed.append(type(instance).__name__)
        client = AsyncMock()
        record.clients.append(client)
        instance.async_client = client

    async def search(
        instance: BaseProvider, query: str = "", **kwargs: object
    ) -> list[ProviderSearchResult]:
        record.searches.append((type(instance).__name__, query, kwargs))
        if record.fail:
            raise record.fail
        return record.results

    async def lookup(_: BaseProvider, identifier: str) -> CampgroundSearchResult:
        record.lookups.append(identifier)
        if identifier == "bad":
            raise ValueError("Unknown or nonbookable campground 'bad'.")
        return campground(identifier)

    async def iterate(
        _: BaseProvider, identifier: str
    ) -> AsyncIterator[CampgroundSearchResult]:
        record.areas.append(identifier)
        if identifier == "bad":
            raise ValueError("Unknown recreation area 'bad'.")
        for target in record.targets:
            yield target

    for provider_class in PROVIDERS.values():
        monkeypatch.setattr(provider_class, "filter_campgrounds", _filter_results)
        monkeypatch.setattr(provider_class, "__init__", initialize)
        monkeypatch.setattr(provider_class, "get_campground", lookup)
    monkeypatch.setattr(BaseProvider, "search", search)
    monkeypatch.setattr(BaseProvider, "get_campground", lookup)
    monkeypatch.setattr(BaseProvider, "iter_campgrounds", iterate)
    _install_availability(monkeypatch, record)
    return record


def _install_availability(monkeypatch: pytest.MonkeyPatch, record: Transcript) -> None:
    async def availability(
        _: BaseProvider, identifier: str, start: date, end: date
    ) -> list[CampsiteDTO]:
        if len(record.checks) >= record.cycles:
            raise asyncio.CancelledError
        record.checks.append((identifier, start, end))
        if record.fail:
            raise record.fail
        if record.empty:
            return []
        return [
            CampsiteDTO(
                campsite_id="site-01",
                campsite_name="Site One",
                campsite_type=CampsiteType.TENT,
                capacity=4,
                available_dates=[date(2027, 7, day) for day in range(8, 15)],
                is_electric=False,
                is_accessible=False,
            )
        ]

    for provider_class in PROVIDERS.values():
        monkeypatch.setattr(provider_class, "find_availabilities", availability)


@pytest.mark.parametrize(
    "args",
    [
        ["--help"],
        ["-h"],
        ["--version"],
        [],
        ["providers"],
        ["providers", "--help"],
        ["recreation-areas", "--help"],
        ["campgrounds", "--help"],
        ["campsites", "--help"],
    ],
)
def test_help_and_listing_never_construct_a_provider(
    transcript: Transcript, args: list[str]
) -> None:
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    assert transcript.constructed == []
    assert transcript.clients == []


def test_provider_capabilities_are_truthful(transcript: Transcript) -> None:
    result = CliRunner().invoke(cli, ["providers"])
    assert result.exit_code == 0
    assert "camply, the campsite finder ⛺️" in result.stdout
    assert "camply currently supports 13 providers:" in result.stdout
    assert sum('":    ' in line for line in result.stdout.splitlines()) == 13
    assert '"RecreationDotGov":    Recreation.gov' in result.stdout
    assert (
        '"ReserveAmerica":    ReserveAmerica (no recreation-area catalog'
        in result.stdout
    )
    assert "GoingToCamp" not in result.stdout
    assert "Exiting camply 👋" in result.stdout


@pytest.mark.parametrize(
    "name,expected",
    [
        (name, provider_class.__name__)
        for name, (provider_class, _) in provider_entries().items()
    ]
    + [
        (provider_class.__name__.swapcase(), provider_class.__name__)
        for provider_class, _ in provider_entries().values()
    ],
)
def test_canonical_names_and_registered_class_aliases(
    transcript: Transcript, name: str, expected: str
) -> None:
    result = CliRunner().invoke(cli, ["campgrounds", "--provider", name.swapcase()])
    assert result.exit_code == 0, result.output
    assert transcript.constructed == [expected]


@pytest.mark.parametrize(
    ("root", "command", "environment", "expected"),
    [
        ([], [], None, "RecreationGovProvider"),
        ([], [], "reserveamerica", "ReserveAmericaProvider"),
        (["--provider", "ReserveCalifornia"], [], "bad", "ReserveCaliforniaProvider"),
        (
            ["--provider", "bad"],
            ["--provider", "FloridaStateParks"],
            "bad",
            "FloridaStateParksProvider",
        ),
        (
            ["--provider", "ReserveAmerica", "--provider", "ReserveCalifornia"],
            [],
            None,
            "ReserveCaliforniaProvider",
        ),
        (
            [],
            ["--provider", "ReserveAmerica", "--provider", "ReserveCalifornia"],
            None,
            "ReserveCaliforniaProvider",
        ),
    ],
)
def test_provider_precedence_uses_only_winning_value(
    transcript: Transcript,
    monkeypatch: pytest.MonkeyPatch,
    root: list[str],
    command: list[str],
    environment: str | None,
    expected: str,
) -> None:
    if environment is not None:
        monkeypatch.setenv("CAMPLY_PROVIDER", environment)
    result = CliRunner().invoke(cli, [*root, "campgrounds", *command])
    assert result.exit_code == 0, result.output
    assert transcript.constructed == [expected]


@pytest.mark.parametrize(
    "args",
    [
        ["--provider", "GoingToCamp", "campgrounds"],
        ["campgrounds", "--provider", "bogus"],
    ],
)
def test_unavailable_winning_provider_is_actionable(
    transcript: Transcript, args: list[str]
) -> None:
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 2
    assert "camply providers" in result.stderr
    assert transcript.constructed == []


@pytest.mark.parametrize(
    "root,command,enabled",
    [
        ([], [], False),
        (["--debug"], [], True),
        (["--debug"], ["--no-debug"], False),
        (["--no-debug"], ["--debug"], True),
        ([], ["--debug", "--no-debug"], False),
    ],
)
def test_debug_precedence_and_stream(
    transcript: Transcript, root: list[str], command: list[str], enabled: bool
) -> None:
    result = CliRunner().invoke(cli, [*root, "campgrounds", *command])
    assert result.exit_code == 0, result.output
    assert ("Debug:" in result.stderr) is enabled
    assert "Debug:" not in result.stdout


def test_discovery_normalizes_search_state_and_requests_probe(
    transcript: Transcript,
) -> None:
    transcript.results = [
        RecreationAreaSearchResult(
            provider_id=1,
            provider_name="Recreation.gov",
            recreation_area_id="park",
            recreation_area_name="Yosemite",
            booking_url="https://booking.example.invalid/park",
        )
    ]
    result = CliRunner().invoke(
        cli, ["recreation-areas", "--search", "  Yosemite  ", "--state", " ca "]
    )
    assert result.exit_code == 0, result.output
    assert 'Searching for Recreation Areas: "Yosemite"' in result.stdout
    assert "1 recreation areas found." in result.stdout
    assert "⛰  Yosemite (#park)" in result.stdout
    assert transcript.searches[0][1] == "Yosemite"
    assert transcript.searches[0][2] == {
        "state": "CA",
        "entity_type": "recreation_area",
        "limit": 51,
    }
    transcript.clients[0].aclose.assert_awaited_once()


@pytest.mark.parametrize("count,truncated", [(0, False), (50, False), (51, True)])
def test_display_limit_distinguishes_exactly_fifty(
    transcript: Transcript, count: int, truncated: bool
) -> None:
    transcript.results = [campground(f"{index:03}") for index in reversed(range(count))]
    result = CliRunner().invoke(cli, ["campgrounds"])
    assert result.exit_code == 0, result.output
    assert result.stdout.count("🏕  Pine Camp (#") == min(count, 50)
    assert ("more results exist" in result.stderr) is truncated
    if count:
        assert "50 Matching Campgrounds Found" in result.stdout
        assert result.stdout.index("🏕  Pine Camp (#000)") < result.stdout.index(
            "🏕  Pine Camp (#049)"
        )
    else:
        assert "No eligible campgrounds" in result.stdout


def test_exact_lookup_preserves_ids_ignores_areas_and_deduplicates(
    transcript: Transcript,
) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "campgrounds",
            "--rec-area",
            "bad",
            "--campground",
            " 001 ",
            "--campground",
            "001",
            "--campground",
            "NY_0005",
        ],
    )
    assert result.exit_code == 0, result.output
    assert transcript.lookups == ["001", "NY_0005"]
    assert transcript.areas == []
    assert transcript.searches == []
    assert "Ignoring --rec-area" in result.stderr
    assert "NY_0005" in result.stdout


def test_filter_excluding_valid_exact_id_is_successful_empty(
    transcript: Transcript,
) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "campgrounds",
            "--campground",
            "001",
            "--search",
            "different",
            "--state",
            "NY",
        ],
    )
    assert result.exit_code == 0, result.output
    assert transcript.lookups == ["001"]
    assert "No eligible campgrounds" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        ["campsites", "--campground", "001"],
        ["campsites", *_DATES],
        [
            "campsites",
            "--campground",
            "001",
            "--start-date",
            _START,
            "--start-date",
            _START,
            "--end-date",
            _END,
        ],
        [
            "campsites",
            "--campground",
            "001",
            "--start-date",
            _END,
            "--end-date",
            _START,
        ],
        [
            "campsites",
            "--campground",
            "001",
            "--start-date",
            "2027-02-29",
            "--end-date",
            _END,
        ],
        ["campsites", "--campground", "001", *_DATES, "--day", "xyz"],
        ["campsites", "--campground", "001", *_DATES, "--nights", "0"],
        ["campsites", "--campground", "001", *_DATES, "--nights", "5"],
        [
            "campsites",
            "--campground",
            "001",
            *_DATES,
            "--day",
            "Monday",
            "--nights",
            "2",
        ],
        ["campgrounds", "--state", "California"],
        ["campgrounds", "--state", "éé"],
        ["campgrounds", "--campground", "  "],
    ],
)
def test_invalid_inputs_fail_before_provider_io(
    transcript: Transcript, args: list[str]
) -> None:
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 2, result.output
    assert transcript.constructed == []
    assert transcript.checks == []


@pytest.mark.parametrize(
    "args",
    [
        ["list-campsites"],
        ["configure"],
        ["test-notifications"],
        ["tui"],
        ["campsites", "--campsite", "123", *_DATES],
        *[
            ["campsites", "--campground", "001", *_DATES, flag]
            for flag in (
                "--continuous",
                "--search-forever",
                "--search-once",
                "--notify-first-try",
                "--offline-search",
            )
        ],
        ["campsites", "--campground", "001", *_DATES, "--notifications", "pushover"],
        ["campsites", "--campground", "001", *_DATES, "--yaml-config", "config.yml"],
        ["campsites", "--campground", "001", *_DATES, "--equipment", "tent"],
    ],
)
def test_deferred_options_are_rejected(transcript: Transcript, args: list[str]) -> None:
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 2, result.output
    assert transcript.constructed == []


def test_invalid_selected_id_prevents_all_availability_io_and_closes(
    transcript: Transcript,
) -> None:
    result = CliRunner().invoke(
        cli, ["campsites", "--campground", "001", "--campground", "bad", *_DATES]
    )
    assert result.exit_code == 1
    assert "Unknown or nonbookable campground" in result.stderr
    assert transcript.checks == []
    transcript.clients[0].aclose.assert_awaited_once()


def test_real_command_prints_sliding_stays_and_continues_after_matches(
    transcript: Transcript,
) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "campsites",
            "--rec-area",
            "bad",
            "--campground",
            "001",
            "--campground",
            "001",
            *_DATES,
            "--nights",
            "3",
        ],
    )
    assert result.exit_code == 1  # Simulated cancellation after two successful cycles.
    assert transcript.checks == [("001", date(2027, 7, 9), date(2027, 7, 13))] * 2
    assert "1 Matching Campgrounds Found" in result.stdout
    assert "⛰  National Park, CA (#parent) - 🏕  Pine Camp (#001)" in result.stdout
    assert "Searching across 1 campgrounds" in result.stdout
    assert "2 Reservable Campsites Matching Search Preferences" in result.stdout
    assert result.stdout.count("📅 Fri, July 09 🏕  1 sites") == 2
    assert result.stdout.count("📅 Sat, July 10 🏕  1 sites") == 2
    assert "⛰️  National Park, CA  🏕  Pine Camp: ⛺ 1 sites" in result.stdout
    assert (
        "🔗 https://booking.example.invalid/campgrounds/001 (3 nights)" in result.stdout
    )
    assert "Ignoring --rec-area" in result.stderr
    assert transcript.areas == []
    transcript.clients[0].aclose.assert_awaited_once()


def test_weekend_and_repeated_weekday_union_reaches_matching(
    transcript: Transcript,
) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "campsites",
            "--campground",
            "001",
            *_DATES,
            "--weekends",
            "--day",
            "SUN",
            "--day",
            "Sunday",
            "--nights",
            "3",
        ],
    )
    assert result.exit_code == 1
    assert result.stdout.count("📅 Fri, July 09 🏕  1 sites") == 2
    assert "📅 Sat, July 10" not in result.stdout


def test_repeated_windows_merge_without_gap_or_duplicate_requests(
    transcript: Transcript,
) -> None:
    transcript.cycles = 4
    args = [
        "campsites",
        "--campground",
        "001",
        "--start-date",
        "2027-07-09",
        "--end-date",
        "2027-07-11",
        "--start-date",
        "2027-07-10",
        "--end-date",
        "2027-07-12",
        "--start-date",
        "2027-07-14",
        "--end-date",
        "2027-07-15",
    ]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 1
    expected = [
        ("001", date(2027, 7, 9), date(2027, 7, 12)),
        ("001", date(2027, 7, 14), date(2027, 7, 15)),
    ]
    assert transcript.checks == expected * 2
    assert "2027-07-12 to 2027-07-13" not in result.stdout


def test_area_union_exhaustive_targets_are_not_display_limited(
    transcript: Transcript,
) -> None:
    transcript.targets = [campground(str(index)) for index in range(1002)]
    transcript.cycles = 1002
    result = CliRunner().invoke(
        cli,
        ["campsites", "--rec-area", "a", "--rec-area", "b", "--rec-area", "a", *_DATES],
    )
    assert result.exit_code == 1
    assert transcript.areas == ["a", "b"]
    assert len(transcript.checks) == 1002
    assert len({identifier for identifier, _, _ in transcript.checks}) == 1002


def test_empty_area_is_explained_and_closes(transcript: Transcript) -> None:
    transcript.targets = []
    result = CliRunner().invoke(cli, ["campsites", "--rec-area", "area", *_DATES])
    assert result.exit_code == 0, result.output
    assert "No eligible campgrounds" in result.stdout
    assert transcript.checks == []
    transcript.clients[0].aclose.assert_awaited_once()


def test_empty_checks_continue_and_notification_settings_are_irrelevant(
    transcript: Transcript, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PUSHOVER_APP_TOKEN", "malformed-secret")
    monkeypatch.setenv("PUSHOVER_USER_KEY", "not-an-initial-cli-setting")
    transcript.empty = True
    result = CliRunner().invoke(cli, ["campsites", "--campground", "001", *_DATES])
    assert result.exit_code == 1
    assert len(transcript.checks) == 2
    assert result.stdout.count("No matching campsite stays") == 2
    assert "secret" not in result.output
    transcript.clients[0].aclose.assert_awaited_once()


def test_provider_failure_is_not_empty_and_exception_payload_is_redacted(
    transcript: Transcript,
) -> None:
    transcript.fail = RuntimeError(
        "https://secret-token@example.invalid?secret=credential"
    )
    result = CliRunner().invoke(
        cli, ["--debug", "campsites", "--campground", "001", *_DATES]
    )
    assert result.exit_code == 1
    assert "Provider request failed (RuntimeError)" in result.stderr
    assert "No matching" not in result.stdout
    assert "secret-token" not in result.output
    transcript.clients[0].aclose.assert_awaited_once()


def test_past_start_clamps_before_provider_request(transcript: Transcript) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "campsites",
            "--campground",
            "001",
            "--start-date",
            "2027-06-28",
            "--end-date",
            "2027-07-10",
        ],
    )
    assert result.exit_code == 1
    assert "Clamped past start" in result.stderr
    assert transcript.checks[0][1] == date(2027, 7, 1)


def test_schema_failure_does_not_disclose_provider_input(
    transcript: Transcript,
) -> None:
    from pydantic import ValidationError

    try:
        CampsiteDTO.model_validate({"capacity": "sensitive-provider-payload"})
    except ValidationError as exc:
        transcript.fail = exc
    result = CliRunner().invoke(cli, ["campgrounds", "--debug"])
    assert result.exit_code == 1
    assert "Provider returned invalid data" in result.stderr
    assert "sensitive-provider-payload" not in result.output
    transcript.clients[0].aclose.assert_awaited_once()


@pytest.mark.parametrize("value", ["2027-7-9", "20270709", "2027-07-09T00:00:00"])
def test_calendar_dates_require_documented_iso_spelling(
    transcript: Transcript, value: str
) -> None:
    result = CliRunner().invoke(
        cli,
        ["campsites", "--campground", "001", "--start-date", value, "--end-date", _END],
    )
    assert result.exit_code == 2
    assert "YYYY-MM-DD" in result.stderr
    assert transcript.constructed == []


def test_provider_diagnostic_payloads_are_suppressed_and_config_restored(
    transcript: Transcript, monkeypatch: pytest.MonkeyPatch
) -> None:
    import structlog

    original = structlog.get_config()

    async def noisy_search(
        *args: object, **kwargs: object
    ) -> list[ProviderSearchResult]:
        structlog.get_logger().warning(
            "private-provider-event", authorization="credential-sentinel"
        )
        return [campground()]

    monkeypatch.setattr(BaseProvider, "search", noisy_search)
    result = CliRunner().invoke(cli, ["campgrounds", "--debug"])
    assert result.exit_code == 0, result.output
    assert "credential-sentinel" not in result.output
    assert "private-provider-event" not in result.output
    assert "Debug:" in result.stderr
    assert structlog.get_config() == original


def test_unknown_area_fails_before_availability_and_releases_client(
    transcript: Transcript,
) -> None:
    result = CliRunner().invoke(
        cli, ["campsites", "--rec-area", "good", "--rec-area", "bad", *_DATES]
    )
    assert result.exit_code == 1
    assert "Unknown recreation area" in result.stderr
    assert transcript.areas == ["good", "bad"]
    assert transcript.checks == []
    transcript.clients[0].aclose.assert_awaited_once()


def test_provider_without_area_catalog_returns_explained_empty(
    transcript: Transcript,
) -> None:
    transcript.results = []
    result = CliRunner().invoke(
        cli, ["recreation-areas", "--provider", "ReserveAmerica"]
    )
    assert result.exit_code == 0, result.output
    assert "No recreation areas found" in result.stdout
    assert "may not have a recreation-area catalog" in result.stdout
    transcript.clients[0].aclose.assert_awaited_once()


@pytest.mark.parametrize("handler", ["rich", "python"])
def test_rich_and_python_log_handlers_log_banners_and_tables(
    transcript: Transcript, monkeypatch: pytest.MonkeyPatch, handler: str
) -> None:
    monkeypatch.setenv("CAMPLY_LOG_HANDLER", handler)
    result = CliRunner().invoke(
        cli, ["campgrounds", "--debug", "--search", "Pine", "--state", "CA"]
    )
    assert result.exit_code == 0, result.output
    assert "CAMPLY" in result.stdout
    assert "camply, the campsite finder ⛺️" in result.stdout
    assert 'Using Camply Provider: "RecreationDotGov"' in result.stdout
    assert 'Searching for Campgrounds: "Pine"' in result.stdout
    assert "1 Matching Campgrounds Found" in result.stdout
    assert "⛰  National Park, CA (#parent) - 🏕  Pine Camp (#001)" in result.stdout
    assert "Exiting camply 👋" in result.stdout
    assert "Setting up camply debugging" in result.stderr
    assert "Camply Version:" in result.stderr
    assert "Python Version:" in result.stderr
    assert "Platform:" in result.stderr


def test_rich_cli_screenshot_html_and_svg_export() -> None:
    """Rich CLI handler exports full-width HTML and SVG terminal captures."""
    import io
    import logging

    from rich.console import Console

    from camply.cli.output import (
        CAMPLY_LOG_LEVEL,
        CamplyRichHandler,
        log_camply,
        render_discovery,
        render_providers,
        render_stays,
    )
    from camply.core.search import AvailabilityStay

    console = Console(
        file=io.StringIO(),
        record=True,
        force_terminal=True,
        color_system="truecolor",
        width=120,
    )
    handler = CamplyRichHandler(
        console=console,
        show_path=False,
        markup=False,
        rich_tracebacks=True,
        log_time_format="[%Y-%m-%d %H:%M:%S]",
    )
    cli_logger = logging.getLogger("camply.cli")
    previous_handlers = list(cli_logger.handlers)
    previous_level = cli_logger.level
    cli_logger.handlers = [handler]
    cli_logger.setLevel(logging.DEBUG)
    target = campground("232450", name="Lower Pines")
    try:
        log_camply("camply, the campsite finder ⛺️")
        cli_logger.info('Using Camply Provider: "RecreationDotGov"')
        render_providers(dict(list(provider_entries().items())[:3]))
        render_discovery([target], empty="No campgrounds found.")
        render_stays(
            [
                AvailabilityStay(
                    campground=target,
                    campsite_id="1001",
                    campsite_name="Site 014",
                    arrival=date(2030, 7, 10),
                    checkout=date(2030, 7, 13),
                    booking_url="https://www.recreation.gov/camping/campsites/1001",
                )
            ]
        )
        log_camply("Exiting camply 👋")
    finally:
        cli_logger.handlers = previous_handlers
        cli_logger.setLevel(previous_level)

    assert logging.getLevelName(CAMPLY_LOG_LEVEL) == "CAMPLY"
    html = console.export_html(inline_styles=True, clear=False)
    svg = console.export_svg(title="camply cli").replace("&#160;", " ")
    for export in (html, svg):
        assert "camply, the campsite finder" in export
        assert "RecreationDotGov" in export
        assert "Lower Pines" in export and "232450" in export
        assert "Wed, July" in export
        assert "https://www.recreation.gov/camping/campsites/1001" in export
        assert "Exiting camply" in export
