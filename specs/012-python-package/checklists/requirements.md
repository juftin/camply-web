# Specification Readiness: One Python Package

**Feature**: [spec.md](../spec.md) | **Status**: Design reviewed; implementation verified locally

## Design Review

- [x] One distribution and the four internal component boundaries are defined.
- [x] Base dependencies and four additive extras have explicit installation contracts.
- [x] CLI implementation, local scheduling, UI bundling, and publication are excluded.
- [x] Python support is explicitly `>=3.11`; development/primary CI/Docker/release defaults are 3.14.
- [x] Python 3.11 compatibility tests supplement the standard 3.14 checks.
- [x] Existing API/database/task compatibility requirements are documented.
- [x] Installed resources and direct/sdist-rebuilt wheels have acceptance checks.
- [x] Dependency partition and development/CI/Docker extra selection happen together.
- [x] Constitution and current architecture documentation updates are tracked.
- [x] All requirements and success criteria map to implementation/verification tasks.

These checks validate the design only. Runtime acceptance evidence is recorded in [quickstart.md](../quickstart.md#acceptance-evidence), outside the
pre-implementation checklist gate.

## Requirement Coverage

| Requirement                                   | Tasks                                         | Verification                                                |
| --------------------------------------------- | --------------------------------------------- | ----------------------------------------------------------- |
| FR-001: Single distribution                   | T004, T006, T009, T024                        | One project/version and wheel/sdist pair                    |
| FR-002: Internal boundaries                   | T005, T014, T022                              | Import checks without application bootstrap                 |
| FR-003: Base and extras                       | T006, T013, T023                              | Isolated base/runtime environments                          |
| FR-004: Preserve existing utility, no new CLI | T016, T029                                    | Population help/flags and entry-point metadata              |
| FR-005: Optional-feature isolation            | T012, T018–T023                               | Missing-extra and service-outage regressions                |
| FR-006: Standalone artifacts/resources        | T010, T012, T015, T024                        | Resource/migration checks for both wheel paths              |
| FR-007: Existing contracts/data               | T001, T005, T015, T018, T028                  | Baseline comparisons and existing suites                    |
| FR-008: Tooling/governance/docs               | T002, T007–T009, T025–T030                    | Task, CI, Docker, release and documentation review          |
| FR-009: Isolated installation                 | T003, T012, T018, T025, T026                  | Fresh artifact installs outside the checkout                |
| FR-010: Scope limits                          | T027, T029, T031                              | No new CLI/scheduler/UI bundle or PyPI upload               |
| FR-011: Python policy                         | T001, T002, T006, T008, T009, T023–T026, T029 | 3.14 defaults, 3.11 tooling floor, both-version tests       |
| FR-012: Import architecture enforcement       | T032–T034                                     | Accepted source and rejected deliberate boundary violations |

Before completing implementation, record actual check outcomes in
[quickstart.md](../quickstart.md), reconcile requirement coverage with
[tasks.md](../tasks.md), and leave unexecuted acceptance checks there unchecked.
