"""Run named, independently scheduled searches in the foreground CLI."""

import asyncio
import json
from pathlib import Path
from typing import Literal, TypedDict

import click

from camply.cli.discovery import resolve_targets
from camply.cli.execution import run
from camply.cli.notifications import StayDeduplicationState, send_stay_notifications
from camply.cli.output import diagnostic, logger, render_stays, serialize_stays
from camply.cli.yaml_config import ConfigError, PreparedSearch, prepare_searches
from camply.core.search import AvailabilityStay, check_availability
from camply.providers.base import BaseProvider
from camply.providers.dto import CampgroundSearchResult


class SearchOutcome(TypedDict):
    """One single-pass result in configuration order."""

    name: str
    provider: str
    status: Literal["ok", "error"]
    stays: list[dict[str, str | int | None]]


async def _watch(
    search: PreparedSearch,
    clients: dict[int, BaseProvider],
    *,
    once: bool,
    json_output: bool,
) -> SearchOutcome:
    state = StayDeduplicationState.load(search.state_file, label=search.label)
    targets: list[CampgroundSearchResult] | None = None
    if search.areas and search.campgrounds:
        logger.warning(
            "%s: explicit campgrounds take precedence over recreation areas.",
            search.label,
        )
    if search.request.warnings:
        logger.warning(
            "%s: past arrival dates were adjusted to today (UTC).", search.label
        )
    while True:
        stays: list[AvailabilityStay] = []
        status: Literal["ok", "error"] = "ok"
        try:
            provider = clients.get(search.provider_id)
            if provider is None:
                provider = search.provider_class()
                clients[search.provider_id] = provider
            if targets is None:
                targets = await resolve_targets(
                    provider, search.areas, search.campgrounds
                )
            stays = await check_availability(provider, targets, search.request)
        except Exception as exc:
            status = "error"
            logger.error(
                "%s: Provider check failed (%s). Check target IDs and provider connectivity.",
                search.label,
                type(exc).__name__,
            )
        else:
            if not json_output:
                logger.info("%s", search.label)
                render_stays(stays)
            new_stays = state.record_cycle(stays)
            await send_stay_notifications(
                search.notifications, new_stays, label=search.label
            )
        if once:
            return {
                "name": search.name,
                "provider": search.provider_name,
                "status": status,
                "stays": serialize_stays(stays) if json_output else [],
            }
        await asyncio.sleep(min(search.interval_seconds, 2**53))


async def execute_batch(
    searches: list[PreparedSearch], *, once: bool, json_output: bool
) -> list[SearchOutcome]:
    """Share provider clients and release them after all searches are drained."""
    clients: dict[int, BaseProvider] = {}
    tasks = [
        asyncio.create_task(_watch(search, clients, once=once, json_output=json_output))
        for search in searches
    ]
    try:
        return await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for provider in clients.values():
            try:
                await provider.async_client.aclose()
            except Exception as exc:
                logger.warning(
                    "Could not close %s client (%s).",
                    type(provider).__name__,
                    type(exc).__name__,
                )


def run_batch(
    ctx: click.Context, path: Path, *, debug: bool, once: bool, json_output: bool
) -> None:
    """Preflight file mode and run the foreground batch."""
    explicit = click.core.ParameterSource.COMMANDLINE
    if ctx.find_root().get_parameter_source("provider") == explicit:
        raise click.UsageError("--yaml-config cannot be combined with --provider.")
    for option in ctx.command.params:
        name = option.name
        if (
            name is not None
            and name not in {"yaml_config", "debug", "search_once", "json_output"}
            and ctx.get_parameter_source(name) == explicit
        ):
            raise click.UsageError(
                f"--yaml-config cannot be combined with {option.opts[0]}."
            )
    try:
        searches = prepare_searches(path)
    except ConfigError as exc:
        raise click.UsageError(str(exc)) from None

    diagnostic("Watching configured campsite searches.", debug, stderr_only=json_output)
    results = run(lambda: execute_batch(searches, once=once, json_output=json_output))
    if json_output:
        click.echo(json.dumps(results, indent=2))
    if any(result["status"] == "error" for result in results):
        ctx.exit(1)
