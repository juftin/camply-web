# Implementation Plan for Provider Availability Cassettes

**Branch** — `provider-cassette-spec`
**Date** — 2026-11-25
**Spec** — [Provider Availability Cassettes](spec.md)

## Summary

Add a parameterized availability integration suite with at least two known-open searches per registered provider. Verify adapter output against independently observed campsites and nights, and use camply's existing search path to check equipment-sensitive matches. Run the suite as part of normal backend tests. Document the provider-specific workflow for replacing one recording at a time.

## Technical Context

- **Language and tools** — Python 3.11 through 3.14 in the existing backend test matrix, pytest, AnyIO, and the current pytest-vcr integration.
- **Storage** — Checked-in YAML cassettes under `tests/providers/cassettes/availability/`. Use ignored `tmp/` for candidate recordings.
- **Platform** — Local contributor runs and existing backend CI through `task backend:test`.
- **Constraints** — Default replay makes no live requests. Use fixed dates and a test-provided search clock. Preserve meaningful request matching and close each provider client even on assertion failure. Use short date windows and limit each cassette to the necessary HTTP interactions.
- **Scale** — 26 current providers, at least 52 scenarios. Coverage grows with the provider registry.

## Constitution Check

| Principle                       | Application                                                                                                                             |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Reliability and precision       | Compare provider output with known site identities and exact nights. Validate the exclusive checkout boundary and equipment exclusions. |
| Type safety and static analysis | Use existing result types and backend lint and type-check tasks.                                                                        |
| Modern workflow and automation  | Expose replay and targeted record mode through the existing backend test task.                                                          |
| Monorepo separation             | Keep new code in provider tests and reuse production provider and core search entry points.                                             |
| Automated verification          | Capture all registered providers, enforce coverage, and verify strict replay without network access.                                    |

The design satisfies the same gates after researching the replay and matching paths. The feature has no new public runtime interface.

## Project Structure

- `tests/providers/test_availability_cassettes.py` owns replay, registry parity, and scenario-level assertions.
- `tests/providers/availability_cases.py` holds the typed scenario inventory. Keep stable case IDs independent of dates.
- `tests/providers/conftest.py` scopes replay and explicit single-case recording to the new suite.
- `tests/providers/cassettes/availability/` stores sanitized recordings, grouped by provider.
- `docs/development/PROVIDER_CASSETTES.md` contains the refresh guide. Link it from `docs/development/DEVELOPER_GUIDE.md` in place of its suite-wide recording command.
- [Research](research.md), [test data](data-model.md), and [verification procedures](quickstart.md) document the design.

## Implementation Sequence

1. Prove the replay and recording controls with a Recreation.gov case. Verify that an empty result, changed request, or missing cassette fails and that a failed capture preserves the committed recording.
2. Add the scenario inventory and registry coverage checks. Reuse the shared equipment search and existing provider clients. For each family, confirm an open stay for each planned equipment request and capture all required interactions before adding the remaining variations.
3. Complete each scenario's refresh entry alongside its cassette. Validate a targeted refresh and run the backend suite, type checks, and lint.
