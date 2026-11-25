"""Limit metadata recordings to the public fields consumed by provider adapters."""

import json
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from pydantic import TypeAdapter
from vcr.request import Request

from camply.providers.going_to_camp.models.metadata import (
    ResourceLocation,
    TransactionLocation,
)
from camply.providers.recreation_gov.models.api import (
    RecDotGovSearchResponse,
)
from camply.providers.reserve_america.enrichment import FacilityInformation
from camply.providers.reserve_america.models.api import BrandCatalog, Facility, Page
from camply.providers.usedirect.enrichment import ParkInformation
from camply.providers.usedirect.models.metadata import Facility as UseDirectFacility
from camply.providers.usedirect.models.metadata import Place
from tests.providers.cassette_sanitization import (
    _GRID_FIELDS,
    _PUBLIC_QUERY_FIELDS,
    _remove_private_fields,
    _response_schema,
    sanitize_interaction,
)
from tests.providers.metadata_archive import redact_contact
from tests.providers.metadata_cases import MetadataTarget

_AREA_CATALOGS = {
    "/api/transactionlocation": (TransactionLocation, "transactionLocationId"),
    "/api/resourceLocation": (ResourceLocation, "transactionLocationId"),
    "/fd/places": (Place, "PlaceId"),
    "/fd/facilities": (UseDirectFacility, "PlaceId"),
}

_METADATA_MODELS = {
    "/api/search": RecDotGovSearchResponse,
    "/jaxrs-json/search": Page[Facility],
    "/additional-place-info/": ParkInformation,
    "/jaxrs-json/facilities/": FacilityInformation,
}


def _metadata_payload(path: str, raw: Any, case: MetadataTarget) -> Any:
    """Preserve the selected metadata subset and its original response shape."""
    for route, (model, field) in _AREA_CATALOGS.items():
        if path.endswith(route):
            return _selected_rows(model, raw, field, case.area_id)
    if path.endswith("/config/brand"):
        catalog = BrandCatalog.model_validate(raw)
        return {
            "states": [
                state.model_dump(mode="json")
                for state in catalog.states
                if state.countryCode == "USA" and state.stateCode == case.state
            ]
        }
    schema = next(
        (
            model
            for route, model in _METADATA_MODELS.items()
            if path == route or (route.endswith("/") and route in path)
        ),
        None,
    )
    if schema is None:
        schema = _response_schema(path, raw)
    adapter = TypeAdapter(schema)
    return adapter.dump_python(
        adapter.validate_python(raw), mode="json", exclude_unset=True
    )


def _selected_rows(
    model: type, raw: list[dict[str, Any]], field: str, value: str | None
) -> list[dict[str, Any]]:
    """Keep all records attached to the selected parent or native ID."""
    return [
        model.model_validate(item).model_dump(mode="json", exclude_unset=True)
        for item in raw
        if str(item.get(field)) == value
    ]


def sanitize_metadata_interaction(
    request: Request, response: dict[str, Any], *, case: MetadataTarget
) -> tuple[Request, dict[str, Any]]:
    """Save compact discovery, catalog, and detail responses with synthetic sessions."""
    request.headers.clear()
    url = urlsplit(request.uri)
    extra = {"q", "brandName", "stype", "tstc", "interest", "detailsOnly"}
    if (
        url.username
        or url.password
        or url.fragment
        or any(
            key not in _PUBLIC_QUERY_FIELDS | extra for key, _ in parse_qsl(url.query)
        )
    ):
        raise ValueError("Unexpected fields in a metadata recording URL")
    if request.body and (
        not url.path.endswith("/search/grid")
        or not json.loads(request.body).keys() <= _GRID_FIELDS
    ):
        raise ValueError("Unexpected metadata recording body")
    if url.path == "/explore/search-results":
        return sanitize_interaction(request, response, case=case)
    response["headers"] = {
        name: value
        for name, value in response["headers"].items()
        if name.lower() == "content-type"
    }
    if "/ParkImages/" in url.path:
        response["body"]["string"] = (
            response["body"]["string"][:32] if response["status"]["code"] == 200 else ""
        )
        return request, response
    raw = json.loads(response["body"]["string"])
    data = _metadata_payload(url.path, raw, case)
    _remove_private_fields(data)
    response["body"]["string"] = redact_contact(json.dumps(data, separators=(",", ":")))
    return request, response
