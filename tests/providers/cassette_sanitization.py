"""Keep the public inventory needed for replay and discard unrelated data."""

import json
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from pydantic import TypeAdapter
from vcr.request import Request

from camply.providers.going_to_camp.models.api import (
    AttributeDefinition,
    EquipmentCategory,
    MapAvailabilityResponse,
    Resource,
)
from camply.providers.going_to_camp.models.metadata import (
    BookingCategory,
    ResourceCategory,
    ResourceLocation,
)
from camply.providers.recreation_gov.models.api import (
    CampsiteAvailabilityResponse,
    RecDotGovCampsiteResponse,
)
from camply.providers.reserve_america.models.api import Page, Site
from camply.providers.usedirect.models.api import AvailabilityResponse, SearchFilters
from tests.providers.availability_cases import AvailabilityCase

_RESPONSE_SCHEMAS = {
    "/api/resourceLocation": list[ResourceLocation],
    "/api/bookingcategories": list[BookingCategory],
    "/api/resourcecategory": list[ResourceCategory],
    "/api/equipment": list[EquipmentCategory],
    "/api/resourcelocation/resources": dict[str, Resource],
    "/api/availability/map": MapAvailabilityResponse,
    "/api/search/campsites": RecDotGovCampsiteResponse,
    "/search/filters": SearchFilters,
    "/search/grid": AvailabilityResponse,
    "/api/camps/availability/": CampsiteAvailabilityResponse,
    "/jaxrs-json/products/": Page[Site],
}
_PUBLIC_QUERY_FIELDS = {
    "start",
    "size",
    "fq",
    "include_non_site_specific_campsites",
    "start_date",
    "resourceLocationId",
    "mapId",
    "bookingCategoryId",
    "startDate",
    "endDate",
    "getDailyAvailability",
    "isReserving",
    "gad",
    "gal",
    "rcp",
    "rcs",
}
_GRID_FIELDS = {
    "FacilityId",
    "StartDate",
    "EndDate",
    "WebOnly",
    "InSeasonOnly",
    "UnitSort",
}


def sanitize_interaction(
    request: Request, response: dict[str, Any], *, case: AvailabilityCase
) -> tuple[Request, dict[str, Any]]:
    """Project the response onto the public fields consumed by the adapter."""
    request.headers.clear()
    url = urlsplit(request.uri)
    if (
        url.username
        or url.password
        or url.fragment
        or any(key not in _PUBLIC_QUERY_FIELDS for key, _ in parse_qsl(url.query))
    ):
        raise ValueError("Unexpected fields in a provider recording URL")
    if request.body:
        if not url.path.endswith("/search/grid") or not (
            json.loads(request.body).keys() <= _GRID_FIELDS
        ):
            raise ValueError("Unexpected provider recording body")

    if url.path == "/explore/search-results":
        # ReserveAmerica bootstraps anonymously. Replay needs no live page or token.
        response["body"]["string"] = ""
        response["headers"] = {
            "set-cookie": [
                "idToken=synthetic-cassette-token; Path=/",
                "a1Data=synthetic-cassette-session; Path=/",
            ]
        }
        return request, response

    response["headers"] = {
        name: value
        for name, value in response["headers"].items()
        if name.lower() == "content-type"
    }
    raw = json.loads(response["body"]["string"])
    schema = _response_schema(url.path, raw)
    data = _project_inventory(schema, raw, case=case)
    _remove_private_fields(data)
    response["body"]["string"] = json.dumps(data, separators=(",", ":"))
    return request, response


def _response_schema(path: str, raw: Any) -> Any:
    """Select the wire model consumed by this provider endpoint."""
    if path == "/api/attribute/filterable":
        return (
            dict[str, AttributeDefinition]
            if isinstance(raw, dict)
            else list[AttributeDefinition]
        )
    for route, schema in _RESPONSE_SCHEMAS.items():
        if path == route or (route.endswith("/") and path.startswith(route)):
            return schema
        if route in {"/search/grid", "/search/filters"} and path.endswith(route):
            return schema
    raise ValueError(f"No cassette sanitizer for {path}")


def _project_inventory(schema: Any, raw: Any, *, case: AvailabilityCase) -> Any:
    """Limit the wire model to the scenario without changing availability status."""
    adapter = TypeAdapter(schema)
    if schema == list[ResourceLocation]:
        raw = [
            site
            for site in raw
            if str(site["resourceLocationId"]) == case.campground_id
        ]
    data = adapter.dump_python(
        adapter.validate_python(raw), mode="json", exclude_unset=True
    )
    if (
        schema is RecDotGovCampsiteResponse
        and data["start"] == 0
        and len(data["campsites"]) >= data["total"]
    ):
        site_ids = {case.campsite_id, *case.excluded_site_ids}
        data["campsites"] = [
            site for site in data["campsites"] if str(site["campsite_id"]) in site_ids
        ]
        data["total"] = len(data["campsites"])
    if schema is CampsiteAvailabilityResponse:
        site_ids = {case.campsite_id, *case.excluded_site_ids}
        data["campsites"] = {
            key: site for key, site in data["campsites"].items() if key in site_ids
        }
        first = (case.arrival - timedelta(days=1)).isoformat()
        last = case.checkout.isoformat()
        for site in data["campsites"].values():
            site["availabilities"] = {
                night: status
                for night, status in site["availabilities"].items()
                if first <= night[:10] <= last
            }
    if schema is Page[Site]:
        first = case.arrival.isoformat()
        last = case.checkout.isoformat()
        for site in data["records"]:
            site["availabilityGrid"] = [
                night
                for night in site["availabilityGrid"]
                if first <= night["date"] <= last
            ]
    return data


def _remove_private_fields(data: Any) -> None:
    """Remove unneeded free text and replace private lock data with a marker."""
    if isinstance(data, dict):
        for key in ("description", "website", "websiteUrl", "gpsCoordinates"):
            data.pop(key, None)
        if data.get("Lock") is not None:
            data["Lock"] = {"synthetic": True}
        for value in data.values():
            _remove_private_fields(value)
    elif isinstance(data, list):
        for value in data:
            _remove_private_fields(value)
