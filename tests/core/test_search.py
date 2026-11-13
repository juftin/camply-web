"""Availability matching and owned sequential monitoring without services."""

import asyncio
from datetime import date
from unittest.mock import AsyncMock

import pytest

from camply.core.search import (
    check_availability,
    monitor,
    normalize_request,
)
from camply.db.availability import matching_available_dates
from camply.providers.dto import CampgroundSearchResult, CampsiteDTO, CampsiteType

TODAY = date(2030, 1, 1)


@pytest.fixture(autouse=True)
def fixed_utc_day(monkeypatch):
    """Keep monitoring deterministic across local timezone and calendar changes."""
    monkeypatch.setattr("camply.core.search.utc_today", lambda: TODAY)


def target(campground_id="001"):
    return CampgroundSearchResult(
        provider_id=1,
        provider_name="Recreation.gov",
        campground_id=campground_id,
        campground_name="Forest",
        recreation_area_id="park",
        recreation_area_name="Park",
        booking_url="https://example.test/camp/001",
    )


def site(site_id="s1", nights=(1, 2, 3, 4)):
    return CampsiteDTO(
        campsite_id=site_id,
        campsite_name=f"Site {site_id}",
        campsite_type=CampsiteType.TENT,
        capacity=1,
        available_dates=[date(2030, 1, day) for day in nights],
        is_electric=False,
        is_accessible=False,
    )


def request(**kwargs):
    return normalize_request(
        start_dates=[date(2030, 1, 1)],
        end_dates=[date(2030, 1, 5)],
        today=TODAY,
        **kwargs,
    )


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"start_dates": [], "end_dates": []}, "paired"),
        ({"start_dates": [TODAY], "end_dates": []}, "paired"),
        ({"start_dates": [TODAY], "end_dates": [TODAY]}, "after"),
        ({"start_dates": [TODAY], "end_dates": [date(2029, 12, 31)]}, "after"),
        ({"start_dates": [date(2029, 1, 1)], "end_dates": [TODAY]}, "remaining"),
    ],
)
def test_invalid_windows(kwargs, message):
    with pytest.raises(ValueError, match=message):
        normalize_request(today=TODAY, **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [{"nights": 0}, {"nights": 5}, {"days": ["bad"]}, {"days": ["MON"], "nights": 2}],
)
def test_invalid_constraints(kwargs):
    with pytest.raises(ValueError):
        request(**kwargs)


def test_past_start_clamped_and_warning():
    normalized = normalize_request(
        start_dates=[date(2029, 12, 30)], end_dates=[date(2030, 1, 3)], today=TODAY
    )
    assert normalized.windows[0].start_date == TODAY
    assert len(normalized.warnings) == 1
    assert "2030-01-01" in normalized.warnings[0]


def test_weekend_weekday_union_and_aliases():
    normalized = normalize_request(
        start_dates=[date(2030, 1, 4)],
        end_dates=[date(2030, 1, 8)],
        days=["Sunday", "fri", "SUN"],
        weekends=True,
        today=TODAY,
    )
    assert normalized.eligible_dates == frozenset(date(2030, 1, d) for d in (4, 5, 6))
    for day in (
        "MON",
        "TUE",
        "TUES",
        "WED",
        "THU",
        "THUR",
        "THURS",
        "FRI",
        "SAT",
        "SUN",
        "monday",
    ):
        normalize_request(
            start_dates=[TODAY], end_dates=[date(2030, 1, 15)], days=[day], today=TODAY
        )


@pytest.mark.asyncio
async def test_sliding_exact_stays_reuse_web_matching_and_dedup():
    provider = AsyncMock()
    provider.find_availabilities.return_value = [site(), site()]
    normalized = request(nights=3)
    stays = await check_availability(
        provider, [target(), target()], normalized, today=TODAY
    )
    assert [(stay.arrival, stay.checkout) for stay in stays] == [
        (date(2030, 1, 1), date(2030, 1, 4)),
        (date(2030, 1, 2), date(2030, 1, 5)),
    ]
    assert matching_available_dates(
        [d.isoformat() for d in normalized.eligible_dates], min_stay_length=3
    ) == [date(2030, 1, d).isoformat() for d in (1, 2, 3, 4)]
    provider.find_availabilities.assert_awaited_once_with(
        "001", date(2030, 1, 1), date(2030, 1, 5)
    )
    assert stays[0].booking_url == target().booking_url


@pytest.mark.asyncio
async def test_windows_overlap_merged_but_gaps_and_sites_never_combined():
    normalized = normalize_request(
        start_dates=[TODAY, date(2030, 1, 2), date(2030, 1, 6)],
        end_dates=[date(2030, 1, 4), date(2030, 1, 5), date(2030, 1, 8)],
        nights=2,
        today=TODAY,
    )
    provider = AsyncMock()
    provider.find_availabilities.return_value = [
        site(nights=(1, 2, 4, 5, 6, 7)),
        site("s2", nights=(3,)),
    ]
    stays = await check_availability(provider, [target()], normalized, today=TODAY)
    assert [(s.campsite_id, s.arrival.day, s.checkout.day) for s in stays] == [
        ("s1", 1, 3),
        ("s1", 6, 8),
    ]
    assert provider.find_availabilities.await_count == 2


