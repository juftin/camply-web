"""Park, campground, and booking-category metadata exposed by GoingToCamp.

Attributes
----------
_NIGHTLY_BOOKING_MODEL : int
    GoingToCamp ``BookingModel.Nightly`` enum value.
_CAMPING_RESOURCE_TYPES : frozenset[int]
    GoingToCamp ``ResourceType`` values for frontcountry (0) and backcountry (3).
_BOOKING_MOORAGE_KEYWORDS : tuple[str, ...]
    Keywords identifying harbor/moorage booking categories rather than camping.
_RESOURCE_MOORAGE_KEYWORDS : tuple[str, ...]
    Keywords identifying harbor slips/buoys rather than camping or marine trails.
_STATE_CODE_LENGTH : int
    Length of a normalized state or province code.
_COUNTRY_CODE_LENGTH : int
    Length of a normalized ISO country code.
_LATITUDE_LIMIT : float
    Maximum valid absolute latitude in decimal degrees.
_LONGITUDE_LIMIT : float
    Maximum valid absolute longitude in decimal degrees.
_COORDINATE_PARTS : int
    Expected comma-separated parts in a ``"lat, lng"`` GPS string.
_REGION_MAP : dict[str, str]
    Full US state and Canadian province names mapped to two-letter codes.
_COUNTRY_MAP : dict[str, str]
    Country aliases mapped to two-letter ISO codes.
"""

from pydantic import BaseModel, Field

_NIGHTLY_BOOKING_MODEL = 0
_CAMPING_RESOURCE_TYPES = frozenset({0, 3})
_BOOKING_MOORAGE_KEYWORDS = ("marina", "moorage", "mooring", "buoy", "harbor")
_RESOURCE_MOORAGE_KEYWORDS = (
    "marina",
    "moorage",
    "mooring",
    "buoy",
    "slip",
    "harbor",
)
_STATE_CODE_LENGTH = 2
_COUNTRY_CODE_LENGTH = 2
_LATITUDE_LIMIT = 90.0
_LONGITUDE_LIMIT = 180.0
_COORDINATE_PARTS = 2

_REGION_MAP: dict[str, str] = {
    "alabama": "AL",
    "alaska": "AK",
    "alberta": "AB",
    "arizona": "AZ",
    "arkansas": "AR",
    "british columbia": "BC",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "manitoba": "MB",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new brunswick": "NB",
    "newfoundland and labrador": "NL",
    "newfoundland & labrador": "NL",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "northwest territories": "NT",
    "nova scotia": "NS",
    "nunavut": "NU",
    "ohio": "OH",
    "oklahoma": "OK",
    "ontario": "ON",
    "oregon": "OR",
    "pennsylvania": "PA",
    "prince edward island": "PE",
    "quebec": "QC",
    "québec": "QC",
    "rhode island": "RI",
    "saskatchewan": "SK",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "yukon": "YT",
}

_COUNTRY_MAP: dict[str, str] = {
    "usa": "US",
    "united states": "US",
    "united states of america": "US",
    "can": "CA",
    "canada": "CA",
}


class LocalizedText(BaseModel):
    """Culture-tagged text fields shared across GoingToCamp catalog entities."""

    cultureName: str | None = None
    displayName: str | None = None
    shortName: str | None = None
    fullName: str | None = None
    name: str | None = None
    value: str | None = None
    description: str | None = None
    city: str | None = None
    websiteUrl: str | None = None
    website: str | None = None


def preferred_localized(
    entries: list[LocalizedText] | None,
) -> LocalizedText | None:
    """Select an English entry when present, falling back to the first item."""
    if not entries:
        return None
    for entry in entries:
        if (entry.cultureName or "").lower().startswith("en"):
            return entry
    return entries[0]


def _first_non_empty(*candidates: str | None) -> str | None:
    """Return the first stripped non-empty string among candidates."""
    for candidate in candidates:
        if candidate is not None and candidate.strip():
            return candidate.strip()
    return None


def parse_gps_coordinates(
    raw: str | None,
) -> tuple[float | None, float | None]:
    """Parse ``"lat, lng"`` strings into validated decimal-degree floats."""
    if not raw or not raw.strip():
        return (None, None)
    parts = raw.split(",")
    if len(parts) != _COORDINATE_PARTS:
        return (None, None)
    try:
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
    except ValueError:
        return (None, None)
    if (
        (lat == 0.0 and lon == 0.0)
        or not (-_LATITUDE_LIMIT <= lat <= _LATITUDE_LIMIT)
        or not (-_LONGITUDE_LIMIT <= lon <= _LONGITUDE_LIMIT)
    ):
        return (None, None)
    return (lat, lon)


def normalize_state_code(raw: str | None, fallback: str | None) -> str | None:
    """Normalize two-letter state/province codes or full names to uppercase."""
    if not raw or not raw.strip():
        return fallback
    cleaned = raw.strip()
    if len(cleaned) == _STATE_CODE_LENGTH and cleaned.isalpha():
        return cleaned.upper()
    return _REGION_MAP.get(cleaned.lower(), fallback)


