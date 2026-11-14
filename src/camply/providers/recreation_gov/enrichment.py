"""Stream destination enrichment from the provider's existing RIDB archive."""

import asyncio
import zipfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ijson  # type: ignore[import-untyped]

from camply.providers.details import (
    DestinationDetails,
    DestinationLink,
    DestinationPhoto,
    public_url,
)
from camply.providers.enrichment import (
    Destination,
    mark_attempt,
    save_details,
    stale_destinations,
)

if TYPE_CHECKING:
    from camply.providers.recreation_gov.provider import RecreationGovProvider


def _records(zipped: zipfile.ZipFile, name: str) -> Iterator[dict[str, Any]]:
    """Fully validate a RIDB envelope while incrementally yielding its records."""
    with zipped.open(name) as member:
        found = False

        def events() -> Iterator[tuple[str, str, Any]]:
            """Reject missing envelopes instead of accepting a false empty snapshot."""
            nonlocal found
            try:
                for prefix, event, value in ijson.parse(member):
                    if prefix == "RECDATA" and event == "start_array":
                        found = True
                    yield prefix, event, value
            except ijson.JSONError as exc:
                raise ValueError(f"Invalid RIDB JSON in {name}") from exc
            if not found:
                raise ValueError(f"Missing RECDATA array in {name}")

        for record in ijson.items(events(), "RECDATA.item"):
            if not isinstance(record, dict):
                raise ValueError(f"Invalid record in {name}")
            yield record


def _text(value: Any) -> str | None:
    """Retain populated source text without manufacturing missing values."""
    return value.strip() or None if isinstance(value, str) else None


def _narrative(
    details: DestinationDetails, record: dict[str, Any], prefix: str
) -> None:
    """Copy source narrative and official links to their existing destination."""
    required = {
        f"{prefix}Directions",
        f"{prefix}AccessibilityText",
        "FacilityUseFeeDescription"
        if prefix == "Facility"
        else "RecAreaFeeDescription",
        "StayLimit",
    }
    if not required.issubset(record):
        raise ValueError("Incomplete RIDB destination narrative")
    details.directions = _text(record.get(f"{prefix}Directions"))
    details.accessibility = _text(record.get(f"{prefix}AccessibilityText"))
    details.fee_information = _text(
        record.get(
            f"{prefix}UseFeeDescription"
            if prefix == "Facility"
            else "RecAreaFeeDescription"
        )
    )
    details.stay_limit = _text(record.get("StayLimit"))
    for field, label in (("MapURL", "Map"), ("ReservationURL", "Official information")):
        if url := public_url(record.get(f"{prefix}{field}")):
            details.links.append(DestinationLink(label=label, url=url))


def _entity_key(
    record: dict[str, Any], catalog: dict[str, set[str]]
) -> tuple[str, str] | None:
    """Resolve RIDB Asset identities, refusing ambiguous cross-catalog matches."""
    identity = str(record.get("EntityID", ""))
    kind = record.get("EntityType")
    if kind == "Asset":
        kinds = catalog.get(identity, set())
        if len(kinds) != 1:
            return None
        return (next(iter(kinds)), identity)
    if kind in {"Facility", "Campground"}:
        return ("campground", identity)
    if kind == "Rec Area":
        return ("recreation_area", identity)
    return None


def _add_image(details: DestinationDetails, record: dict[str, Any]) -> None:
    """Retain a bounded, primary-first set of valid destination images."""
    url = public_url(record.get("URL"))
    if url is None:
        return
    title = _text(record.get("Title"))
    description = _text(record.get("Description"))
    caption = (
        " — ".join(dict.fromkeys(value for value in (title, description) if value))
        or None
    )
    dimensions = {
        name.lower(): value
        for name in ("Width", "Height")
        if isinstance(value := record.get(name), int) and value > 0
    }
    photo = DestinationPhoto(
        url=url,
        caption=caption,
        credit=_text(record.get("Credits")),
        is_primary=record.get("IsPrimary") is True,
        source_url=details.source_url,
        **dimensions,
    )
    details.photos = DestinationDetails.select_photos([*details.photos, photo])


