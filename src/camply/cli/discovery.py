"""Validate discovery filters and resolve complete provider-qualified targets."""

from collections.abc import Sequence

import click

from camply.providers.base import BaseProvider
from camply.providers.dto import (
    CampgroundSearchResult,
    ProviderSearchQuery,
    ProviderSearchResult,
)

_STATE_CODE_LENGTH = 2
DISPLAY_LIMIT = 50
RESULT_PROBE = DISPLAY_LIMIT + 1


def normalize_ids(values: Sequence[str], option: str) -> tuple[str, ...]:
    """Trim and deduplicate opaque IDs, rejecting blank selectors."""
    result = tuple(dict.fromkeys(value.strip() for value in values))
    if any(not value for value in result):
        raise click.BadParameter("IDs must not be blank.", param_hint=option)
    return result


def discovery_query(search: str, state: str | None) -> ProviderSearchQuery:
    """Normalize discovery filters and request one extra result to detect truncation."""
    if state is not None:
        state = state.strip().upper()
        if (
            len(state) != _STATE_CODE_LENGTH
            or not state.isascii()
            or not state.isalpha()
        ):
            raise click.BadParameter(
                "Use a two-letter state code.", param_hint="--state"
            )
    return ProviderSearchQuery(query=search.strip(), state=state, limit=RESULT_PROBE)


def identity_key(result: ProviderSearchResult) -> tuple[int, str, str]:
    """Identify and order results within their provider and entity type."""
    return (
        result.provider_id,
        result.entity_type,
        result.campground_id or result.recreation_area_id or "",
    )


async def resolve_targets(
    provider: BaseProvider,
    areas: Sequence[str],
    campgrounds: Sequence[str],
) -> list[CampgroundSearchResult]:
    """Resolve every selected ID before any availability request is allowed."""
    if campgrounds:
        results = [
            await provider.get_campground(identifier) for identifier in campgrounds
        ]
    else:
        results = []
        for area in areas:
            results.extend([result async for result in provider.iter_campgrounds(area)])
    return sorted(
        {identity_key(result): result for result in results}.values(),
        key=identity_key,
    )
