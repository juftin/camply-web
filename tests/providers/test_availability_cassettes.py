"""Replay known-open searches through the real provider and search layers."""

from dataclasses import replace
from datetime import date, timedelta
from functools import partial
from pathlib import Path
from unittest.mock import patch

import pytest
import vcr

from camply.core.search import DateWindow, SearchRequest, check_availability
from camply.providers import PROVIDERS
from camply.providers.dto import CampgroundSearchResult, CampsiteDTO, CampsiteType
from tests.providers.availability_cases import (
    CASES,
    AvailabilityCase,
    validate_availability_cases,
)
from tests.providers.cassette_sanitization import sanitize_interaction

validate_availability_cases(CASES)

CASSETTE_ROOT = Path(__file__).with_name("cassettes") / "availability"
MATCHERS = ("method", "scheme", "host", "port", "path", "query", "body")
SEASONAL_GAPS = {
    20: "Nova Scotia reservations open in April 2027.",
    21: "Birds Hill returned no bookable sites in the sampled spring windows.",
    22: "Butter Pot returned no bookable sites in the sampled spring windows.",
    24: "Backus returned no bookable sites in the sampled spring windows.",
    25: "Falls Reserve is closed for camping.",
    26: "St. Clair reservations open January 11, 2027.",
}
EQUIPMENT_FALLBACKS = {
    11: "Florence Falls 2WD inventory has no vehicle lengths or category contrast.",
    23: "The available Gatineau winter sites have a single normalized category.",
}
SINGLE_CATEGORY_PROVIDERS = {2, 3, 7, 8, 17}
ALTERNATE_CATEGORY = {
    9: CampsiteType.OTHER,
    12: CampsiteType.CABIN,
    18: CampsiteType.OTHER,
}
NO_LENGTH_CONTRAST = {9, 10, 18}


def _assert_equipment_coverage(
    provider_id: int, cases: tuple[AvailabilityCase, ...]
) -> None:
    """Require contrasting requests and a known exclusion where inventory supports them."""
    provider_name = PROVIDERS[provider_id].__name__
    if provider_id in EQUIPMENT_FALLBACKS:
        assert (
            len({(case.campground_id, case.arrival, case.checkout) for case in cases})
            >= 2
        ), (
            f"{provider_name} equipment fallback requires distinct campground or date inputs"
        )
        return
    requests = {
        (case.campsite_type, case.min_rv_length)
        for case in cases
        if case.campsite_type is not None or case.min_rv_length is not None
    }
    assert len(requests) >= 2, f"{provider_name} needs contrasting equipment requests"
    rv_lengths = {
        length
        for kind, length in requests
        if kind == CampsiteType.RV and length is not None
    }
    if provider_id in SINGLE_CATEGORY_PROVIDERS:
        assert len(rv_lengths) >= 2, (
            f"{provider_name} needs distinct RV length requests"
        )
    else:
        categories = {kind for kind, _ in requests}
        alternate = ALTERNATE_CATEGORY.get(provider_id, CampsiteType.TENT)
        assert {CampsiteType.RV, alternate} <= categories, (
            f"{provider_name} needs RV and {alternate.value} equipment requests"
        )
        if provider_id not in NO_LENGTH_CONTRAST:
            assert rv_lengths, f"{provider_name} needs an RV request with a length"
    assert any(
        case.excluded_site_ids
        and (case.campsite_type is not None or case.min_rv_length is not None)
        for case in cases
    ), f"{provider_name} needs an available site excluded by an equipment request"


@pytest.mark.parametrize(
    "provider_id",
    [
        pytest.param(
            provider_id,
            id=provider.__name__,
            marks=pytest.mark.xfail(
                reason=SEASONAL_GAPS[provider_id], raises=AssertionError, strict=True
            ),
        )
        if provider_id in SEASONAL_GAPS
        else pytest.param(provider_id, id=provider.__name__)
        for provider_id, provider in PROVIDERS.items()
    ],
)
def test_provider_has_distinct_searches(provider_id: int) -> None:
    """Detect missing coverage for registered providers by name."""
    cases = tuple(case for case in CASES if case.provider_id == provider_id)
    searches = {
        (
            case.campground_id,
            case.arrival,
            case.checkout,
            case.campsite_type,
            case.min_rv_length,
        )
        for case in cases
    }
    assert len(searches) >= 2, (
        f"{PROVIDERS[provider_id].__name__} needs two known-open searches"
    )
    _assert_equipment_coverage(provider_id, cases)


