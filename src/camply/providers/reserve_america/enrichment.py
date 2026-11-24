"""Cache verified ReserveAmerica facility narratives and original-photo galleries."""

from datetime import datetime, timezone
from functools import partial
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote, urljoin, urlsplit

from pydantic import BaseModel
from sqlalchemy import update

from camply.db.config import db
from camply.db.models import Campground
from camply.providers.details import (
    DestinationDetails,
    DestinationFact,
    DestinationLink,
    DestinationPhoto,
    public_url,
)
from camply.providers.enrichment import Destination, refresh_destinations
from camply.providers.reserve_america.models.api import split_facility_id

_ELECTRIC_NEGATIVE = ("non-electric", "non electric", "no electric", "unelectrified")
_ONSITE_DISTANCE_CODE = "2000"

if TYPE_CHECKING:
    from camply.providers.reserve_america.provider import ReserveAmericaProvider


class OriginalPhoto(BaseModel):
    """An original rendition; the paired facilityPhotos list is intentionally unused."""

    photoURL: str
    description: str | None = None


class Narrative(BaseModel):
    """Provider-authored content retained for the existing safe HTML renderer."""

    content: str | None = None


class Directions(BaseModel):
    """The facility-level directions section may explicitly contain no content."""

    directionsInfo: Narrative | None = None


class Amenity(BaseModel):
    """Keep nearby-facility distances separate from on-site amenity claims."""

    name: str
    distanceCode: str | None = None
    distanceName: str | None = None


class RelatedLink(BaseModel):
    """A labeled public information link supplied by the facility."""

    linkLabel: str | None = None
    linkTitle: str | None = None
    linkURL: str


class DatePeriod(BaseModel):
    """Preserve optional source dates rather than guessing recurring seasons."""

    startDate: str | None = None
    endDate: str | None = None


class Season(BaseModel):
    """A named seasonal date range, where the provider supplies one."""

    name: str | None = None
    datePeriod: DatePeriod | None = None


class FacilityInformation(BaseModel):
    """Require complete supported sections so partial successes cannot erase caches."""

    id: int
    contrCode: str
    originalPhotos: list[OriginalPhoto]
    notes: list[Narrative]
    directions: Directions
    amenities: list[Amenity]
    relatedLinks: list[RelatedLink]
    feesCancellationsDescription: str | None
    seasons: list[Season]


