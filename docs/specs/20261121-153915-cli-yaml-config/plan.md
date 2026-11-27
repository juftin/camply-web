# Implementation Plan for CLI YAML Configuration

**Branch** — `prolific-yak`

**Date** — 2026-11-18

**Spec** — [CLI YAML Configuration](spec.md)

## Summary

Add file mode to `camply campsites --yaml-config PATH`. Validate the complete configuration with Pydantic and resolve shared defaults before startup. Run named searches concurrently with per-provider pacing, per-search alert history, and a batch outcome for single-pass automation. Reuse the current flag-mode matching, provider clients, and notifications. [Research decisions](research.md).

## Technical Context

| Area         | Design                                                                                                                                                                               |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Language     | Python 3.11+ with 3.14 as the default development and CI runtime                                                                                                                     |
| Dependencies | Existing Click, Pydantic v2, Rich, and async provider clients. Declare PyYAML in the base runtime and JSON Schema validation tooling in development dependencies.                    |
| Storage      | User-provided local YAML and optional per-search JSON observation files                                                                                                              |
| Testing      | pytest with unit cases, Click command tests, controlled async tests, and synthetic HTTP in installed-wheel tests                                                                     |
| Platform     | Existing base package on supported CLI platforms, with current signal-handling fallbacks                                                                                             |
| Scope        | A foreground batch in one process with continuous watches and a one-cycle mode                                                                                                       |
| Performance  | Start immediately after local validation. A stalled provider cannot block another provider's results or next eligible cycle. Maintain existing pacing, retries, and interval bounds. |
| Boundaries   | No database access, server runtime, distributed worker, or network validation during file preparation                                                                                |

## Constitution Check

All five gates pass before research and after design review.

| Principle                    | Design evidence                                                                                                                                                                                                   |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I. Reliability and precision | Live provider checks, reused filters and booking links, independent error recovery, and alerts sent promptly after a successful check. Exercise the 60-second notification objective under controlled conditions. |
| II. Type safety              | Strict Pydantic input boundary, typed prepared searches and outcomes, controlled error messages, and existing Ruff and mypy checks.                                                                               |
| III. Workflow and automation | Root Taskfile and uv manage verification and locked dependencies.                                                                                                                                                 |
| IV. Separation of concerns   | File parsing and batch orchestration belong to the CLI layer. The base wheel uses existing provider and shared search code without service imports or database access.                                            |
| V. Automated verification    | Unit tests for decoding, defaults, and schema parity. Synthetic provider and notification tests cover the installed public command. Existing flag-mode tests protect compatibility.                               |

## Project Structure

### Documentation

```text
docs/
├── cli-yaml-config.schema.json
└── specs/20261121-153915-cli-yaml-config/
    ├── spec.md
    ├── plan.md
    ├── research.md
    ├── data-model.md
    ├── quickstart.md
    └── contracts/cli.md
```

### Source Code

```text
pyproject.toml
uv.lock
src/camply/cli/
├── campsites.py
├── yaml_config.py
├── campsite_batch.py
├── providers.py
├── notifications.py
└── output.py
src/camply/core/search.py
tests/cli/
tests/packaging/test_cli_search.py
docs/cli.md
```

Keep input preparation in `yaml_config.py` and file-mode execution in `campsite_batch.py`. Keep the Click command in `campsites.py`. Reuse the shared core search operations and extract small CLI pieces where both modes need them.

## Implementation Sequence

1. **Input and preflight (FR-001–005, FR-011–013)** — Make date and target requirements conditional on invocation mode. Use Click parameter sources to reject explicit search flags at the root and command levels in file mode. Recognize a legacy flat file and report how to migrate it. Validate inputs, defaults, conflicts, supported filters, effective channel settings, and state paths without creating provider clients. Verify rejection of invalid final entries before any request or state write.
2. **Concurrent watches (FR-004, FR-006–007)** — Use the existing foreground runner to own the batch. Attribute provider initialization, target resolution, and availability failures to affected searches. Collect or render stays and wait independently per search. Run cleanup after cancellation and drain child tasks before closing shared clients. Verify pacing for aliases, concurrent progress across providers, and recovery on the next attempt.
3. **Alerts and scripting (FR-007–010)** — Reuse notifications and local history per search. Avoid updating history on provider failure. Collect outcomes in file order for JSON and return an aggregate status after every single-pass attempt has finished. Verify status and stream separation with mixed success, empty results, and failures.
4. **Docs and release checks (FR-011)** — Update the CLI guide with file mode, inheritance, editor schema setup, and legacy migration. Run the validation scenarios and existing CLI, packaging, imports, lint, and type checks. [Validation guide](quickstart.md).

## Complexity Tracking

The design passes all constitution gates without exceptions.
