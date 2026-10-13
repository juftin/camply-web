"""
Tests for CLI AvailabilityMonitor.
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from camply.config import CamplySettings
from camply.monitor import AvailabilityMonitor
from camply_core.models import CampsiteDTO, CampsiteType, SearchFilters, SearchWindow


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_monitor_single_cycle() -> None:
    """Verify monitor executes single cycle and filters results."""
    mock_sites = [
        CampsiteDTO(
            campsite_id="site_1",
            campsite_name="Site 1",
            campsite_type=CampsiteType.TENT,
            capacity=4,
            available_dates=[date(2026, 9, 1), date(2026, 9, 2)],
            is_electric=True,
            is_accessible=False,
        ),
        CampsiteDTO(
            campsite_id="site_2",
            campsite_name="Site 2",
            campsite_type=CampsiteType.RV,
            capacity=8,
            available_dates=[date(2026, 9, 1)],
            is_electric=False,
            is_accessible=False,
        ),
    ]

    window = SearchWindow(arrival=date(2026, 9, 1), departure=date(2026, 9, 3))
    # Filter for electric sites only
    filters = SearchFilters(min_consecutive_nights=1, electric_requirement=True)

    monitor = AvailabilityMonitor(
        campground_ids=[12345],
        search_window=window,
        filters=filters,
        continuous=False,
    )

    with patch.object(
        monitor.client,
        "find_availabilities",
        new_callable=AsyncMock,
        return_value=mock_sites,
    ):
        results = await monitor.execute_cycle()
        assert len(results) == 1
        assert results[0].campsite_id == "site_1"


@pytest.mark.anyio
async def test_monitor_pushover_alert_dispatch() -> None:
    """Verify pushover alerts triggered on new openings."""
    site = CampsiteDTO(
        campsite_id="site_new",
        campsite_name="Site New",
        campsite_type=CampsiteType.TENT,
        capacity=4,
        available_dates=[date(2026, 9, 1)],
        is_electric=False,
        is_accessible=False,
    )

    window = SearchWindow(arrival=date(2026, 9, 1), departure=date(2026, 9, 2))
    filters = SearchFilters()
    settings = CamplySettings(
        pushover_user_key="user_token",
        pushover_app_token="app_token",
    )

    monitor = AvailabilityMonitor(
        campground_ids=[12345],
        search_window=window,
        filters=filters,
        continuous=False,
        notifications=["pushover"],
        settings=settings,
    )

    with patch.object(
        monitor.client,
        "find_availabilities",
        new_callable=AsyncMock,
        return_value=[site],
    ):
        with patch(
            "camply_core.notifications.pushover.PushoverClient.send_alert",
            new_callable=AsyncMock,
        ) as mock_send:
            results = await monitor.execute_cycle()
            assert len(results) == 1
            mock_send.assert_called_once()
