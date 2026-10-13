"""
Campground catalog search command.
"""

import asyncio

import click

from camply.catalog import search_campgrounds
from camply.output import print_campgrounds_table, print_error, print_json_output


@click.command(name="campgrounds")
@click.option(
    "--search",
    "-s",
    default=None,
    help="Search query string for campground name.",
)
@click.option(
    "--state",
    default=None,
    help="Two-letter state code filter (e.g. CO, CA, OR).",
)
@click.option(
    "--rec-area",
    "-r",
    default=None,
    type=int,
    help="Parent Recreation Area ID filter.",
)
@click.option(
    "--output-json",
    is_flag=True,
    default=False,
    help="Output results in JSON format.",
)
def campgrounds_command(
    search: str | None,
    state: str | None,
    rec_area: int | None,
    output_json: bool,
) -> None:
    """
    Search for campgrounds on Recreation.gov.
    """
    if not search and not state and not rec_area:
        print_error(
            "Please specify at least one search parameter: --search, --state, or --rec-area."
        )
        raise click.Abort()

    campgrounds = asyncio.run(
        search_campgrounds(query=search, state=state, rec_area_id=rec_area)
    )

    if output_json:
        print_json_output(campgrounds)
    else:
        print_campgrounds_table(campgrounds)
