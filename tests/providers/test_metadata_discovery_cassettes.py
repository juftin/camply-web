"""Verify public discovery and exact resolution with recorded provider responses."""

import json

import pytest

from camply.providers import PROVIDERS
from tests.providers.metadata_cases import DISCOVERY_TARGETS, MetadataTarget
from tests.providers.metadata_replay import metadata_replay


@pytest.mark.anyio
@pytest.mark.parametrize("case", DISCOVERY_TARGETS, ids=lambda case: case.key)
async def test_metadata_discovery(
    case: MetadataTarget, pytestconfig: pytest.Config
) -> None:
    """Find the same native destination via search and exact lookup."""
    provider = PROVIDERS[case.provider_id]()
    try:
        with metadata_replay(
            pytestconfig, operation="discovery", case=case
        ) as cassette:
            found = await provider.search(
                case.query, state=case.state, entity_type="campground", limit=5
            )
            result = next(
                item for item in found if item.campground_id == case.campground_id
            )
            assert result.campground_name == case.campground_name
            assert (result.state, result.country) == (case.state, case.country)
            assert result.booking_url == case.booking_url
            assert result.recreation_area_id == case.area_id
            if case.family == "reserve-america" and pytestconfig.getoption(
                "record_provider_metadata"
            ):
                # Capture the selected state catalog, rather than crawling every US state.
                await provider._request("config/brand", {"brandName": "RA"})
                return
            exact = await provider.get_campground(case.campground_id)
            assert exact == result
            if case.area_id is None:
                assert (
                    await provider.search(case.query, entity_type="recreation_area")
                    == []
                )
                with pytest.raises(ValueError, match="Unknown recreation-area"):
                    await provider.get_recreation_area(case.campground_id)
                eligible = await provider.search(
                    state=case.state, entity_type="campground", limit=1000
                )
                assert not {item.campground_id for item in eligible}.intersection(
                    case.excluded
                )
                return
            area = await provider.get_recreation_area(case.area_id)
            assert (area.recreation_area_id, area.recreation_area_name) == (
                case.area_id,
                case.area_name,
            )
            members = [item async for item in provider.iter_campgrounds(case.area_id)]
            member_ids = {item.campground_id for item in members}
            assert member_ids == set(case.siblings)
            assert all(item.recreation_area_id == case.area_id for item in members)
            assert member_ids.isdisjoint(case.excluded)
            if case.family == "usedirect":
                # Require the negative examples to survive recording and sanitization.
                unbookable_ids = {
                    str(facility["FacilityId"])
                    for request, response in cassette.data
                    if request.path.endswith("/fd/facilities")
                    for facility in json.loads(response["body"]["string"])
                    if str(facility["PlaceId"]) == case.area_id
                    and facility.get("AllowWebBooking") is not True
                }
                assert case.excluded and set(case.excluded) <= unbookable_ids
    finally:
        await provider.async_client.aclose()
