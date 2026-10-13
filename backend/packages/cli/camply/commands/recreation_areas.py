"""
Recreation Area catalog search command.
"""

import asyncio

import click

from camply.catalog import search_recreation_areas
from camply.output import print_error, print_json_output, print_rec_areas_table


@click.command(name="recreation-areas")
@click.option(
    "--search",
    "-s",
    default=None,
    help="Search query string for recreation area name.",
)
@click.option(
    "--state",
    default=None,
    help="Two-letter state code filter (e.g. CO, CA, UT).",
)
@click.option(
    "--output-json",
    is_flag=True,
    default=False,
    help="Output results in JSON format.",
)
def recreation_areas_command(
    search: str | None,
    state: str | None,
    output_json: bool,
) -> None:
    """
    Search for Recreation Areas on Recreation.gov.
    """
    if not search and not state:
        print_error(
            "Please specify at least one search parameter: --search or --state."
        )
        raise click.Abort()

    rec_areas = asyncio.run(search_recreation_areas(query=search, state=state))

    if output_json:
        print_json_output(rec_areas)
    else:
        print_rec_areas_table(rec_areas)
