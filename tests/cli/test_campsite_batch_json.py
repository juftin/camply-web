"""Exercise batch JSON and exit status using the public CLI."""

import json

from click.testing import CliRunner

from camply.cli.main import cli
from tests.cli.test_yaml_config import SEARCH

pytest_plugins = ("tests.cli.test_search",)


def test_single_pass_mixed_results(tmp_path, transcript):
    path = tmp_path / "trips.yaml"
    path.write_text(
        json.dumps(
            {
                "searches": [
                    SEARCH | {"name": "failure", "campgrounds": ["bad"]},
                    SEARCH
                    | {
                        "dates": [
                            {"start_date": "2027-07-09", "end_date": "2027-07-13"}
                        ]
                    },
                    SEARCH | {"name": "empty", "campsites": ["missing"]},
                ]
            }
        )
    )
    args = ["campsites", "--yaml-config", str(path), "--json"]
    invalid = CliRunner().invoke(cli, args)
    assert invalid.exit_code == 2
    assert not invalid.stdout
    result = CliRunner().invoke(cli, [*args, "--search-once"])
    assert result.exit_code == 1
    outcomes = json.loads(result.stdout)
    assert [(row["name"], row["status"]) for row in outcomes] == [
        ("failure", "error"),
        ("trip", "ok"),
        ("empty", "ok"),
    ]
    assert not outcomes[0]["stays"]
    assert outcomes[1]["stays"]
    assert not outcomes[2]["stays"]
    assert "failure" in result.stderr
    assert "nonbookable" not in result.stderr
    assert len(transcript.checks) == 2
    transcript.checks.clear()
    path.write_text(json.dumps({"searches": [SEARCH]}))
    result = CliRunner().invoke(cli, [*args, "--search-once"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["status"] == "ok"
