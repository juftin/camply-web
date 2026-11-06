"""Independent metadata ingestion for all registered providers."""

from unittest.mock import AsyncMock, MagicMock, call

import pytest

from camply.providers import CATALOG_PROVIDERS, PROVIDERS
from camply.worker.tasks import ingestion


@pytest.fixture
def anyio_backend() -> str:
    """Run ingestion coroutines on asyncio."""
    return "asyncio"


def test_ingestion_fans_out_all_enabled_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Daily ingestion includes enabled IDs only and skips unverified providers."""
    send = MagicMock()
    monkeypatch.setattr(ingestion.celery_app, "send_task", send)
    result = ingestion.populate_database.run()
    assert result["provider_ids"] == list(CATALOG_PROVIDERS) == list(range(1, 13))
    assert set(PROVIDERS) - set(CATALOG_PROVIDERS) == set(range(13, 26))
    assert result["providers_fanned_out"] == 12
    assert send.call_args_list == [
        call(
            name="camply.catalog.sync_provider_catalog",
            kwargs={"provider_id": provider_id},
        )
        for provider_id in CATALOG_PROVIDERS
    ]


@pytest.mark.anyio
@pytest.mark.parametrize("failure", [False, True])
async def test_ingestion_uses_metadata_and_closes_clients(failure: bool) -> None:
    """The worker ingests catalogs independently and releases clients after failures."""
    provider = MagicMock()
    provider.populate_database = AsyncMock(
        side_effect=RuntimeError("Synthetic ingestion failure") if failure else None,
    )
    provider.find_availabilities = AsyncMock()
    provider.async_client.aclose = AsyncMock()
    factory = MagicMock(return_value=provider)
    factory.__name__ = "SyntheticProvider"
    if failure:
        with pytest.raises(RuntimeError, match="Synthetic ingestion failure"):
            await ingestion._populate_provider_async(11, factory)
    else:
        result = await ingestion._populate_provider_async(11, factory)
        assert result == {
            "status": "success",
            "provider_id": 11,
            "provider_name": "SyntheticProvider",
            "search_name": "Sync SyntheticProvider Catalog",
        }
    provider.populate_database.assert_awaited_once()
    provider.find_availabilities.assert_not_called()
    provider.async_client.aclose.assert_awaited_once()
