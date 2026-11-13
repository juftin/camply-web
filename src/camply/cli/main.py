"""Camply entrypoint and lazy routing to independently owned command modules."""

import click

from camply.__about__ import __application__, __version__
from camply.cli import options


class CamplyCLI(click.Group):
    """Resolve commands lazily so unrelated groups keep their import boundaries."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        return sorted(
            set(super().list_commands(ctx))
            | {
                "serve",
                "db",
                "providers",
                "recreation-areas",
                "campgrounds",
                "campsites",
            }
        )

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        command = super().get_command(ctx, cmd_name)
        if command is not None:
            return command
        if cmd_name == "serve":
            from camply.cli.serve import serve_group

            command = serve_group
        elif cmd_name == "db":
            from camply.cli.db import db_group

            command = db_group
        elif cmd_name == "providers":
            from camply.cli.providers import providers_cmd

            command = providers_cmd
        elif cmd_name == "recreation-areas":
            from camply.cli.recreation_areas import recreation_areas_cmd

            command = recreation_areas_cmd
        elif cmd_name == "campgrounds":
            from camply.cli.campgrounds import campgrounds_cmd

            command = campgrounds_cmd
        elif cmd_name == "campsites":
            from camply.cli.campsites import campsites_cmd

            command = campsites_cmd
        return command


@click.group(
    cls=CamplyCLI,
    name=__application__,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(
    version=__version__,
    prog_name=__application__,
    message="%(prog)s, version %(version)s",
)
@options.provider(root=True)
@options.debug(root=True)
@click.pass_context
def cli(ctx: click.Context, provider: str | None, debug: bool | None) -> None:
    """
    camply, the campsite finder ⛺️.

    Find campsites at sold-out campgrounds.
    """
    ctx.ensure_object(dict)
    ctx.obj.update(provider=provider, debug=debug)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
