"""Portable, validated destination information shared by providers and APIs."""

from datetime import datetime
from ipaddress import ip_address
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, Field, field_validator

MAX_PHOTOS = 12
"""Maximum retained images per destination snapshot."""


def public_url(value: str | None) -> str | None:
    """Accept public HTTP links without credentials, local hosts, or controls."""
    if not isinstance(value, str) or any(char.isspace() for char in value):
        return None
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme not in {"http", "https"}
            or not host
            or parsed.username is not None
            or parsed.password is not None
            or host.endswith((".local", ".internal", ".localhost"))
            or any(not char.isprintable() for char in value)
        ):
            return None
        _ = parsed.port
        try:
            if not ip_address(host).is_global:
                return None
        except ValueError:
            if (
                "." not in host
                or host.endswith(".")
                or "\\" in host
                or host.rsplit(".", 1)[-1].isdigit()
                or host.rsplit(".", 1)[-1].startswith("0x")
            ):
                return None
    except ValueError:
        return None
    return value


def _validated_url(value: str) -> str:
    """Raise a model-validation error for an unsuitable external link."""
    validated = public_url(value)
    if validated is None:
        raise ValueError("Expected a public HTTP(S) URL without credentials")
    return validated


class DestinationPhoto(BaseModel):
    """One image belonging to the destination containing its snapshot."""

    url: str
    caption: str | None = None
    credit: str | None = None
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    is_primary: bool = False
    source_url: str | None = None

    _url = field_validator("url")(_validated_url)

    @field_validator("source_url")
    @classmethod
    def validate_source(cls, value: str | None) -> str | None:
        """Allow omitted source links while validating supplied ones."""
        return _validated_url(value) if value is not None else None


class DestinationLink(BaseModel):
    """A labeled public information or map link."""

    label: str
    url: str

    _url = field_validator("url")(_validated_url)


class DestinationFact(BaseModel):
    """A source-labeled fact retaining its original units and meaning."""

    label: str
    value: str


class DestinationDetails(BaseModel):
    """A complete cached destination snapshot with successful-refresh provenance."""

    source_url: str
    fetched_at: AwareDatetime
    description: str | None = None
    directions: str | None = None
    accessibility: str | None = None
    fee_information: str | None = None
    stay_limit: str | None = None
    photos: list[DestinationPhoto] = Field(default_factory=list)
    activities: list[str] = Field(default_factory=list)
    amenities: list[str] = Field(default_factory=list)
    links: list[DestinationLink] = Field(default_factory=list)
    hours: list[DestinationFact] = Field(default_factory=list)
    vehicle_limits: list[DestinationFact] = Field(default_factory=list)

    _url = field_validator("source_url")(_validated_url)

    @field_validator("photos")
    @classmethod
    def select_photos(cls, photos: list[DestinationPhoto]) -> list[DestinationPhoto]:
        """Prefer primary images and retain a deterministic, deduplicated gallery."""
        selected: dict[str, DestinationPhoto] = {}
        for photo in sorted(photos, key=lambda p: (not p.is_primary, p.url)):
            selected.setdefault(photo.url, photo)
        return list(selected.values())[:MAX_PHOTOS]

    @field_validator("fetched_at")
    @classmethod
    def normalize_freshness(cls, value: datetime) -> datetime:
        """Use a consistent UTC timestamp for portable freshness comparisons."""
        from datetime import timezone

        return value.astimezone(timezone.utc)
