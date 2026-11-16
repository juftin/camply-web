# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Utility functions for providers.
"""

import math
import re
from collections.abc import Iterable
from decimal import Decimal

_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "of",
        "the",
        "and",
        "in",
        "on",
        "at",
        "to",
        "for",
        "with",
        "by",
    }
)


def normalize_name(name: str | None) -> str | None:
    """
    Normalize a campground or recreation area name.

    If the string is entirely uppercase or entirely lowercase, convert to
    title case (respecting common exception words).  Otherwise return
    the name unchanged — it is already properly cased.

    Exception words (lowered except when they are the first word):
    of, the, and, in, on, at, to, for, with, by

    Parameters
    ----------
    name : str | None
        The name to normalize.

    Returns
    -------
    str | None
        The normalized name, or ``None`` / empty string as-is.
    """
    if not name:
        return name

    if not name.isupper() and not name.islower():
        return name

    words = name.lower().split(" ")
    result: list[str] = []
    for i, word in enumerate(words):
        if not word:
            result.append(word)
            continue
        if i == 0 or word not in _EXCEPTIONS:
            result.append(word[0].upper() + word[1:])
        else:
            result.append(word)
    return " ".join(result)


_STATE_CODE_LENGTH = 2
_COUNTRY_CODE_LENGTH = 2

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
    "district of columbia": "DC",
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


def normalize_state_code(raw: str | None, fallback: str) -> str:
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


_METERS_TO_FEET = 3.28084
_METRIC_LENGTH_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:meters?|metres?|m)\b", re.IGNORECASE
)
_FEET_LENGTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:feet|foot|ft|')\b", re.IGNORECASE)
_PLAIN_NUMBER_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*$")
_RV_EQUIPMENT_KEYWORDS: tuple[str, ...] = (
    "rv",
    "trailer",
    "motorhome",
    "camper",
    "fifth wheel",
    "5th wheel",
    "pop up",
    "popup",
    "van",
    "vehicle",
    "car",
    "pickup",
)


def is_rv_equipment_name(name: str) -> bool:
    """Return True when an equipment label represents a drivable or towable vehicle."""
    lowered = name.lower()
    return any(keyword in lowered for keyword in _RV_EQUIPMENT_KEYWORDS)


def _floor_positive_feet(value: float | Decimal) -> int | None:
    """Floor a positive numeric value in feet conservatively to ``int``."""
    if isinstance(value, Decimal):
        if value.is_nan() or value.is_infinite() or value <= 0:
            return None
        feet = int(value)
    else:
        if math.isnan(value) or math.isinf(value) or value <= 0:
            return None
        feet = math.floor(value)
    return feet if feet > 0 else None


def _parse_string_length_feet(text: str) -> int | None:
    """Parse metric, foot-tagged, or bare numeric string lengths into whole feet."""
    if metric_match := _METRIC_LENGTH_RE.search(text):
        return _floor_positive_feet(float(metric_match.group(1)) * _METERS_TO_FEET)
    if feet_match := _FEET_LENGTH_RE.search(text):
        return _floor_positive_feet(float(feet_match.group(1)))
    if plain_match := _PLAIN_NUMBER_RE.match(text):
        return _floor_positive_feet(float(plain_match.group(1)))
    return None


def parse_vehicle_length_feet(raw: int | float | Decimal | str | None) -> int | None:
    """Convert numeric or unit-tagged vehicle lengths conservatively to whole feet.

    Parameters
    ----------
    raw : int | float | Decimal | str | None
        Raw vehicle, trailer, or driveway length value from a provider payload.

    Returns
    -------
    int | None
        Positive whole feet floored conservatively, or ``None`` for missing,
        zero, negative, or unparseable sentinel values.
    """
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float, Decimal)):
        return _floor_positive_feet(raw)
    text = raw.strip()
    return _parse_string_length_feet(text) if text else None


def normalize_equipment_labels(labels: Iterable[str | None]) -> list[str]:
    """Return stripped, sorted, deduplicated non-empty equipment labels."""
    cleaned = {label.strip() for label in labels if label and label.strip()}
    return sorted(cleaned)
