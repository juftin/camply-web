"""Options for replaying and recording individual provider availability cases."""

from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the single-case recording and candidate replay options."""
    group = parser.getgroup("provider availability")
    group.addoption("--record-provider-availability", metavar="CASE")
    group.addoption("--provider-availability-candidate", type=Path, metavar="PATH")


def pytest_collection_finish(session: pytest.Session) -> None:
    """Validate the selection before a request or file write can occur."""
    record_key = session.config.getoption("record_provider_availability")
    candidate = session.config.getoption("provider_availability_candidate")
    if not record_key and candidate is None:
        return

    if len(session.items) != 1:
        raise pytest.UsageError("Select exactly one provider availability test case")
    item = session.items[0]
    callspec = getattr(item, "callspec", None)
    case = callspec.params.get("case") if callspec is not None else None
    if item.path.name != "test_availability_cassettes.py" or case is None:
        raise pytest.UsageError("Select a known-open provider availability test case")
    if record_key and record_key != case.key:
        raise pytest.UsageError(f"Selected {case.key}, but requested {record_key}")
    if candidate is None:
        raise pytest.UsageError("Supply --provider-availability-candidate under tmp/")
    path = candidate.resolve()
    if not path.is_relative_to(session.config.rootpath / "tmp"):
        raise pytest.UsageError("Store the candidate cassette under tmp/")
    if record_key and path.exists():
        raise pytest.UsageError(f"Candidate already exists: {path}")
