"""Decode and validate campsite search configuration before starting a batch."""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Self

import click
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError
from yaml.nodes import MappingNode, ScalarNode

from camply.cli.discovery import normalize_ids
from camply.cli.notifications import CLINotificationConfig, resolve_notification_config
from camply.cli.providers import find_provider, validate_provider_filters
from camply.core.search import SearchRequest, allowed_weekdays, normalize_request
from camply.providers.base import BaseProvider


class ConfigError(ValueError):
    """An actionable configuration error safe to print."""


class _ConfigLoader(yaml.SafeLoader):
    """Preserve ISO date strings and reject repeated YAML mapping keys."""

    def construct_mapping(
        self, node: MappingNode, deep: bool = False
    ) -> dict[Any, Any]:
        keys: set[str] = set()
        for key, _ in node.value:
            if not isinstance(key, ScalarNode) or key.tag != "tag:yaml.org,2002:str":
                raise ConfigError(
                    f"Expected a string key at line {key.start_mark.line + 1}."
                )
            if key.value in keys:
                raise ConfigError(f"Duplicate key at line {key.start_mark.line + 1}.")
            keys.add(key.value)
        return super().construct_mapping(node, deep)


_ConfigLoader.yaml_implicit_resolvers = {
    initial: [
        (tag, pattern)
        for tag, pattern in resolvers
        if tag not in {"tag:yaml.org,2002:timestamp", "tag:yaml.org,2002:bool"}
    ]
    for initial, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_ConfigLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.IGNORECASE), "tTfF"
)

