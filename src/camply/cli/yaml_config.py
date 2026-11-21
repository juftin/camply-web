"""Decode and validate campsite search configuration before starting a batch."""

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Self, get_args

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
from pydantic.json_schema import SkipJsonSchema, WithJsonSchema
from pydantic_core import PydanticCustomError
from yaml.nodes import MappingNode, ScalarNode

from camply.cli.discovery import normalize_ids
from camply.cli.notifications import (
    ChannelName,
    CLINotificationConfig,
    resolve_notification_config,
)
from camply.cli.providers import find_provider, validate_provider_filters
from camply.core import search as core_search
from camply.core.search import WEEKDAY_NAMES, SearchRequest, allowed_weekdays
from camply.providers.base import BaseProvider
from camply.providers.dto import CampsiteType

_CONFIG_VERSION = 2


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


def _ascii_choice_pattern(*choices: str) -> str:
    alternatives = "|".join(
        "".join(f"[{letter.lower()}{letter.upper()}]" for letter in choice)
        for choice in choices
    )
    return rf"^\s*(?:{alternatives})\s*$"


NonBlank = Annotated[str, StringConstraints(pattern=r"\S")]
IsoDay = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"),
    Field(json_schema_extra={"format": "date"}),
]
RvLength = Annotated[int, Field(ge=1, le=200)]
DayName = Annotated[
    NonBlank,
    WithJsonSchema(
        {
            "type": "string",
            "pattern": _ascii_choice_pattern(
                *(name for names in WEEKDAY_NAMES for name in names)
            ),
        }
    ),
]
Channel = Annotated[
    str,
    StringConstraints(pattern=_ascii_choice_pattern(*get_args(ChannelName))),
    Field(examples=list(get_args(ChannelName))),
]
SiteType = Annotated[
    str,
    StringConstraints(pattern=_ascii_choice_pattern(*CampsiteType)),
    Field(examples=list(CampsiteType)),
]


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _WeekdayFilters(_Input):
    days: list[DayName] = Field(
        default_factory=list,
        description="English weekday names or abbreviations. An explicit empty list clears inherited weekdays.",
    )
    weekends: bool = Field(
        default=False,
        description="Include Friday and Saturday nights. An explicit false clears an inherited weekend filter.",
    )

    @field_validator("days")
    @classmethod
    def valid_days(cls, value: list[str]) -> list[str]:
        """Validate English weekday names and abbreviations."""
        if any(not day.strip().isascii() for day in value):
            raise ValueError("use English weekday names or abbreviations")
        allowed_weekdays(value, weekends=False)
        return value


class DateWindow(_WeekdayFilters):
    """A check-in and checkout pair in the config file."""

    start_date: IsoDay = Field(description="Inclusive check-in date.")
    end_date: IsoDay = Field(description="Exclusive checkout date.")

    @field_validator("start_date", "end_date")
    @classmethod
    def valid_date(cls, value: str) -> str:
        """Check the calendar date without changing its input representation."""
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError("invalid calendar date") from None
        return value


def _omit_schema_default(schema: dict[str, Any]) -> None:
    schema.pop("default", None)


class SearchDefaults(_WeekdayFilters):
    """Settings that may be shared by all searches."""

    nights: int = Field(default=1, ge=1)
    campsite_types: list[SiteType] = Field(default_factory=list)
    electric: bool = False
    accessible: bool = False
    rv_length: RvLength | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra=_omit_schema_default
    )
    interval: int = Field(default=10, ge=5)
    notifications: list[Channel] = Field(default_factory=list)

    @field_validator("rv_length")
    @classmethod
    def shared_rv_length(cls, value: int | None) -> int | None:
        """Require a length when the shared key is explicitly supplied."""
        if value is None and cls is SearchDefaults:
            raise ValueError("shared RV length must be an integer")
        return value


