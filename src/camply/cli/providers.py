"""List registered providers and resolve canonical CLI names and aliases."""

import os
from collections.abc import Sequence
from typing import TYPE_CHECKING

import click

from camply.cli import options
from camply.cli.options import resolve_debug
from camply.cli.output import (
    diagnostic,
    log_camply,
    render_providers,
    render_providers_json,
)
from camply.db.data import providers as identities
from camply.db.models import Provider
from camply.providers import PROVIDERS
from camply.providers.base import BaseProvider

if TYPE_CHECKING:
    from camply.core.search import SearchRequest
    from camply.providers.dto import CampsiteType


def validate_site_filters(
    provider_name: str,
    provider_class: type["BaseProvider"],
    *,
    campsite_types: Sequence["CampsiteType"] = (),
    require_electric: bool = False,
    require_accessible: bool = False,
    min_rv_length: int | None = None,
) -> None:
    """Reject site-attribute filters that are unsupported by the selected provider."""
    caps = provider_class.filter_capabilities
    unsupported: list[str] = []
    if campsite_types and not caps.preferred_types:
        unsupported.append("campsite type")
    if require_electric and not caps.require_electric:
        unsupported.append("electric hookup")
    if require_accessible and not caps.require_accessible:
        unsupported.append("ADA accessibility")
    if min_rv_length is not None and not caps.min_rv_length:
        unsupported.append("minimum RV / trailer length")
    if unsupported:
        raise click.UsageError(
            f"{provider_name} does not support {', '.join(unsupported)} filtering."
        )


def validate_provider_filters(
    provider_name: str,
    provider_class: type["BaseProvider"],
    request: "SearchRequest",
) -> None:
    """Reject site-attribute filters that are unsupported by the selected provider."""
    validate_site_filters(
        provider_name,
        provider_class,
        campsite_types=request.campsite_types,
        require_electric=request.require_electric,
        require_accessible=request.require_accessible,
        min_rv_length=request.min_rv_length,
    )


def provider_entries() -> dict[str, tuple[type[BaseProvider], Provider]]:
    """Read registered identities without constructing clients or touching storage."""
    return {
        name: (PROVIDERS[identity.id], identity)
        for name, identity in vars(identities).items()
        if isinstance(identity, Provider) and identity.id in PROVIDERS
    }


def find_provider(value: str) -> tuple[str, type[BaseProvider], int] | None:
    """Resolve an explicit CLI provider name or class alias without runtime access."""
    for name, (provider_class, identity) in provider_entries().items():
        if value.casefold() in {name.casefold(), provider_class.__name__.casefold()}:
            return name, provider_class, identity.id
    return None


def selected_provider(
    ctx: click.Context, command_provider: str | None
) -> tuple[str, type[BaseProvider]]:
    """Resolve only the winning explicit option, environment value or default."""
    selected = command_provider
    if selected is None:
        selected = ctx.find_root().params.get("provider")
    if selected is None:
        selected = os.environ.get("CAMPLY_PROVIDER", "RecreationDotGov")
    match = find_provider(selected)
    if match is not None:
        name, provider_class, _ = match
        return name, provider_class
    raise click.BadParameter(
        f"Unsupported provider {selected!r}. Run 'camply providers' for supported names; legacy deployments such as GoingToCamp are deferred.",
        param_hint="--provider",
    )


@click.command(name="providers")
@options.debug()
@options.json_output()
@click.pass_context
def providers_cmd(
    ctx: click.Context,
    debug: bool | None,
    json_output: bool = False,
) -> None:
    """List currently supported camping providers and discovery capabilities."""
    diagnostic(
        "Listing registered providers without network access.",
        resolve_debug(ctx, debug),
        stderr_only=json_output,
    )
    try:
        entries = provider_entries()
        if json_output:
            render_providers_json(entries)
        else:
            render_providers(entries)
    finally:
        log_camply("Exiting camply 👋")