def _photo_url(raw: str, *, contract: str, facility: str, origin: str) -> str:
    """Join known original paths without double-escaping existing percent sequences."""
    parsed = urlsplit(raw)
    base = urlsplit(origin)
    if parsed.scheme and parsed.scheme != base.scheme:
        raise ValueError("ReserveAmerica returned an untrusted image scheme")
    if parsed.netloc and (parsed.scheme != base.scheme or parsed.netloc != base.netloc):
        raise ValueError("ReserveAmerica returned an untrusted image origin")
    prefix = f"/webphotos/originals/{contract}/pid{facility}/"
    if (
        not parsed.path.startswith(prefix)
        or ".." in unquote(parsed.path).split("/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "ReserveAmerica returned an image outside the requested facility"
        )
    return urljoin(origin, quote(parsed.path, safe="/%"))


def _season_facts(seasons: list[Season]) -> list[DestinationFact]:
    """Describe only provider-supplied seasonal dates, preserving their labels."""
    facts = []
    for season in seasons:
        period = season.datePeriod
        if period is None:
            continue
        dates = [value for value in (period.startDate, period.endDate) if value]
        if dates:
            facts.append(
                DestinationFact(
                    label=f"Season: {season.name or 'Camping'}", value=" - ".join(dates)
                )
            )
    return facts


def _extract_onsite_capabilities(amenities: list[Amenity]) -> dict[str, bool]:
    """Derive verified campground amenity booleans strictly from on-site entries."""
    flags = {
        "has_electric": False,
        "has_water": False,
        "has_sewer": False,
        "pets_allowed": False,
        "ada_accessible": False,
    }
    for amenity in amenities:
        if amenity.distanceCode != _ONSITE_DISTANCE_CODE:
            continue
        low = amenity.name.strip().lower()
        if not low:
            continue
        if "electric" in low and not any(neg in low for neg in _ELECTRIC_NEGATIVE):
            flags["has_electric"] = True
        if (
            any(kw in low for kw in ("water hookup", "drinking water", "potable water"))
            or low == "water"
        ):
            flags["has_water"] = True
        if "sewer" in low:
            flags["has_sewer"] = True
        if "pet" in low and "no pet" not in low:
            flags["pets_allowed"] = True
        if "ada" in low or "accessible" in low:
            flags["ada_accessible"] = True
    return flags


async def fetch_details(
    provider: "ReserveAmericaProvider",
    destination: Destination,
    *,
    capabilities_out: dict[str, dict[str, bool]] | None = None,
) -> DestinationDetails | None:
    """Translate one complete native facility response into cached destination details."""
    if destination.entity_type != "campground":
        return None
    contract, facility = split_facility_id(destination.id)
    information = FacilityInformation.model_validate(
        await provider._request(
            f"facilities/{contract}/{facility}", {"detailsOnly": "false"}
        )
    )
    if information.id != int(facility) or information.contrCode != contract:
        raise ValueError("ReserveAmerica returned another facility's information")
    if capabilities_out is not None:
        capabilities_out[destination.id] = _extract_onsite_capabilities(
            information.amenities
        )
    source_url = provider.get_campground_url(destination.id)
    api = urlsplit(provider.api_url)
    origin = f"{api.scheme}://{api.netloc}"
    photos: dict[str, DestinationPhoto] = {}
    for index, photo in enumerate(information.originalPhotos):
        url = _photo_url(
            photo.photoURL, contract=contract, facility=facility, origin=origin
        )
        photos.setdefault(
            url,
            DestinationPhoto(
                url=url,
                caption=(photo.description or "").strip() or None,
                source_url=source_url,
                is_primary=index == 0,
            ),
        )
    amenities = []
    for amenity in information.amenities:
        name = amenity.name.strip()
        if not name:
            continue
        if amenity.distanceCode != "2000":
            name += (
                f" ({(amenity.distanceName or '').strip() or 'Location not specified'})"
            )
        amenities.append(name)
    links = []
    for link in information.relatedLinks:
        if link_url := public_url(link.linkURL):
            links.append(
                DestinationLink(
                    label=(
                        link.linkLabel or link.linkTitle or "More information"
                    ).strip(),
                    url=link_url,
                )
            )
    return DestinationDetails(
        source_url=source_url,
        fetched_at=datetime.now(tz=timezone.utc),
        description="\n\n".join(
            note.content for note in information.notes if note.content
        )
        or None,
        directions=information.directions.directionsInfo.content
        if information.directions.directionsInfo is not None
        else None,
        fee_information=information.feesCancellationsDescription,
        photos=list(photos.values()),
        amenities=amenities,
        links=links,
        hours=_season_facts(information.seasons),
    )


async def enrich_metadata(provider: "ReserveAmericaProvider") -> None:
    """Use the shared bounded refresh while retaining existing anonymous sessions."""
    extracted: dict[str, dict[str, bool]] = {}
    updated = False

    async def apply_amenities(
        destination: Destination, _details: DestinationDetails
    ) -> None:
        nonlocal updated
        flags = extracted.get(destination.id)
        if destination.entity_type != "campground" or not flags:
            return
        async with db.get_session() as session:
            async with session.begin():
                await session.execute(
                    update(Campground)
                    .where(
                        Campground.provider_id == provider.provider.id,
                        Campground.id == destination.id,
                    )
                    .values(**flags)
                )
        updated = True

    await refresh_destinations(
        provider_id=provider.provider.id,
        fetch=partial(fetch_details, provider, capabilities_out=extracted),
        on_details=apply_amenities,
    )
    if updated:
        async with db.get_session() as session:
            async with session.begin():
                await provider.populate_search_table(session, commit=False)