@pytest.mark.parametrize("remove_contrast", [True, False])
def test_equipment_coverage_rejects_missing_evidence(remove_contrast: bool) -> None:
    """Detect a lost equipment contrast even when both date searches remain."""
    cases = tuple(
        replace(case, campsite_type=CampsiteType.TENT, min_rv_length=None)
        if remove_contrast
        else replace(case, excluded_site_ids=())
        for case in CASES
        if case.provider_id == 1
    )
    message = (
        "contrasting equipment requests"
        if remove_contrast
        else "excluded by an equipment request"
    )
    with pytest.raises(
        AssertionError, match=f"RecreationGovProvider needs .*{message}"
    ):
        _assert_equipment_coverage(1, cases)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"key": "synthetic/first"}, "duplicate cassette key"),
        ({"campsite_id": " "}, "expected campsite ID"),
        ({"nights": ()}, "expected night"),
        ({"checkout": date(2030, 1, 2)}, "checkout must follow arrival"),
        ({"checkout": date(2030, 1, 1)}, "checkout must follow arrival"),
        ({"nights": (date(2030, 1, 1),)}, "expected nights outside the stay"),
        ({"nights": (date(2030, 1, 3),)}, "expected nights outside the stay"),
    ],
)
def test_inventory_rejects_invalid_scenarios(
    changes: dict[str, object], message: str
) -> None:
    """Report the fixture key even when two distinct search inputs are present."""
    first = AvailabilityCase(
        key="synthetic/first",
        provider_id=1,
        campground_id="first",
        campground_name="Synthetic Campground",
        booking_url="https://example.test/first",
        arrival=date(2030, 1, 2),
        checkout=date(2030, 1, 3),
        campsite_id="001",
        campsite_name="Synthetic Site",
        nights=(date(2030, 1, 2),),
    )
    second = replace(first, key="synthetic/second", campground_id="second")
    second = replace(second, **changes)
    with pytest.raises(ValueError, match=f"{second.key}: {message}"):
        validate_availability_cases((first, second))


@pytest.mark.anyio
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.key)
async def test_known_open_search(
    case: AvailabilityCase, pytestconfig: pytest.Config
) -> None:
    """Verify the recorded search and eligible equipment results."""
    record_key = pytestconfig.getoption("record_provider_availability")
    candidate = pytestconfig.getoption("provider_availability_candidate")
    path = candidate if candidate is not None else CASSETTE_ROOT / f"{case.key}.yaml"

    if not record_key:
        assert path.is_file(), f"Missing cassette for {case.key}: {path}"

    provider = PROVIDERS[case.provider_id]()
    find_availabilities = provider.find_availabilities

    async def check_provider_result(
        park_id: str, start_date: date, end_date: date
    ) -> list[CampsiteDTO]:
        """Observe the unfiltered adapter response before matching equipment."""
        sites = await find_availabilities(park_id, start_date, end_date)
        assert sites, f"{case.key} returned no available sites"
        assert all(
            case.arrival <= night < case.checkout
            for site in sites
            for night in site.available_dates
        ), "Provider returned nights outside the requested stay"
        by_id = {site.campsite_id: site for site in sites}
        assert case.campsite_id in by_id, f"Expected available site {case.campsite_id}"
        expected = by_id[case.campsite_id]
        assert expected.campsite_name == case.campsite_name
        assert tuple(sorted(expected.available_dates)) == case.nights
        for site_id in case.excluded_site_ids:
            assert site_id in by_id, f"Expected availability before filtering {site_id}"
            assert set(case.nights) <= set(by_id[site_id].available_dates), site_id
        return sites

    target = CampgroundSearchResult(
        provider_id=case.provider_id,
        provider_name=provider.provider.name,
        campground_id=case.campground_id,
        campground_name=case.campground_name,
        booking_url=case.booking_url,
    )
    search = SearchRequest(
        windows=(DateWindow(start_date=case.arrival, end_date=case.checkout),),
        eligible_dates=frozenset(
            case.arrival + timedelta(days=offset)
            for offset in range((case.checkout - case.arrival).days)
        ),
        nights=(case.checkout - case.arrival).days,
        campsite_types=(case.campsite_type,) if case.campsite_type else (),
        min_rv_length=case.min_rv_length,
    )
    try:
        with (
            vcr.use_cassette(
                str(path),
                record_mode="all" if record_key else "none",
                match_on=MATCHERS,
                record_on_exception=False,
                decode_compressed_response=True,
                before_save_interaction=partial(sanitize_interaction, case=case),
            ),
            patch.object(
                provider, "find_availabilities", side_effect=check_provider_result
            ),
        ):
            stays = await check_availability(
                provider, [target], search, today=case.arrival
            )
            assert any(
                stay.campsite_id == case.campsite_id
                and stay.arrival == case.arrival
                and stay.checkout == case.checkout
                for stay in stays
            ), f"Expected site {case.campsite_id} to match the search"
            incompatible = {stay.campsite_id for stay in stays}.intersection(
                case.excluded_site_ids
            )
            assert not incompatible, (
                f"Search matched incompatible sites: {incompatible}"
            )
    finally:
        await provider.async_client.aclose()
