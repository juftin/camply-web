"""Validate the YAML loader and the editor contract with shared fixtures."""

import json
from datetime import date
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from camply.cli.yaml_config import (
    ConfigError,
    SearchDefaults,
    load_config,
    prepare_searches,
)

SCHEMA = Path("docs/cli-yaml-config.schema.json")
SEARCH = {
    "name": "trip",
    "provider": "RecreationDotGov",
    "campgrounds": ["001"],
    "dates": [{"start_date": "2030-06-01", "end_date": "2030-06-05"}],
}


def test_documented_example_matches_defaults():
    path = Path("docs/public/examples/camply.yaml")
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(
        yaml.safe_load(path.read_text())
    )
    assert load_config(path).defaults.model_dump(exclude_unset=True) == (
        SearchDefaults().model_dump(exclude_none=True)
    )


@pytest.mark.parametrize(
    "fields", [{}, {"version": 2}, {"version": "1"}, {"version": True}]
)
def test_config_requires_supported_integer_version(tmp_path, fields):
    path = tmp_path / "camply.yaml"
    document = {"searches": [SEARCH], **fields}
    path.write_text(json.dumps(document))
    schema = Draft202012Validator(json.loads(SCHEMA.read_text()))
    assert not schema.is_valid(document)
    with pytest.raises(ConfigError, match=r"version.*version: 1"):
        load_config(path)


@pytest.mark.parametrize(
    ("changes", "valid"),
    [
        ({}, True),
        ({"rv_length": None, "notifications": [], "electric": False}, True),
        ({"rv_length": "28"}, False),
        ({"campgrounds": [1]}, False),
        ({"campgrounds": []}, False),
        ({"dates": []}, False),
        ({"dates": [SEARCH["dates"][0] | {"days": [], "weekends": False}]}, True),
        ({"dates": [SEARCH["dates"][0] | {"days": ["Funday"]}]}, False),
        ({"dates": [SEARCH["dates"][0] | {"weekends": "true"}]}, False),
        ({"dates": [SEARCH["dates"][0] | {"nights": 2}]}, False),
        ({"date_windows": SEARCH["dates"]}, False),
        ({"electric": "true"}, False),
        ({"interval": 4}, False),
        ({"notifications": ["secret-marker"]}, False),
        ({"notifications": ["pu\u017fhover"]}, False),
        ({"notifications": [" PUSHOVER ", "ntfy"]}, True),
        ({"days": ["Tues", " thURs ", "Sunday"]}, True),
        ({"days": ["Funday"]}, False),
        ({"days": ["\u017funday"]}, False),
        ({"secret-marker": 1}, False),
    ],
)
def test_editor_and_input_model(tmp_path, changes, valid):
    path = tmp_path / "trips.yaml"
    document = {"version": 1, "searches": [SEARCH | changes]}
    path.write_text(json.dumps(document))
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    assert Draft202012Validator(schema).is_valid(document) == valid
    if valid:
        assert load_config(path).searches[0].campgrounds == ["001"]
    else:
        with pytest.raises(ConfigError) as error:
            load_config(path)
        assert "secret-marker" not in str(error.value)
        assert "pu\u017fhover" not in str(error.value)


def test_invalid_default_weekday_is_rejected_even_with_override(tmp_path):
    path = tmp_path / "trips.yaml"
    document = {
        "defaults": {"days": ["Funday"]},
        "version": 1,
        "searches": [SEARCH | {"days": ["Mon"]}],
    }
    path.write_text(json.dumps(document))
    assert not Draft202012Validator(json.loads(SCHEMA.read_text())).is_valid(document)
    with pytest.raises(ConfigError, match=r"defaults\.days"):
        load_config(path)


def test_weekday_filters_inherit_independently_across_three_levels(tmp_path):
    path = tmp_path / "camply.yaml"
    path.write_text(
        """version: 1
defaults: {days: [Sun], weekends: true}
searches:
  - name: shared
    provider: RecreationDotGov
    campgrounds: ['001']
    dates:
      - {start_date: 2030-06-07, end_date: 2030-06-11}
  - name: mixed
    provider: RecreationDotGov
    campgrounds: ['001']
    days: [Fri]
    dates:
      - {start_date: 2030-06-07, end_date: 2030-06-11}
      - {start_date: 2030-06-14, end_date: 2030-06-18, weekends: false}
      - {start_date: 2030-06-21, end_date: 2030-06-25, days: [Sun]}
      - {start_date: 2030-06-28, end_date: 2030-07-02, days: [], weekends: false}
"""
    )
    shared, mixed = prepare_searches(path)
    assert shared.request.eligible_dates == {date(2030, 6, day) for day in (7, 8, 9)}
    assert mixed.request.eligible_dates == {
        date(2030, 6, day) for day in (7, 8, 14, 21, 22, 23, 28, 29, 30)
    } | {date(2030, 7, 1)}


def test_overlapping_date_ranges_union_their_eligible_nights(tmp_path):
    path = tmp_path / "camply.yaml"
    path.write_text(
        """version: 1
searches:
  - name: overlapping
    provider: RecreationDotGov
    campgrounds: ['001']
    nights: 2
    dates:
      - {start_date: 2030-06-07, end_date: 2030-06-10, days: [Fri]}
      - {start_date: 2030-06-07, end_date: 2030-06-09, days: [Sat]}
"""
    )
    (search,) = prepare_searches(path)
    assert search.request.eligible_dates == {date(2030, 6, 7), date(2030, 6, 8)}


@pytest.mark.parametrize(
    ("source", "diagnostic"),
    [
        ("searches: []\nsearches: []", "Duplicate"),
        ("searches: []\n---\nsearches: []", "line"),
        ("provider: RecreationDotGov", "legacy"),
        ("", "configuration"),
        ("version: 1\ndefaults: {rv_length: null}\nsearches: []", "defaults.rv_length"),
    ],
)
def test_yaml_document_errors(tmp_path, source, diagnostic):
    path = tmp_path / "trips.yaml"
    path.write_text(source)
    with pytest.raises(ConfigError, match=diagnostic):
        load_config(path)


def test_yaml_dates_and_field_presence(tmp_path):
    path = tmp_path / "trips.yaml"
    path.write_text(
        """version: 1
defaults: {rv_length: 28, electric: true, notifications: [ntfy]}
searches:
  - name: trip
    provider: RecreationDotGov
    campgrounds: ['001']
    dates:
      - {start_date: 2030-06-01, end_date: '2030-06-05'}
      - {start_date: 2030-06-08, end_date: '2030-06-12'}
    rv_length: null
    electric: false
    notifications: []
"""
    )
    search = load_config(path).searches[0]
    assert [window.start_date for window in search.dates] == [
        "2030-06-01",
        "2030-06-08",
    ]
    assert {"rv_length", "electric", "notifications"} <= search.model_fields_set
