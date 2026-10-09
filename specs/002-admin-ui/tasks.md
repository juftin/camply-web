# Tasks: Admin UI

**Status**: Planned | **References**: [spec.md](spec.md), [plan.md](plan.md)

## Foundation and suspension

- [ ] T001 Add regression tests for administrator authorization, user suspension, and preserved scan state in backend API/worker suites.
- [ ] T002 Add `is_admin`, `scanning_enabled`, and audit event models/migration in `backend/packages/db`; verify upgrade against populated data.
- [ ] T003 Extend `backend/auth.py`, `/me`, and schemas; add `require_admin` and task-wrapped Auth0 admin provisioning by UUID.
- [ ] T004 Add shared eligibility predicate and serialize scan creation/resumption against suspension in `backend/routers/scans.py`.
- [ ] T005 Enforce eligibility in `worker/tasks/heartbeat.py`, `scanner.py`, and `notifications.py`; pass scan context and support old queued notification payloads.
- [ ] T006 Verify shared-target behavior, queued-task suspension, mutation concurrency, and re-enable restoration.

## User and scan administration

- [ ] T007 Add admin router/DTOs and transactional audits under `backend/packages/backend/backend`; implement user, scan, target, overview, and audit endpoints.
- [ ] T008 Test authorization for every admin endpoint, query totals, stale targets, redaction, and atomic audits.
- [ ] T009 Generate frontend contracts; extend `frontend/src/lib/api.ts`, `structs.ts`, and auth state.
- [ ] T010 Add admin route guard/navigation, query hooks, overview, user list/detail, scan list/detail, target detail, and audit view in `frontend/src`.
- [ ] T011 Reflect scanning suspension in the regular dashboard/forms and test complete administration journeys.

## Read-only operations

- [ ] T012 Test task application outcomes, retry/exhaustion behavior, telemetry retention, and failure isolation in worker tests.
- [ ] T013 Add bounded recent-task telemetry and discovery completion metadata in `backend/packages/worker/worker`; preserve retry exceptions.
- [ ] T014 Add backend-only Celery/Valkey dependencies and Compose/configuration wiring, operations reader, overall deadlines/concurrency/cache, allowlisted live-task DTOs, and typed GET endpoints.
- [ ] T015 Test partial worker responses, broker failure, result expiry, queue depth, redaction, history gaps, and absence of mutation routes.
- [ ] T016 Add frontend read-only operations overview/task detail, visible-view polling, freshness indicators, and unavailable-state tests.
- [ ] T017 Verify against a real local Celery/Valkey stack with mocked provider/notification calls, including retries and dependency outages.

## Usage and operational trend graphs

- [ ] T021 Define/test total/new user, scan creation, saved-active/eligible scan, eligible target, provider-check, and application-outcome metrics in backend/worker metric suites.
- [ ] T022 Instrument committed creations and effective eligibility gauges in `backend/metrics.py` and relevant routes; add worker check/outcome metrics and verify single/multi-process export, nonduplicated DB snapshots, startup cleanup, and scraping.
- [ ] T023 Add backend Prometheus configuration and admin trends endpoint with fixed queries, bounded ranges/buckets, timeouts, caching, and coverage metadata.
- [ ] T024 Test trends authorization, counter resets, bucket boundaries, missing history, suspension, deletion, and Prometheus outages with synthetic series.
- [ ] T025 Add admin overview/operations graphs, range controls, legends/tooltips, and accessible tables; install chart dependency and update the frontend lockfile if needed.
- [ ] T026 Verify graphs and metric collection against local Prometheus; document retention and capture-start limits and update frontend contracts/tests.

## Grafana replacement

- [ ] T027 Implement/test the 24-panel parity mapping in `plan.md`: API status/rates/latency, worker throughput/outcomes/duration, discovery/enqueue, results/notifications, locks, provider errors, and accurate health cards.
- [ ] T028 Correct provider-attempt denominators, checked-target execution metrics, unknown ratios, percentile aggregation, error styling, and worker-versus-scrape status; add bounded metric groups/selectors to the backend trends API.
- [ ] T029 Verify all mapped capabilities in the native admin UI with synthetic history and local Prometheus, including zero traffic and outages.
- [ ] T030 Remove Grafana service/port/volume declaration/environment references from `backend/docker-compose.yaml` and delete `backend/monitoring/grafana/` provisioning; retain Prometheus and avoid deleting persisted volumes.
- [ ] T031 Validate Compose without Grafana and update active roadmap/setup/checklist references to Admin UI monitoring.

## Completion

- [ ] T018 Update affected architecture/configuration/developer documentation and check off verified tasks in this file and `docs/agents/CHECKLIST.md`.
- [ ] T019 Run `task fix`, `task lint`, `task check`, `task test`, and configured pre-commit hooks before committing implementation.
- [ ] T020 Complete two-user shared-target smoke test, compatible consumer/producer rollout check, metric reset/retention verification, and responsive admin UI review.

Dependencies: T001–T006 precede user/scan delivery; T012–T015 precede operations UI verification; T021–T024 precede trend graph verification; monitoring parity T027–T029 precedes Grafana removal T030–T031; all slices precede completion. Application implementation has not started.