def normalize_country_code(raw: str | None, fallback: str) -> str:
    """Normalize ISO country codes or common aliases to uppercase two-letter codes."""
    if not raw or not raw.strip():
        return fallback
    cleaned = raw.strip()
    if len(cleaned) == _COUNTRY_CODE_LENGTH and cleaned.isalpha():
        return cleaned.upper()
    return _COUNTRY_MAP.get(cleaned.lower(), fallback)


class TransactionLocation(BaseModel):
    """A GoingToCamp park mapped to a ``RecreationArea``."""

    transactionLocationId: int
    isDisabled: bool | None = False
    gpsCoordinates: str | None = None
    regionCode: str | None = None
    rootMapId: int | None = None
    localizedValues: list[LocalizedText] = Field(default_factory=list)

    @property
    def display_name(self) -> str | None:
        """Return the preferred park name."""
        loc = preferred_localized(self.localizedValues)
        if loc is None:
            return None
        return _first_non_empty(loc.fullName, loc.shortName, loc.name)

    @property
    def description(self) -> str | None:
        """Return the localized park description when present."""
        loc = preferred_localized(self.localizedValues)
        return _first_non_empty(loc.description) if loc is not None else None

    @property
    def city(self) -> str | None:
        """Return the localized park city when present."""
        loc = preferred_localized(self.localizedValues)
        return _first_non_empty(loc.city) if loc is not None else None


class ResourceLocation(BaseModel):
    """A GoingToCamp campground/facility mapped to a ``Campground``."""

    resourceLocationId: int
    transactionLocationId: int | None = None
    rootMapId: int | None = None
    gpsCoordinates: str | None = None
    region: str | None = None
    country: str | None = None
    resourceCategoryIds: list[int] = Field(default_factory=list)
    localizedValues: list[LocalizedText] = Field(default_factory=list)

    @property
    def display_name(self) -> str | None:
        """Return the preferred campground or facility name."""
        loc = preferred_localized(self.localizedValues)
        if loc is None:
            return None
        return _first_non_empty(loc.fullName, loc.shortName, loc.name)

    @property
    def description(self) -> str | None:
        """Return the localized campground description when present."""
        loc = preferred_localized(self.localizedValues)
        return _first_non_empty(loc.description) if loc is not None else None

    @property
    def city(self) -> str | None:
        """Return the localized campground city when present."""
        loc = preferred_localized(self.localizedValues)
        return _first_non_empty(loc.city) if loc is not None else None


class ResourceCategory(BaseModel):
    """Describe a GoingToCamp resource category (campsite, cabin, shelter, slip)."""

    resourceCategoryId: int
    resourceType: int | None = None
    localizedValues: list[LocalizedText] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Return the localized category name."""
        loc = preferred_localized(self.localizedValues)
        if loc is None:
            return ""
        return _first_non_empty(loc.name, loc.fullName, loc.shortName, loc.value) or ""


class BookingCategory(BaseModel):
    """Describe a GoingToCamp booking category and its permitted resource categories."""

    bookingCategoryId: int
    bookingModel: int | None = None
    isDisabled: bool | None = False
    allowedResourceCategoryIds: list[int] = Field(default_factory=list)
    localizedValues: list[LocalizedText] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Return the localized booking category name."""
        loc = preferred_localized(self.localizedValues)
        if loc is None:
            return ""
        return _first_non_empty(loc.name, loc.fullName, loc.shortName, loc.value) or ""


def resolve_overnight_categories(
    booking_categories: list[BookingCategory],
    resource_categories: list[ResourceCategory],
) -> tuple[dict[int, BookingCategory], dict[int, ResourceCategory]]:
    """Resolve active nightly camping/lodging categories dynamically.

    Excludes disabled booking categories, non-nightly booking models (day use,
    rentals, seasonal), and harbor/marina moorage while retaining frontcountry
    and backcountry overnight camping and lodging categories.
    """
    nightly_booking: list[BookingCategory] = []
    referenced_resource_ids: set[int] = set()
    for bc in booking_categories:
        name_lower = bc.display_name.lower()
        if (
            bc.isDisabled is True
            or bc.bookingModel != _NIGHTLY_BOOKING_MODEL
            or any(word in name_lower for word in _BOOKING_MOORAGE_KEYWORDS)
        ):
            continue
        nightly_booking.append(bc)
        referenced_resource_ids.update(bc.allowedResourceCategoryIds)

    eligible_resources: dict[int, ResourceCategory] = {}
    for rc in resource_categories:
        name_lower = rc.display_name.lower()
        if (
            rc.resourceCategoryId not in referenced_resource_ids
            or rc.resourceType not in _CAMPING_RESOURCE_TYPES
            or any(word in name_lower for word in _RESOURCE_MOORAGE_KEYWORDS)
        ):
            continue
        eligible_resources[rc.resourceCategoryId] = rc

    eligible_booking = {
        bc.bookingCategoryId: bc
        for bc in nightly_booking
        if any(rc_id in eligible_resources for rc_id in bc.allowedResourceCategoryIds)
    }
    return eligible_booking, eligible_resources
