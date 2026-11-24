"""Independent metadata ingestion for all registered providers."""

from unittest.mock import AsyncMock, MagicMock, call

import pytest

from camply.providers import PROVIDERS
from camply.worker.tasks import ingestion


@pytest.fixture
def anyio_backend() -> str:
    """Run ingestion coroutines on asyncio."""
    return "asyncio"


def test_ingestion_fans_out_all_registered_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Daily ingestion includes all new IDs without requiring active user scans."""
    send = MagicMock()
    monkeypatch.setattr(ingestion.celery_app, "send_task", send)
    result = ingestion.populate_database.run()
    assert result["provider_ids"] == list(PROVIDERS)
    assert result["providers_fanned_out"] == len(PROVIDERS)
    assert send.call_args_list == [
        call(
            name="catalog.sync_provider",
            kwargs={"provider_id": provider_id},
        )
        for provider_id in PROVIDERS
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


def test_enrichment_discovery_fans_out_without_importing_catalogs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Heartbeat discovery resumes existing details independently of catalog imports."""
    send = MagicMock()
    monkeypatch.setattr(ingestion.celery_app, "send_task", send)
    result = ingestion.enrich_all_provider_details.run()
    assert result["providers_fanned_out"] == len(PROVIDERS)
    assert send.call_args_list == [
        call(
            name="catalog.enrich_provider",
            kwargs={"provider_id": provider_id},
        )
        for provider_id in PROVIDERS
    ]


@pytest.mark.parametrize(
    ("status", "has_more", "continues"),
    [("success", True, True), ("success", False, False), ("error", True, False)],
)
def test_enrichment_continues_only_successful_pending_batches(
    monkeypatch: pytest.MonkeyPatch, status: str, has_more: bool, continues: bool
) -> None:
    """A completed batch yields the queue then reaches records beyond its first 100."""
    outcome = {"status": status, "has_more": has_more}
    refresh = AsyncMock(return_value=outcome)
    send = MagicMock()
    monkeypatch.setattr(ingestion, "_enrich_provider_details_async", refresh)
    monkeypatch.setattr(ingestion.celery_app, "send_task", send)
    assert ingestion.enrich_provider_details.run(1) == outcome
    refresh.assert_awaited_once_with(1, PROVIDERS[1])
    if continues:
        send.assert_called_once_with(
            name="catalog.enrich_provider",
            kwargs={"provider_id": 1},
            countdown=1,
        )
    else:
        send.assert_not_called()


def test_unknown_enrichment_provider_is_not_requeued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Removed provider IDs cannot cause continuation storms after an upgrade."""
    send = MagicMock()
    monkeypatch.setattr(ingestion.celery_app, "send_task", send)
    assert ingestion.enrich_provider_details.run(999)["status"] == "error"
    send.assert_not_called()


@pytest.mark.anyio
async def test_populate_provider_with_missing_optional_enrichment_retains_catalog() -> (
    None
):
    """Unavailable optional detail endpoints during catalog sync still succeed without blocking scans."""
    provider = MagicMock()
    provider.populate_database = AsyncMock(return_value=None)
    provider.enrich_metadata = AsyncMock(
        side_effect=RuntimeError("Optional detail endpoint 404")
    )
    provider.async_client.aclose = AsyncMock()
    factory = MagicMock(return_value=provider)
    factory.__name__ = "SyntheticPartialProvider"

    result = await ingestion._populate_provider_async(12, factory)
    assert result["status"] == "success"
    provider.populate_database.assert_awaited_once()
    provider.enrich_metadata.assert_awaited_once()
    provider.async_client.aclose.assert_awaited_once()
