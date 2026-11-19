"""Validate the YAML loader and the editor contract with shared fixtures."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from camply.cli.yaml_config import ConfigError, load_config

SCHEMA = Path("docs/specs/032-cli-yaml-config/contracts/cli-yaml-config.schema.json")
SEARCH = {
    "name": "trip",
    "provider": "RecreationDotGov",
    "campgrounds": ["001"],
    "date_windows": [{"start_date": "2030-06-01", "end_date": "2030-06-05"}],
}


@pytest.mark.parametrize(
    ("changes", "valid"),
    [
        ({}, True),
        ({"rv_length": None, "notifications": [], "electric": False}, True),
        ({"rv_length": "28"}, False),
        ({"campgrounds": [1]}, False),
        ({"campgrounds": []}, False),
        ({"electric": "true"}, False),
        ({"interval": 4}, False),
        ({"notifications": ["secret-marker"]}, False),
        ({"secret-marker": 1}, False),
    ],
)
def test_editor_and_input_model(tmp_path, changes, valid):
    path = tmp_path / "trips.yaml"
    document = {"searches": [SEARCH | changes]}
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


@pytest.mark.parametrize(
    ("source", "diagnostic"),
    [
        ("searches: []\nsearches: []", "Duplicate"),
        ("searches: []\n---\nsearches: []", "line"),
        ("provider: RecreationDotGov", "legacy"),
        ("", "configuration"),
        ("defaults: {rv_length: null}\nsearches: []", "defaults.rv_length"),
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
        """defaults: {rv_length: 28, electric: true, notifications: [ntfy]}
searches:
  - name: trip
    provider: RecreationDotGov
    campgrounds: ['001']
    date_windows: [{start_date: 2030-06-01, end_date: '2030-06-05'}]
    rv_length: null
    electric: false
    notifications: []
"""
    )
    search = load_config(path).searches[0]
    assert search.date_windows[0].start_date == "2030-06-01"
    assert {"rv_length", "electric", "notifications"} <= search.model_fields_set