class SearchInput(SearchDefaults):
    """A single named search and its optional overrides."""

    model_config = ConfigDict(
        json_schema_extra={
            "anyOf": [
                {"required": [key], "properties": {key: {"minItems": 1}}}
                for key in ("campgrounds", "recreation_areas")
            ]
        }
    )

    rv_length: RvLength | None = Field(
        default=None,
        description="Minimum compatible RV length. Set to null to clear an inherited length.",
    )
    name: NonBlank = Field(description="Unique within the file.")
    provider: NonBlank = Field(
        description="A provider name or alias recognized by camply."
    )
    campgrounds: list[NonBlank] = Field(default_factory=list)
    recreation_areas: list[NonBlank] = Field(default_factory=list)
    campsites: list[NonBlank] = Field(default_factory=list)
    dates: list[DateWindow] = Field(min_length=1)
    state_file: NonBlank | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra=_omit_schema_default
    )

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
    """The configuration accepted by camply campsites --yaml-config."""

    model_config = ConfigDict(
        title="Camply CLI YAML configuration",
        json_schema_extra={"$schema": "https://json-schema.org/draft/2020-12/schema"},
    )

    version: int = Field(
        ge=_CONFIG_VERSION,
        le=_CONFIG_VERSION,
        description="CLI YAML configuration format version.",
        json_schema_extra={"const": _CONFIG_VERSION},
    )
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
    "dates": "provide at least one date window",
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
    if isinstance(data, dict):
        if (
            "version" not in data
            and "searches" not in data
            and _LEGACY_KEYS & data.keys()
        ):
            raise ConfigError(
                f"This is a legacy flat configuration. Set version: {_CONFIG_VERSION}, move the search into the searches list, and pair dates under dates."
            )
        version = data.get("version")
        if type(version) is not int:
            raise ConfigError(f"version: set version: {_CONFIG_VERSION} as an integer.")
        if version != _CONFIG_VERSION:
            raise ConfigError(
                f"Unsupported configuration version. This release supports version: {_CONFIG_VERSION}. Use a compatible camply release or migrate the file."
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


def _prepare_search(
    search: SearchInput,
    state_file: Path | None,
    provider: tuple[str, type[BaseProvider], int],
) -> PreparedSearch:
    name, provider_class, provider_id = provider
    areas = normalize_ids(search.recreation_areas, "recreation_areas")
    campgrounds = normalize_ids(search.campgrounds, "campgrounds")
    today = core_search.utc_today()
    start_dates = []
    end_dates = []
    window_weekdays = []
    for index, window in enumerate(search.dates):
        start = date.fromisoformat(window.start_date)
        end = date.fromisoformat(window.end_date)
        if end <= start:
            raise ConfigError(f"dates.{index}.end_date: must follow start_date.")
        if end <= today:
            raise ConfigError(
                f"dates.{index}.end_date: choose a window with current or future booking nights."
            )
        start_dates.append(start)
        end_dates.append(end)
        window_weekdays.append(
            allowed_weekdays(
                window.days if "days" in window.model_fields_set else search.days,
                weekends=(
                    window.weekends
                    if "weekends" in window.model_fields_set
                    else search.weekends
                ),
            )
        )
    try:
        request = core_search.normalize_request(
            start_dates=start_dates,
            end_dates=end_dates,
            window_weekdays=window_weekdays,
            nights=search.nights,
            campsites=normalize_ids(search.campsites, "campsites"),
            campsite_types=search.campsite_types,
            require_electric=search.electric,
            require_accessible=search.accessible,
            min_rv_length=search.rv_length,
            today=today,
        )
    except ValueError:
        raise ConfigError(
            "dates: choose windows and weekdays that allow the configured number of consecutive nights."
        ) from None
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


def _resolve_state_file(
    state_file: str, config_path: Path, directory: Path, state_paths: set[Path]
) -> Path:
    try:
        resolved = (directory / Path(state_file).expanduser()).resolve()
    except (OSError, RuntimeError, ValueError):
        raise ConfigError("state_file: could not resolve this path.") from None
    if resolved == config_path:
        raise ConfigError("state_file: path resolves to the configuration file.")
    if resolved in state_paths:
        raise ConfigError("state_file: path is already used by another search.")
    state_paths.add(resolved)
    return resolved


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
        location = f"searches.{index} {search.name!r}"
        provider = find_provider(search.provider)
        if provider is None:
            raise ConfigError(
                f"{location}: provider: choose a provider listed by camply providers."
            )
        location = f"{location} ({provider[0]})"
        try:
            if search.name in names:
                raise ConfigError("name: choose a unique search name.")
            names.add(search.name)
            state_file = None
            if search.state_file is not None:
                state_file = _resolve_state_file(
                    search.state_file, config_path, path.absolute().parent, state_paths
                )
            prepared.append(_prepare_search(search, state_file, provider))
        except click.UsageError as exc:
            raise ConfigError(f"{location}: {exc.format_message()}") from None
        except ConfigError as exc:
            raise ConfigError(f"{location}: {exc}") from None
    return prepared


if __name__ == "__main__":
    Path("docs/cli-yaml-config.schema.json").write_text(
        json.dumps(SearchConfig.model_json_schema(), indent=2) + "\n", encoding="utf-8"
    )
