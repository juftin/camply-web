# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Utility functions for providers.
"""

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