def _read_links(
    zipped: zipfile.ZipFile,
    catalog: dict[str, set[str]],
    snapshots: dict[tuple[str, str], DestinationDetails],
) -> None:
    """Retain distinct official links for the selected destinations only."""
    for record in _records(zipped, "Links_API_v1.json"):
        key = _entity_key(record, catalog)
        url = public_url(record.get("URL"))
        if key in snapshots and url:
            details = snapshots[key]
            link = DestinationLink(
                label=_text(record.get("Title"))
                or _text(record.get("LinkType"))
                or "Official information",
                url=url,
            )
            if all(existing.url != url for existing in details.links):
                details.links.append(link)


def read_details(
    path: Path, selected: list[Destination]
) -> dict[tuple[str, str], DestinationDetails]:
    """Parse complete members before exposing snapshots, with bounded photo memory.

    Media and links use ``Asset`` IDs in current exports, unlike activities.
    Resolve those IDs against both catalogs and skip any ambiguous identities.
    Only selected destinations accumulate details; campsite and tour media never do.
    """
    from camply.providers.recreation_gov.provider import RecreationGovProvider

    now = datetime.now(timezone.utc)
    snapshots = {
        (d.entity_type, d.id): DestinationDetails(
            source_url=RecreationGovProvider.get_campground_url(
                d.id, rec_area_id=d.recreation_area_id
            )
            if d.entity_type == "campground"
            else RecreationGovProvider.get_rec_area_url(d.id),
            fetched_at=now,
        )
        for d in selected
    }
    catalog: dict[str, set[str]] = {}
    matched: set[tuple[str, str]] = set()
    with zipfile.ZipFile(path) as zipped:
        for name, identity, kind, prefix in (
            ("Facilities_API_v1.json", "FacilityID", "campground", "Facility"),
            ("RecAreas_API_v1.json", "RecAreaID", "recreation_area", "RecArea"),
        ):
            for record in _records(zipped, name):
                record_id = str(record[identity])
                catalog.setdefault(record_id, set()).add(kind)
                if (
                    kind == "campground"
                    and record.get("FacilityTypeDescription") != "Campground"
                ):
                    continue
                if details := snapshots.get((kind, record_id)):
                    matched.add((kind, record_id))
                    _narrative(details, record, prefix)
        snapshots = {
            key: details for key, details in snapshots.items() if key in matched
        }
        for record in _records(zipped, "Media_API_v1.json"):
            key = _entity_key(record, catalog)
            if record.get("MediaType") == "Image" and key in snapshots:
                _add_image(snapshots[key], record)
        _read_links(zipped, catalog, snapshots)
        activities = {
            str(record["ActivityID"]): _text(record.get("ActivityName"))
            for record in _records(zipped, "Activities_API_v1.json")
        }
        for record in _records(zipped, "EntityActivities_API_v1.json"):
            key = _entity_key(record, catalog)
            if key in snapshots:
                activity_name = activities.get(str(record.get("ActivityID"))) or _text(
                    record.get("ActivityDescription")
                )
                if activity_name and activity_name not in snapshots[key].activities:
                    snapshots[key].activities.append(activity_name)
    return {key: details for key, details in snapshots.items() if key in matched}


async def enrich_metadata(provider: "RecreationGovProvider") -> None:
    """Enrich one stale batch from the existing cached export without extra APIs."""
    selected = await stale_destinations(provider.provider.id)
    selected = [
        destination
        for destination in selected
        if await mark_attempt(provider.provider.id, destination)
    ]
    if not selected:
        return
    path = await provider.download_offline_data()
    snapshots = await asyncio.to_thread(read_details, path, selected)
    for destination in selected:
        if details := snapshots.get((destination.entity_type, destination.id)):
            await save_details(provider.provider.id, destination, details)
