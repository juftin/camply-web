"""Cached UseDirect destination photos and practical park information.

Attributes
----------
_ENTERPRISES : dict[int, str]
    Verified image-directory names on the configured public booking origins.
_IMAGE_PREFIX_BYTES : int
    Maximum decoded prefix consumed while validating a static destination image.
"""

import re
from datetime import datetime, timezone
from functools import partial
from typing import TYPE_CHECKING

from pydantic import BaseModel

from camply.providers.details import (
    DestinationDetails,
    DestinationFact,
    DestinationLink,
    DestinationPhoto,
    public_url,
)
from camply.providers.enrichment import Destination, refresh_destinations

if TYPE_CHECKING:
    from camply.providers.usedirect.provider import UseDirectProvider

_ENTERPRISES = {
    2: "California",
    3: "Florida",
    4: "Virginia",
    5: "Minnesota",
    6: "Ohio",
    7: "Arizona",
    8: "Missouri",
    9: "FairfaxFCPA",
    10: "OregonMetro",
    11: "NorthernTerritory",
}
_IMAGE_PREFIX_BYTES = 32


class ParkInformation(BaseModel):
    """Require the supported response fields before replacing a cached snapshot."""

    PlaceId: int
    Website: str | None
    ParkHeadquartersHours: str | None
    DayUseParkHours: str | None
    BackCountyTrailCampOfficeHours: str | None
    TrailerMaxLength: str | int | None
    CamperMotorHomeMaxLength: str | int | None
    DisplayMaxTrailerLengthOnWeb: bool


def _value(value: str | int | None) -> str | None:
    """Discard source placeholders without inventing hours or measurement units."""
    if value is None:
        return None
    text = str(value).strip()
    return (
        text
        if text.lower()
        not in {"", "0", "0.0", "not available", "n/a", "none", "unknown"}
        else None
    )


async def _image_exists(provider: "UseDirectProvider", url: str) -> bool:
    """Read only an image prefix, never following a different asset destination."""
    async with provider.async_client.stream(
        "GET", url, headers=provider.headers, timeout=15.0, follow_redirects=False
    ) as response:
        if response.status_code in {404, 410}:
            return False
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        prefix = await anext(response.aiter_bytes(chunk_size=_IMAGE_PREFIX_BYTES), b"")
        valid = (
            (content_type == "image/jpeg" and prefix.startswith(b"\xff\xd8\xff"))
            or (content_type == "image/png" and prefix.startswith(b"\x89PNG\r\n\x1a\n"))
            or (
                content_type == "image/webp"
                and prefix.startswith(b"RIFF")
                and prefix[8:12] == b"WEBP"
            )
        )
        if not valid:
            raise ValueError("UseDirect returned invalid destination image content")
        return True


def _park_facts(details: DestinationDetails, information: ParkInformation) -> None:
    """Populate supported park facts without guessing placeholder values or units."""
    website = public_url(information.Website or "")
    if website is not None:
        details.links = [DestinationLink(label="Official park website", url=website)]
    for label, raw in (
        ("Park office", information.ParkHeadquartersHours),
        ("Day use", information.DayUseParkHours),
        ("Backcountry office", information.BackCountyTrailCampOfficeHours),
    ):
        if value := _value(raw):
            details.hours.append(DestinationFact(label=label, value=value))
    if information.DisplayMaxTrailerLengthOnWeb:
        for label, raw_limit in (
            ("Maximum trailer length", information.TrailerMaxLength),
            (
                "Maximum camper/motorhome length",
                information.CamperMotorHomeMaxLength,
            ),
        ):
            if value := _value(raw_limit):
                details.vehicle_limits.append(DestinationFact(label=label, value=value))


async def fetch_details(
    provider: "UseDirectProvider", destination: Destination
) -> DestinationDetails | None:
    """Fetch one destination's own photo and supported park-level practical facts."""
    enterprise = _ENTERPRISES.get(provider.provider.id)
    if enterprise is None or destination.entity_type not in {
        "campground",
        "recreation_area",
    }:
        return None
    if not re.fullmatch(r"[0-9]+", destination.id):
        raise ValueError("UseDirect enrichment requires a numeric destination ID")
    if destination.entity_type == "recreation_area":
        source_url = provider.get_rec_area_url(destination.id)
        folder = "Place"
        response = await provider._request(
            "GET", f"fd/placeinfo/additional-place-info/{destination.id}"
        )
        information = ParkInformation.model_validate_json(response.content)
        if information.PlaceId != int(destination.id):
            raise ValueError("UseDirect returned another park's information")
    else:
        source_url = provider.get_campground_url(
            destination.id, rec_area_id=destination.recreation_area_id
        )
        folder = "Facility"
        information = None
    image_url = (
        f"{provider.booking_url.rstrip('/')}/images/{enterprise}/ParkImages/"
        f"{folder}/{destination.id}.jpg"
    )
    photos = (
        [DestinationPhoto(url=image_url, source_url=source_url, is_primary=True)]
        if await _image_exists(provider, image_url)
        else []
    )
    details = DestinationDetails(
        source_url=source_url,
        fetched_at=datetime.now(tz=timezone.utc),
        photos=photos,
    )
    if information is not None:
        _park_facts(details, information)
    return details


async def enrich_metadata(provider: "UseDirectProvider") -> None:
    """Refresh a bounded stale destination batch independently of catalog ingestion."""
    await refresh_destinations(
        provider_id=provider.provider.id, fetch=partial(fetch_details, provider)
    )
