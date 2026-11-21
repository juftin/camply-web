"""Verify the file scheduler with independent synthetic provider operations."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from camply.cli.campsite_batch import execute_batch
from camply.cli.yaml_config import prepare_searches
from tests.cli.test_yaml_config import SEARCH


@pytest.mark.asyncio
async def test_batch_cancellation_drains_watchers(tmp_path, monkeypatch):
    path = tmp_path / "trips.yaml"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "searches": [
                    SEARCH,
                    SEARCH | {"name": "alias", "provider": "RecreationGovProvider"},
                    SEARCH | {"name": "slow", "provider": "ReserveCalifornia"},
                ],
            }
        )
    )
    searches = prepare_searches(path)
    clients = {}

    def init(provider):
        client = AsyncMock()
        assert type(provider) not in clients
        clients[type(provider)] = client
        provider.async_client = client

    for search in searches:
        monkeypatch.setattr(search.provider_class, "__init__", init)

    checked = asyncio.Event()
    slow = asyncio.Event()
    count = 0

    async def resolve(provider, *_):
        nonlocal count
        if type(provider) is searches[2].provider_class:
            slow.set()
            await asyncio.Future()
        count += 1
        if count == 2:
            checked.set()
        return []

    monkeypatch.setattr("camply.cli.campsite_batch.resolve_targets", resolve)
    task = asyncio.create_task(execute_batch(searches, once=False, json_output=False))
    await asyncio.wait_for(asyncio.gather(slow.wait(), checked.wait()), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(clients) == 2
    for client in clients.values():
        client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_target_resolution_retries_after_its_own_interval(tmp_path, monkeypatch):
    from types import SimpleNamespace

    path = tmp_path / "trips.yaml"
    path.write_text(json.dumps({"version": 2, "searches": [SEARCH | {"interval": 7}]}))
    searches = prepare_searches(path)
    provider_client = AsyncMock()
    waits = []

    def initialize(provider):
        provider.async_client = provider_client

    async def wait(seconds):
        waits.append(seconds)
        if len(waits) == 2:
            raise asyncio.CancelledError

    resolve = AsyncMock(side_effect=[ValueError("upstream error"), []])
    check = AsyncMock(return_value=[])
    monkeypatch.setattr(searches[0].provider_class, "__init__", initialize)
    monkeypatch.setattr("camply.cli.campsite_batch.resolve_targets", resolve)
    monkeypatch.setattr("camply.cli.campsite_batch.check_availability", check)
    monkeypatch.setattr(
        "camply.cli.campsite_batch.asyncio",
        SimpleNamespace(
            create_task=asyncio.create_task, gather=asyncio.gather, sleep=wait
        ),
    )
    with pytest.raises(asyncio.CancelledError):
        await execute_batch(searches, once=False, json_output=False)
    assert waits == [420, 420]
    assert resolve.await_count == 2
    check.assert_awaited_once()
    provider_client.aclose.assert_awaited_once()
