"""Synthetic RIDB archive association, bounded parsing, and failure regressions."""

import json
import zipfile
from pathlib import Path

import pytest

from camply.providers.enrichment import Destination
from camply.providers.recreation_gov.enrichment import read_details


def archive(tmp_path: Path, *, broken: bool = False, partial: bool = False) -> Path:
    """Write a complete small export including ambiguous and campsite media."""
    path = tmp_path / "metadata.zip"
    records = {
        "Facilities_API_v1.json": [
            {
                "FacilityID": "1",
                "FacilityTypeDescription": "Campground",
                "FacilityDirections": "Turn left",
                "FacilityAccessibilityText": "Paved path",
            },
            {"FacilityID": "collision", "FacilityTypeDescription": "Campground"},
            {"FacilityID": "tour", "FacilityTypeDescription": "Tour"},
        ],
        "RecAreas_API_v1.json": [
            {"RecAreaID": "2", "RecAreaDirections": "Follow the river"},
            {"RecAreaID": "collision"},
        ],
        "Media_API_v1.json": [
            {
                "EntityID": "1",
                "EntityType": "Asset",
                "MediaType": "Image",
                "URL": f"https://cdn.recreation.gov/{i:02}.jpg",
                "IsPrimary": i == 19,
                "Title": "Lake",
                "Credits": "Agency",
            }
            for i in range(20)
        ]
        + [
            {
                "EntityID": "2",
                "EntityType": "Asset",
                "MediaType": "Image",
                "URL": "https://cdn.recreation.gov/area.jpg",
            },
            {
                "EntityID": "1",
                "EntityType": "Campsite",
                "MediaType": "Image",
                "URL": "https://cdn.recreation.gov/site.jpg",
            },
            {
                "EntityID": "collision",
                "EntityType": "Asset",
                "MediaType": "Image",
                "URL": "https://cdn.recreation.gov/ambiguous.jpg",
            },
        ],
        "Links_API_v1.json": [
            {
                "EntityID": "1",
                "EntityType": "Facility",
                "URL": "https://parks.example.com/map",
                "Title": "Map",
            }
        ],
        "Activities_API_v1.json": [{"ActivityID": "5", "ActivityName": "Hiking"}],
        "EntityActivities_API_v1.json": [
            {"EntityID": "1", "EntityType": "Facility", "ActivityID": "5"}
        ],
    }
    for name, prefix, fee in (
        ("Facilities_API_v1.json", "Facility", "FacilityUseFeeDescription"),
        ("RecAreas_API_v1.json", "RecArea", "RecAreaFeeDescription"),
    ):
        for record in records[name]:
            for field in (
                f"{prefix}Directions",
                f"{prefix}AccessibilityText",
                fee,
                "StayLimit",
            ):
                record.setdefault(field, None)
    if partial:
        del records["Facilities_API_v1.json"][0]["FacilityDirections"]
    with zipfile.ZipFile(path, "w") as zipped:
        for name, rows in records.items():
            zipped.writestr(
                name,
                '{"RECDATA":['
                if broken and name == "Media_API_v1.json"
                else json.dumps({"RECDATA": rows}),
            )
    return path


def test_archive_matches_asset_catalogs_without_cross_entity_photos(
    tmp_path: Path,
) -> None:
    """RIDB Asset media is resolved against catalogs; ambiguous IDs are excluded."""
    selected = [
        Destination("campground", "1", "Synthetic campground"),
        Destination("recreation_area", "2", "Synthetic area"),
        Destination("campground", "collision", "Ambiguous campground"),
        Destination("recreation_area", "collision", "Ambiguous area"),
    ]
    details = read_details(archive(tmp_path), selected)
    campground = details[("campground", "1")]
    assert len(campground.photos) == 12
    assert campground.photos[0].url.endswith("19.jpg")
    assert all(not p.url.endswith("site.jpg") for p in campground.photos)
    assert campground.directions == "Turn left"
    assert campground.accessibility == "Paved path"
    assert campground.activities == ["Hiking"]
    assert campground.links[0].label == "Map"
    assert details[("recreation_area", "2")].photos[0].url.endswith("area.jpg")
    assert not details[("campground", "collision")].photos
    assert not details[("recreation_area", "collision")].photos


def test_incomplete_archive_is_not_a_successful_empty_snapshot(tmp_path: Path) -> None:
    """A malformed member aborts parsing before any snapshot can be persisted."""
    with pytest.raises(ValueError):
        read_details(
            archive(tmp_path, broken=True), [Destination("campground", "1", "Park")]
        )


def test_missing_member_and_missing_data_envelope_fail(tmp_path: Path) -> None:
    """Missing export sections are failures, rather than empty galleries."""
    path = tmp_path / "missing.zip"
    with zipfile.ZipFile(path, "w") as zipped:
        zipped.writestr("Facilities_API_v1.json", "{}")
    with pytest.raises((ValueError, KeyError)):
        read_details(path, [Destination("campground", "1", "Park")])


def test_missing_or_changed_destination_is_not_a_successful_empty_snapshot(
    tmp_path: Path,
) -> None:
    """Absent IDs and facilities converted to tours preserve their old snapshots."""
    details = read_details(
        archive(tmp_path),
        [
            Destination("campground", "1", "Park"),
            Destination("campground", "missing", "Retired"),
            Destination("campground", "tour", "Former campground"),
        ],
    )
    assert set(details) == {("campground", "1")}


def test_partial_destination_record_preserves_the_previous_snapshot(
    tmp_path: Path,
) -> None:
    """A schema-incomplete narrative is a source failure, not an explicit clearing."""
    with pytest.raises(ValueError, match="Incomplete RIDB destination narrative"):
        read_details(
            archive(tmp_path, partial=True), [Destination("campground", "1", "Park")]
        )
