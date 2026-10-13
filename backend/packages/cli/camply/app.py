"""
Main CLI entry point for camply.
"""

import logging
import sys

import click
import structlog

from camply.__about__ import __application__, __version__
from camply.commands.campgrounds import campgrounds_command
from camply.commands.campsites import campsites_command
from camply.commands.configure import configure_command
from camply.commands.recreation_areas import recreation_areas_command


@click.group(name="camply")
@click.version_option(version=__version__, prog_name=__application__)
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Enable verbose debug logging.",
)
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """
    ⛺️ camply: The Campsite Finder.

    Search for campsite availabilities and monitor for openings on Recreation.gov.
    """
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug

    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=log_level,
    )
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )


cli.add_command(campsites_command)
cli.add_command(campgrounds_command)
cli.add_command(recreation_areas_command)
cli.add_command(configure_command)


if __name__ == "__main__":
    cli()