@pytest.mark.asyncio
async def test_expired_nights_excluded_at_next_cycle():
    provider = AsyncMock()
    provider.find_availabilities.return_value = [site()]
    stays = await check_availability(
        provider, [target()], request(nights=2), today=date(2030, 1, 4)
    )
    assert stays == []
    provider.find_availabilities.assert_awaited_once_with(
        "001", date(2030, 1, 4), date(2030, 1, 5)
    )


@pytest.mark.asyncio
async def test_provider_failure_does_not_look_empty():
    provider = AsyncMock()
    provider.find_availabilities.side_effect = TimeoutError("failed check")
    with pytest.raises(TimeoutError, match="failed check"):
        await check_availability(provider, [target()], request(), today=TODAY)


@pytest.mark.asyncio
async def test_monitor_continues_after_matches_then_cancels_owned_work():
    provider = AsyncMock()
    provider.find_availabilities.return_value = [site()]
    waits = 0
    output = []

    async def wait(seconds):
        nonlocal waits
        waits += 1
        assert seconds == 0.1
        if waits == 2:
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await monitor(
            provider, [target()], request(), output.append, interval=0.1, wait=wait
        )
    assert len(output) == 2
    assert all(output)
    assert provider.find_availabilities.await_count == 2
    await asyncio.sleep(0)
    assert provider.find_availabilities.await_count == 2


@pytest.mark.asyncio
async def test_cancellation_reaps_active_request_without_next_target():
    started = asyncio.Event()
    cancelled = asyncio.Event()
    provider = AsyncMock()

    async def find_availabilities(*args):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    provider.find_availabilities.side_effect = find_availabilities
    task = asyncio.create_task(
        monitor(provider, [target("001"), target("002")], request(), lambda stays: None)
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled.is_set()
    assert provider.find_availabilities.await_count == 1
    await asyncio.sleep(0)
    assert provider.find_availabilities.await_count == 1


@pytest.mark.asyncio
async def test_deterministic_targets_sites_and_site_url():
    provider = AsyncMock()
    first = site("b")
    first.metadata["booking_url"] = "https://example.test/sites/b"
    provider.find_availabilities.return_value = [first, site("a")]
    stays = await check_availability(
        provider, [target("002"), target("001")], request(), today=TODAY
    )
    assert [
        (stay.campground.campground_id, stay.campsite_id, stay.arrival)
        for stay in stays
    ] == sorted(
        (stay.campground.campground_id, stay.campsite_id, stay.arrival)
        for stay in stays
    )
    assert {stay.booking_url for stay in stays if stay.campsite_id == "b"} == {
        "https://example.test/sites/b"
    }


@pytest.mark.asyncio
async def test_empty_targets_do_not_start_polling():
    provider = AsyncMock()
    output = []
    wait = AsyncMock()
    await monitor(provider, [], request(), output.append, wait=wait)
    provider.find_availabilities.assert_not_awaited()
    wait.assert_not_awaited()
    assert output == []


@pytest.mark.asyncio
async def test_rollover_refreshes_later_targets_and_expires_earlier_results(
    monkeypatch,
):
    current_day = TODAY
    provider = AsyncMock()

    async def availability(identifier, start, end):
        nonlocal current_day
        current_day += date.resolution
        return [site()]

    provider.find_availabilities.side_effect = availability
    monkeypatch.setattr("camply.core.search.utc_today", lambda: current_day)
    stays = await check_availability(
        provider, [target("001"), target("002")], request(nights=2)
    )
    assert [
        (call.args[0], call.args[1])
        for call in provider.find_availabilities.await_args_list
    ] == [
        ("001", date(2030, 1, 1)),
        ("002", date(2030, 1, 2)),
    ]
    assert [
        (stay.campground.campground_id, stay.arrival, stay.checkout) for stay in stays
    ] == [
        ("001", date(2030, 1, 3), date(2030, 1, 5)),
        ("002", date(2030, 1, 3), date(2030, 1, 5)),
    ]


@pytest.mark.asyncio
async def test_rollover_clips_the_next_window_and_preserves_explicit_today(monkeypatch):
    current_day = TODAY
    provider = AsyncMock()
    normalized = normalize_request(
        start_dates=[TODAY, date(2030, 1, 6)],
        end_dates=[date(2030, 1, 3), date(2030, 1, 9)],
        today=TODAY,
    )

    async def availability(identifier, start, end):
        nonlocal current_day
        current_day = date(2030, 1, 7)
        return [site(nights=(1, 2, 6, 7, 8))]

    provider.find_availabilities.side_effect = availability
    monkeypatch.setattr("camply.core.search.utc_today", lambda: current_day)
    stays = await check_availability(provider, [target()], normalized)
    assert [call.args[1] for call in provider.find_availabilities.await_args_list] == [
        TODAY,
        date(2030, 1, 7),
    ]
    assert [stay.arrival.day for stay in stays] == [7, 8]
    provider.find_availabilities.reset_mock()
    stays = await check_availability(provider, [target()], normalized, today=TODAY)
    assert [call.args[1] for call in provider.find_availabilities.await_args_list] == [
        TODAY,
        date(2030, 1, 6),
    ]
    assert [stay.arrival.day for stay in stays] == [1, 2, 6, 7, 8]
