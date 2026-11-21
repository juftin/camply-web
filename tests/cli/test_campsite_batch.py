"""Exercise the public file-mode flag and preflight contracts."""

import json

import pytest
from click.testing import CliRunner

from camply.cli.main import cli
from tests.cli.test_yaml_config import SEARCH

pytest_plugins = ("tests.cli.test_search",)

pytestmark = pytest.mark.usefixtures("transcript")


@pytest.mark.parametrize(
    ("root", "options"),
    [
        (["--provider", "RecreationDotGov"], []),
        ([], ["--provider", "RecreationDotGov"]),
        ([], ["--nights", "1"]),
        ([], ["--start-date", "2030-06-01"]),
    ],
)
def test_explicit_search_flags_conflict(tmp_path, root, options, transcript):
    path = tmp_path / "trips.yaml"
    path.write_text(json.dumps({"searches": [SEARCH]}))
    result = CliRunner().invoke(
        cli, [*root, "campsites", "--yaml-config", str(path), *options]
    )
    assert result.exit_code == 2
    assert "cannot be combined" in result.stderr
    assert not transcript.constructed


def test_invalid_final_search_has_no_side_effects(tmp_path, transcript):
    path = tmp_path / "trips.yaml"
    path.write_text(
        json.dumps(
            {
                "searches": [
                    SEARCH | {"state_file": "state.json"},
                    SEARCH | {"name": "invalid", "provider": "secret-marker"},
                ]
            }
        )
    )
    result = CliRunner().invoke(
        cli, ["campsites", "--yaml-config", str(path), "--search-once", "--json"]
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "provider" in result.stderr
    assert "secret-marker" not in result.stderr
    assert not transcript.constructed
    assert not (tmp_path / "state.json").exists()


def test_reversed_window_reports_yaml_field(tmp_path, transcript):
    path = tmp_path / "trips.yaml"
    search = SEARCH | {
        "provider": "ReserveCaliforniaProvider",
        "dates": [
            *SEARCH["dates"],
            {"start_date": "2030-08-05", "end_date": "2030-08-03"},
        ],
    }
    path.write_text(json.dumps({"searches": [search]}))
    result = CliRunner().invoke(
        cli, ["campsites", "--yaml-config", str(path), "--search-once", "--json"]
    )
    assert result.exit_code == 2
    assert not result.stdout
    assert "'trip' (ReserveCalifornia)" in result.stderr
    assert "dates.1.end_date" in result.stderr
    assert "2030-08-03" not in result.stderr
    assert "--end-date" not in result.stderr
    assert not transcript.constructed


def test_effective_filters_and_target_precedence(tmp_path, transcript, monkeypatch):
    from camply.cli.yaml_config import prepare_searches
    from camply.providers.base import ProviderFilterCapabilities

    path = tmp_path / "trips.yaml"
    search = SEARCH | {
        "recreation_areas": ["ignored"],
        "dates": [
            {"start_date": "2027-07-09", "end_date": "2027-07-13"},
            {"start_date": "2027-07-12", "end_date": "2027-07-13", "weekends": False},
        ],
        "weekends": True,
    }
    document = {"defaults": {"rv_length": 28}, "searches": [search]}
    path.write_text(json.dumps(document))
    provider = prepare_searches(path)[0].provider_class
    monkeypatch.setattr(
        provider, "filter_capabilities", ProviderFilterCapabilities(min_rv_length=False)
    )

    args = ["campsites", "--yaml-config", str(path), "--search-once", "--json"]
    unsupported = CliRunner().invoke(cli, args)
    assert unsupported.exit_code == 2
    assert "RV / trailer length" in unsupported.stderr
    assert not transcript.constructed

    search["rv_length"] = None
    path.write_text(json.dumps(document))
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.stderr
    assert "campgrounds take precedence" in result.stderr
    assert transcript.lookups == ["001"]
    assert not transcript.areas
    assert [stay["arrival"] for stay in json.loads(result.stdout)[0]["stays"]] == [
        "2027-07-09",
        "2027-07-10",
        "2027-07-12",
    ]
