"""Build a small public RIDB fixture from a downloaded archive."""

import argparse
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import ijson

_NARRATIVE_FIELDS = (
    "Directions",
    "AccessibilityText",
    "MapURL",
    "ReservationURL",
)
_CONTACT = re.compile(
    r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|(?<!\w)\+?\d?[ .-]*\(?\d{3}\)?[ .-]+\d{3}[ .-]+\d{4}(?!\w)"
)


def redact_contact(text: str) -> str:
    """Remove contact values from retained public text."""
    return _CONTACT.sub("[redacted]", text)


def compact_archive(
    source: Path, destination: Path, *, area_id: str, campground_id: str
) -> None:
    """Keep two destinations and the records needed by catalog and enrichment."""
    selected = {area_id, campground_id}
    with ZipFile(source) as original, ZipFile(destination, "x") as compact:
        selections = (
            (
                "RecAreas",
                "RecAreaID",
                {area_id},
                (
                    "RecAreaID",
                    "OrgRecAreaID",
                    "ParentOrgID",
                    "RecAreaName",
                    "RecAreaDescription",
                    "RecAreaLongitude",
                    "RecAreaLatitude",
                    "Reservable",
                    "Enabled",
                    "LastUpdatedDate",
                    "RecAreaFeeDescription",
                    "StayLimit",
                    *(f"RecArea{field}" for field in _NARRATIVE_FIELDS),
                ),
            ),
            (
                "Facilities",
                "FacilityID",
                {campground_id},
                (
                    "FacilityID",
                    "ParentRecAreaID",
                    "FacilityName",
                    "FacilityDescription",
                    "FacilityTypeDescription",
                    "FacilityLongitude",
                    "FacilityLatitude",
                    "Reservable",
                    "Enabled",
                    "FacilityUseFeeDescription",
                    "StayLimit",
                    *(f"Facility{field}" for field in _NARRATIVE_FIELDS),
                ),
            ),
            (
                "RecAreaAddresses",
                "RecAreaID",
                {area_id},
                (
                    "RecAreaID",
                    "City",
                    "RecAreaAddressType",
                    "AddressStateCode",
                    "PostalCode",
                    "AddressCountryCode",
                ),
            ),
            (
                "FacilityAddresses",
                "FacilityID",
                {campground_id},
                (
                    "FacilityID",
                    "City",
                    "FacilityAddressType",
                    "AddressStateCode",
                    "PostalCode",
                    "AddressCountryCode",
                ),
            ),
            (
                "Media",
                "EntityID",
                selected,
                (
                    "EntityID",
                    "EntityType",
                    "MediaType",
                    "URL",
                    "IsPrimary",
                ),
            ),
            (
                "Links",
                "EntityID",
                selected,
                ("EntityID", "EntityType", "URL", "LinkType"),
            ),
            (
                "EntityActivities",
                "EntityID",
                selected,
                (
                    "EntityID",
                    "EntityType",
                    "ActivityID",
                    "ActivityDescription",
                ),
            ),
        )
        for member, key, ids, fields in selections:
            _write_member(
                compact, member, _selected_records(original, member, key, ids, fields)
            )
        with original.open("Activities_API_v1.json") as stream:
            activities = [
                {key: row[key] for key in ("ActivityID", "ActivityName")}
                for row in ijson.items(stream, "RECDATA.item", use_float=True)
            ]
        _write_member(compact, "Activities", activities)


def _selected_records(
    archive: ZipFile, member: str, key: str, ids: set[str], fields: tuple[str, ...]
) -> list[dict]:
    """Keep allowlisted wire fields and remove contact strings."""
    with archive.open(f"{member}_API_v1.json") as stream:
        return [
            {
                field: redact_contact(item[field])
                if isinstance(item[field], str)
                else item[field]
                for field in fields
                if field in item
            }
            for item in ijson.items(stream, "RECDATA.item", use_float=True)
            if str(item.get(key)) in ids
        ]


def _write_member(archive: ZipFile, member: str, records: list[dict]) -> None:
    """Preserve the upstream member name and record envelope."""
    entry = ZipInfo(f"{member}_API_v1.json")
    archive.writestr(
        entry, json.dumps({"RECDATA": records}), compress_type=ZIP_DEFLATED
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--area-id", required=True)
    parser.add_argument("--campground-id", required=True)
    args = parser.parse_args()
    compact_archive(
        args.source,
        args.destination,
        area_id=args.area_id,
        campground_id=args.campground_id,
    )
