"""List registered providers and resolve canonical CLI names and aliases."""

import os

import click

from camply.cli import options
from camply.cli.options import resolve_debug
from camply.cli.output import diagnostic
from camply.db.data import providers as identities
from camply.db.models import Provider
from camply.providers import PROVIDERS
from camply.providers.base import BaseProvider


def provider_entries() -> dict[str, tuple[type[BaseProvider], Provider]]:
    """Read registered identities without constructing clients or touching storage."""
    return {
        name: (PROVIDERS[identity.id], identity)
        for name, identity in vars(identities).items()
        if isinstance(identity, Provider) and identity.id in PROVIDERS
    }


def selected_provider(
    ctx: click.Context, command_provider: str | None
) -> tuple[str, type[BaseProvider]]:
    """Resolve only the winning explicit option, environment value or default."""
    selected = command_provider
    if selected is None:
        selected = ctx.find_root().params.get("provider")
    if selected is None:
        selected = os.environ.get("CAMPLY_PROVIDER", "RecreationDotGov")
    for name, (provider_class, _) in provider_entries().items():
        if selected.casefold() in {name.casefold(), provider_class.__name__.casefold()}:
            return name, provider_class
    raise click.BadParameter(
        f"Unsupported provider {selected!r}. Run 'camply providers' for supported names; legacy deployments such as GoingToCamp are deferred.",
        param_hint="--provider",
    )


@click.command(name="providers")
@options.debug()
@click.pass_context
def providers_cmd(ctx: click.Context, debug: bool | None) -> None:
    """List currently supported camping providers and discovery capabilities."""
    diagnostic(
        "Listing registered providers without network access.",
        resolve_debug(ctx, debug),
    )
    for name, (_, identity) in provider_entries().items():
        areas = (
            "no recreation-area catalog"
            if name == "ReserveAmerica"
            else "recreation-area discovery"
        )
        click.echo(
            f"{name} | {identity.name} | {areas}; campground discovery; campground availability"
        )
