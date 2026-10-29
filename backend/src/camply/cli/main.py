"""
Camply CLI entrypoint.

The ``camply`` console script resolves to :func:`cli`. Subcommands are
registered on this group as the CLI grows.
"""

import click

from camply.__about__ import __application__, __version__


@click.group(
    name=__application__,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(
    version=__version__,
    prog_name=__application__,
    message="%(prog)s, version %(version)s",
)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    camply, the campsite finder ⛺️.

    Find campsites at sold-out campgrounds.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
