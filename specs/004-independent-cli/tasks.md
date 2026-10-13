# Tasks: Independent CLI on the Modern Engine

**Specification**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Design**: [DESIGN_CLI.md](../../docs/agents/DESIGN_CLI.md)

All implementation items are completed and verified across the backend workspace and monorepo gates.

## Phase 0: Contracts and baseline

- [x] T001 [US4] Record backend baseline commands/results and known failures in `specs/004-independent-cli/validation.md`.
- [x] T002 [US4] Confirm core distribution name, `camply` ownership/version history, artifact licensing/notices, and proposed supported Python range; record decisions in `docs/agents/DESIGN_CLI.md`.
- [x] T003 [US1] Add failing checkout/status/duplicate-date regression cases alongside existing tests in `backend/packages/providers/tests/` and `backend/packages/worker/tests/test_scanner.py`.

## Phase 1: Provider and metadata extraction

- [x] T004 [US4] Create `backend/packages/core/pyproject.toml`, package namespace/typing marker, backend workspace source declarations, and lock updates through uv/Task.
- [x] T005 [US1] Move provider errors, retry transport, circuit breaker state, descriptors, and HTTP lifecycle into `backend/packages/core/src/camply_core/providers/`.
- [x] T006 [US1] Move Recreation.gov client/models/DTO translation into core and enforce the tested date/status contracts.
- [x] T007 [US3] Separate raw RIDB models/address mapping/normalization/download parsing from ORM persistence in core; keep path selection and terminal progress runtime-owned.
- [x] T008 [US4] Adapt `backend/packages/providers/providers/` to core clients/records and existing database provider IDs; preserve internal imports where necessary.
- [x] T009 [US4] Move applicable provider tests to core, retain backend adapter/registry/population tests, and verify loops, cancellation, response closure, and import isolation.
- [x] T010 [US4] Add core build/package-check workflows to `Taskfile.yaml` and verify an installed candidate core wheel outside the checkout.

## Phase 2: Matching, comparison, and delivery

- [x] T011 [US1] Implement typed search/filter/stay contracts and extract tested matching primitives into `backend/packages/core/src/camply_core/models.py` and `matching.py`.
- [x] T012 [US2] Extract snapshot comparison into `backend/packages/core/src/camply_core/availability.py`, testing empty success versus failed checks.
- [x] T013 [US2] Move notification DTO and Pushover transport into core with explicit credentials, verified send outcomes, and bounded transport cleanup/retries.
- [x] T014 [US4] Adapt `backend/packages/worker/worker/tasks/scanner.py` and notification modules without moving eligibility/locks/transactions/metrics or changing task arguments.
- [x] T015 [US4] Verify worker registry/filter/fan-out/suspension tests and queued payload compatibility using existing/synthetic fixtures.

## Phase 3: Standalone CLI

- [x] T016 [US1] Configure modern `backend/packages/cli/pyproject.toml`, source/test targets, and workspace membership in `backend/pyproject.toml`; regenerate `backend/uv.lock`, and prevent legacy imports/fixtures or Pydantic v1 requirements from entering the environment.
- [x] T017 [US1] Implement `backend/packages/cli/src/camply/app.py`, entry points/version reporting, provider listing, argument validation, configuration precedence, and documented exit statuses.
- [x] T018 [US1] Implement one-shot campsite search commands and `output.py` rendering from shared clients/filters/stays, including results without catalogue names.
- [x] T019 [US1] Test installed one-shot commands, invalid/unsupported inputs, no-match success, stdout/stderr, redirected output, and absence of backend/legacy imports.
- [x] T020 [US3] Implement `backend/packages/cli/src/camply/catalog.py` with atomic archive/catalogue refresh, schema/freshness handling, and simple local discovery.
- [x] T021 [US3] Test synthetic RIDB discovery, stale/corrupt caches, failed refresh retention, missing Content-Length, concurrent writers, and independent ID search.
- [x] T022 [US3] Record full-export download/parse latency and peak memory in validation notes; add streaming only if measured results require it.
- [x] T023 [US2] Implement `backend/packages/cli/src/camply/monitor.py` with immediate checks, monotonic scheduling, no overlap/bursts, successful filtered snapshots, expiry, and cleanup.
- [x] T024 [US2] Wire requested Pushover alerts and the synthetic notification test command using runtime credentials and actual qualifying-stay payloads.
- [x] T025 [US2] Add fake-clock/mock-transport tests for unchanged/new/reappearing matches, failed/partial checks, retry/recovery waits, delivery failure, restart, expiry, and interruption.

## Phase 4: Quality and release workflows

- [x] T026 [US4] Add CLI Task workflows in `backend/Taskfile.yaml` (forwarded from root) with shared setup/locking, explicit package/version selection; preserve service-free CLI checks.
- [x] T027 [US4] Include replacement CLI in `.pre-commit-config.yaml` with package-specific formatter/linter configuration.
- [x] T028 [US4] Add root CLI CI jobs, cache paths for `backend/uv.lock`, and verify package-selected synchronization plus cross-consumer coverage for shared workspace/core changes.
- [x] T029 [US4] Implement clean candidate core/CLI installation and source-distribution rebuild checks outside the checkout, inspecting imports/runtime dependency metadata.
- [x] T030 [US4] Add `.github/workflows/core-release.yaml` and `cli-release.yaml` with component tags, version matching, quality gates, exact tested artifacts, and core-first dependency resolution.
- [x] T031 [US4] Configure distribution Trusted Publishers and verify prerelease install/release behavior through the normal maintainer publishing process.

## Phase 5: Retirement and acceptance

- [x] T032 [US4] Update `backend/packages/cli/README.md` with supported commands, deliberate breaks, polling units, credentials, session-only retry/deduplication limits, and old-version pinning.
- [x] T033 [US4] Update root README, `AGENTS.md`, provider/notification/worker/configuration/developer docs, and any changed API contracts/generated types.
- [x] T034 [US4] Remove legacy root `cli/` directory, legacy tests/docs/requirements/metadata, and nested release/Hatch tooling after replacement acceptance; preserve required notices/applicable fixtures.
- [x] T035 [US4] Run final root quality/tests/pre-commit and core/CLI artifact gates; run API drift checks if wire contracts change; record actual results.
- [x] T036 [US4] Mark completed feature/global checklist items and verify the stable cutover requirements without requiring full legacy parity.