NonBlank = Annotated[str, StringConstraints(pattern=r"\S")]
IsoDay = Annotated[str, StringConstraints(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]
RvLength = Annotated[int, Field(ge=1, le=200)]
Channel = Annotated[str, StringConstraints(pattern=r"(?i)^\s*(pushover|ntfy)\s*$")]
SiteType = Annotated[
    str, StringConstraints(pattern=r"(?i)^\s*(tent|rv|cabin|other)\s*$")
]


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class DateWindow(_Input):
    """A check-in and checkout pair in the config file."""

    start_date: IsoDay
    end_date: IsoDay

    @field_validator("start_date", "end_date")
    @classmethod
    def valid_date(cls, value: str) -> str:
        """Check the calendar date without changing its input representation."""
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError("invalid calendar date") from None
        return value


class SearchDefaults(_Input):
    """Settings that may be shared by all searches."""

    days: list[NonBlank] = Field(default_factory=list)
    weekends: bool = False
    nights: int = Field(default=1, ge=1)
    campsite_types: list[SiteType] = Field(default_factory=list)
    electric: bool = False
    accessible: bool = False
    rv_length: RvLength | None = None
    interval: int = Field(default=10, ge=5)
    notifications: list[Channel] = Field(default_factory=list)

    @field_validator("rv_length")
    @classmethod
    def shared_rv_length(cls, value: int | None) -> int | None:
        """Require a length when the shared key is explicitly supplied."""
        if value is None and cls is SearchDefaults:
            raise ValueError("shared RV length must be an integer")
        return value

    @field_validator("days")
    @classmethod
    def valid_days(cls, value: list[str]) -> list[str]:
        """Validate shared weekday values even when every search overrides them."""
        allowed_weekdays(value, weekends=False)
        return value


class SearchInput(SearchDefaults):
    """A single named search and its optional overrides."""

    name: NonBlank
    provider: NonBlank
    campgrounds: list[NonBlank] = Field(default_factory=list)
    recreation_areas: list[NonBlank] = Field(default_factory=list)
    campsites: list[NonBlank] = Field(default_factory=list)
    date_windows: list[DateWindow] = Field(min_length=1)
    state_file: NonBlank | None = None

    @field_validator("state_file")
    @classmethod
    def defined_state_file(cls, value: str | None) -> str:
        """Reject explicit null paths while allowing omission."""
        if value is None:
            raise ValueError("state file must be a path")
        return value

    @model_validator(mode="after")
    def has_parent(self) -> Self:
        """Require a campground or recreation area."""
        if not self.campgrounds and not self.recreation_areas:
            raise PydanticCustomError(
                "missing_parent", "add a campground or recreation area"
            )
        return self


class SearchConfig(_Input):
    """The single file-mode document."""

    defaults: SearchDefaults = Field(default_factory=SearchDefaults)
    searches: list[SearchInput] = Field(min_length=1)


_FIELD_NAMES = {
    *SearchConfig.model_fields,
    *SearchInput.model_fields,
    *DateWindow.model_fields,
}
_LEGACY_KEYS = {"provider", "campgrounds", "recreation_area", "start_date", "end_date"}
_HINTS = {
    "days": "use English weekday names or abbreviations",
    "rv_length": "use a whole number from 1 to 200 (or null on a search)",
    "interval": "use a whole number of at least 5 minutes",
    "nights": "use a positive whole number",
    "date_windows": "provide at least one date window",
    "start_date": "use a valid calendar date in YYYY-MM-DD form",
    "end_date": "use a valid calendar date in YYYY-MM-DD form",
    "notifications": "choose pushover or ntfy",
    "campsite_types": "choose TENT, RV, CABIN, or OTHER",
}


def _format_errors(exc: ValidationError) -> str:
    lines = []
    for error in exc.errors(
        include_input=False, include_context=False, include_url=False
    ):
        location = error["loc"]
        safe_location = [
            str(part) if isinstance(part, int) or part in _FIELD_NAMES else "<field>"
            for part in location
        ]
        hint = error["msg"] if error["type"] != "value_error" else "invalid value"
        if error["type"] == "extra_forbidden":
            safe_location[-1] = "<unknown field>"
        elif location and location[-1] == "rv_length" and location[0] == "defaults":
            hint = "use a whole number from 1 to 200"
        else:
            hint = next(
                (_HINTS[part] for part in reversed(location) if part in _HINTS),
                hint,
            )
        lines.append(f"{'.'.join(safe_location) or 'configuration'}: {hint}")
    return "\n".join(lines)


def load_config(path: Path) -> SearchConfig:
    """Read one local YAML document and return validated file fields."""
    try:
        text = path.read_text(encoding="utf-8")
    except (ValueError, OSError):
        raise ConfigError("Could not read the YAML configuration file.") from None
    try:
        data = yaml.load(text, Loader=_ConfigLoader)
    except ConfigError:
        raise
    except yaml.MarkedYAMLError as exc:
        mark = exc.problem_mark
        location = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        raise ConfigError(f"Invalid YAML configuration{location}.") from None
    except (yaml.YAMLError, RecursionError, ValueError):
        raise ConfigError("Invalid YAML configuration.") from None
    if isinstance(data, dict) and "searches" not in data and _LEGACY_KEYS & data.keys():
        raise ConfigError(
            "This is a legacy flat configuration. Move the search into the searches list and pair dates under date_windows."
        )
    try:
        return SearchConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(_format_errors(exc)) from None


@dataclass(frozen=True)
class PreparedSearch:
    """A search that has passed local validation and can start polling."""

    name: str
    provider_name: str
    provider_id: int
    provider_class: type[BaseProvider]
    areas: tuple[str, ...]
    campgrounds: tuple[str, ...]
    request: SearchRequest
    interval_seconds: int
    notifications: CLINotificationConfig
    state_file: Path | None

    @property
    def label(self) -> str:
        """Identify the search and provider safely in terminal diagnostics."""
        return f"{self.name!r} ({self.provider_name})"


def _prepare_search(search: SearchInput, state_file: Path | None) -> PreparedSearch:
    selected = find_provider(search.provider)
    if selected is None:
        raise ConfigError("provider: choose a provider listed by camply providers.")
    name, provider_class, provider_id = selected
    areas = normalize_ids(search.recreation_areas, "recreation_areas")
    campgrounds = normalize_ids(search.campgrounds, "campgrounds")
    request = normalize_request(
        start_dates=[
            date.fromisoformat(window.start_date) for window in search.date_windows
        ],
        end_dates=[
            date.fromisoformat(window.end_date) for window in search.date_windows
        ],
        days=search.days,
        weekends=search.weekends,
        nights=search.nights,
        campsites=normalize_ids(search.campsites, "campsites"),
        campsite_types=search.campsite_types,
        require_electric=search.electric,
        require_accessible=search.accessible,
        min_rv_length=search.rv_length,
    )
    validate_provider_filters(name, provider_class, request)
    try:
        notifications = resolve_notification_config(search.notifications)
    except ValueError as exc:
        raise ConfigError(f"notifications: {exc}") from None
    return PreparedSearch(
        search.name,
        name,
        provider_id,
        provider_class,
        areas,
        campgrounds,
        request,
        search.interval * 60,
        notifications,
        state_file,
    )


def prepare_searches(path: Path) -> list[PreparedSearch]:
    """Resolve inherited values and validate all searches before external work."""
    config = load_config(path)
    try:
        config_path = path.resolve()
    except (OSError, RuntimeError, ValueError):
        raise ConfigError("Could not resolve the YAML configuration path.") from None

    defaults = config.defaults.model_dump(exclude_unset=True)
    names: set[str] = set()
    state_paths: set[Path] = set()
    prepared: list[PreparedSearch] = []
    for index, raw in enumerate(config.searches):
        search = raw.model_copy(
            update={
                name: value
                for name, value in defaults.items()
                if name not in raw.model_fields_set
            }
        )
        try:
            if search.name in names:
                raise ConfigError("name: choose a unique search name.")
            names.add(search.name)
            state_file = None
            if search.state_file is not None:
                try:
                    state_file = (
                        path.absolute().parent / Path(search.state_file).expanduser()
                    ).resolve()
                except (OSError, RuntimeError, ValueError):
                    raise ConfigError(
                        "state_file: could not resolve this path."
                    ) from None
                if state_file == config_path:
                    raise ConfigError(
                        "state_file: path resolves to the configuration file."
                    )
                if state_file in state_paths:
                    raise ConfigError(
                        "state_file: path is already used by another search."
                    )
                state_paths.add(state_file)
            prepared.append(_prepare_search(search, state_file))
        except click.UsageError as exc:
            raise ConfigError(f"searches.{index}: {exc.format_message()}") from None
        except ValueError as exc:
            raise ConfigError(f"searches.{index}: {exc}") from None
    return prepared
