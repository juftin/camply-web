"""Verify optional Sentry initialization without sending events or changing globals."""

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("module", ["camply.server.app", "camply.worker.celery_app"])
def test_configured_sentry_initializes_with_application_settings(module: str) -> None:
    """Both entry points pass configured values to the optional reporting SDK."""
    script = """
import importlib
import sys
from unittest.mock import patch

with patch('sentry_sdk.init') as initialize:
    importlib.import_module(sys.argv[1])
    initialize.assert_called_once()
    settings = initialize.call_args.kwargs
    assert settings['dsn'] == 'https://synthetic@example.test/1'
    assert settings['environment'] == 'package-test'
    assert settings['traces_sample_rate'] == 0.25
    assert settings['integrations']
"""
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("CAMPLY_")
    }
    environment.update(
        CAMPLY_SENTRY_DSN="https://synthetic@example.test/1",
        CAMPLY_ENVIRONMENT="package-test",
        CAMPLY_SENTRY_TRACES_SAMPLE_RATE="0.25",
    )
    result = subprocess.run(
        [sys.executable, "-c", script, module],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
