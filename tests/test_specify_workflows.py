"""Exercise relocated Spec-Kit feature workflows without changing checkout state."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def specify_project(tmp_path: Path) -> Path:
    """Copy only shared Spec-Kit infrastructure into a disposable project."""
    source = Path(__file__).resolve().parents[1] / ".specify"
    destination = tmp_path / ".specify"
    for directory in ("scripts", "templates"):
        shutil.copytree(source / directory, destination / directory)
    (destination / "init-options.json").write_text(
        json.dumps({"feature_numbering": "sequential"})
    )
    for name in ("007-first", "007-second", "013-existing"):
        feature = tmp_path / "docs" / "specs" / name
        feature.mkdir(parents=True)
        (feature / "spec.md").write_text("# Synthetic feature\n")
    return tmp_path


def run_specify(
    project: Path,
    script: str,
    *arguments: str,
    settings: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a real shared script with isolated state and parse its JSON result."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT"}
    }
    environment.update(settings or {})
    result = subprocess.run(
        ["bash", str(project / ".specify/scripts/bash" / script), "--json", *arguments],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_create_feature_uses_documentation_root(specify_project: Path) -> None:
    """Creation scans relocated features, retaining duplicate historical prefixes."""
    result = run_specify(
        specify_project,
        "create-new-feature.sh",
        "--short-name",
        "synthetic-feature",
        "Create a synthetic feature",
    )
    expected = specify_project / "docs/specs/014-synthetic-feature/spec.md"
    assert result["SPEC_FILE"] == str(expected)
    assert expected.is_file()
    assert not (specify_project / "specs").exists()
    state = json.loads((specify_project / ".specify/feature.json").read_text())
    assert state["feature_directory"] == "docs/specs/014-synthetic-feature"
    assert (specify_project / "docs/specs/007-first").is_dir()
    assert (specify_project / "docs/specs/007-second").is_dir()


def test_conflicting_feature_number_advances(specify_project: Path) -> None:
    """A conflicting numeric preference advances past every relocated feature."""
    result = run_specify(
        specify_project,
        "create-new-feature.sh",
        "--number",
        "7",
        "--short-name",
        "synthetic-feature",
        "Synthetic feature",
    )
    assert result["FEATURE_NUM"] == "014"
    assert not (specify_project / "specs").exists()


def test_saved_feature_supports_plan_and_tasks(specify_project: Path) -> None:
    """Plan/task setup and implementation prerequisites share a saved feature."""
    directory = "docs/specs/013-existing"
    state = specify_project / ".specify/feature.json"
    state.write_text(json.dumps({"feature_directory": directory}))
    plan = run_specify(specify_project, "setup-plan.sh")
    assert plan["FEATURE_DIR"] == str(specify_project / directory)
    assert Path(plan["IMPL_PLAN"]).is_file()
    tasks = run_specify(specify_project, "setup-tasks.sh")
    assert tasks["FEATURE_DIR"] == plan["FEATURE_DIR"]
    assert "docs/specs" in tasks["TASKS_TEMPLATE_CONTENT"]
    (specify_project / directory / "tasks.md").write_text("# Synthetic tasks\n")
    prerequisites = run_specify(
        specify_project,
        "check-prerequisites.sh",
        "--require-spec",
        "--require-tasks",
        "--include-tasks",
    )
    assert "tasks.md" in prerequisites["AVAILABLE_DOCS"]


@pytest.mark.parametrize("paths_only", [False, True])
def test_explicit_feature_does_not_overwrite_saved_state(
    specify_project: Path, *, paths_only: bool
) -> None:
    """Both read-only mechanisms preserve a different saved feature selection."""
    state = specify_project / ".specify/feature.json"
    original = json.dumps({"feature_directory": "docs/specs/007-first"})
    state.write_text(original)
    feature = specify_project / "docs/specs/013-existing"
    (feature / "plan.md").write_text("# Synthetic plan\n")
    result = run_specify(
        specify_project,
        "check-prerequisites.sh",
        *(["--paths-only"] if paths_only else ["--require-spec"]),
        settings={
            "SPECIFY_FEATURE_DIRECTORY": "docs/specs/013-existing",
            "SPECIFY_FEATURE_NO_PERSIST": "1",
        },
    )
    assert result["FEATURE_DIR"] == str(feature)
    assert state.read_text() == original


@pytest.mark.parametrize("paths_only", [False, True])
@pytest.mark.parametrize("absolute", [False, True])
def test_old_saved_pointer_resolves_relocated_feature(
    specify_project: Path, *, paths_only: bool, absolute: bool
) -> None:
    """Old checkout-local pointers migrate only when writes are permitted."""
    state = specify_project / ".specify/feature.json"
    original = (
        str(specify_project / "specs/013-existing")
        if absolute
        else "specs/013-existing"
    )
    state.write_text(json.dumps({"feature_directory": original}))
    feature = specify_project / "docs/specs/013-existing"
    (feature / "plan.md").write_text("# Synthetic plan\n")
    result = run_specify(
        specify_project,
        "check-prerequisites.sh",
        *(["--paths-only"] if paths_only else ["--require-spec"]),
    )
    assert result["FEATURE_DIR"] == str(feature)
    expected = original if paths_only else "docs/specs/013-existing"
    assert json.loads(state.read_text())["feature_directory"] == expected


def test_local_documentation_links_resolve() -> None:
    """Current guides and historical specifications keep usable local references."""
    root = Path(__file__).resolve().parents[1]
    documents = [
        root / "README.md",
        root / "AGENTS.md",
        *root.joinpath("docs").rglob("*.md"),
    ]
    for document in documents:
        content = re.sub(r"```.*?```", "", document.read_text(), flags=re.DOTALL)
        for target in re.findall(r"\[[^\]]+\]\(([^\s)]+)\)", content):
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            filename = target.split("#", maxsplit=1)[0]
            assert (document.parent / filename).exists(), f"{document}: {target}"
