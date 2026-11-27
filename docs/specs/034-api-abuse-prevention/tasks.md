# Tasks · API Abuse Prevention

[Specification](spec.md) · [Plan](plan.md) · [HTTP contract](contracts/http.md)

## Phase 1 · Setup

- [x] T001 Audit hosted and local routing, API operation groups, and existing monitoring in `src/frontend/functions/api/[[path]].ts`, `src/camply/server/app.py` and `deploy/helm/templates/routing.yaml`. Record decisions in `docs/specs/034-api-abuse-prevention/research.md`.

## Phase 2 · Foundation

- [x] T002 Add validated proxy and rate store settings in `src/camply/server/config.py`. Use a runtime-only secret of at least 32 characters. Require session or Auth0 with gateway enforcement, and reject strict distributed mode without shared accounting. FR-003, FR-006.
- [x] T003 Implement rate policy, store and identity handling under `src/camply/server/`, including a stable server-defined scope, positive budget and window, and expiry that does not move when a request increments the counter. Implement optional async Valkey access and bounded in-memory state. Maintain the import and optional dependency contracts in `pyproject.toml`. FR-004, FR-006.

## Phase 3 · User Story 1 · Enforce gateway provenance

Independent check: given protected settings, the same browser operation succeeds through Pages and cannot reach the backend handler without the gateway credential.

- [x] T004 [P] [US1] Extend `src/frontend/test/pages-proxy.test.ts` with synthetic credentials, header replacement, browser origin rules, cookie/CSRF/bearer forwarding, no-store behavior, missing configuration, and redirect handling. FR-002.
- [x] T005 [US1] Enforce the server-only gateway credential and trusted client identity in `src/frontend/functions/api/[[path]].ts`. Maintain local Pages validation in `src/frontend/tooling/verify-pages.ts`. FR-002, FR-003.
- [x] T006 [P] [US1] Add API tests under `tests/` covering direct/through-gateway requests, credential/identity validation, docs, unknown API paths, exact probe routes and unchanged authorization on protected endpoints. FR-001, FR-003.
- [x] T007 [US1] Enforce provenance at the HTTP boundary wired from `src/camply/server/app.py`, preserving exact safe probes and direct deployments. FR-001, FR-003.

## Phase 4 · User Story 2 · Enforce separate quotas

Independent check: class, identity, expiry and replica behavior match the HTTP contract.

- [x] T008 [US2] Cover public discovery, general traffic, login, access requests, pre-authentication, authenticated mutation, test alert and provider sync scopes, plus quota isolation and store failures, in `tests/`. FR-004, FR-005, FR-006.
- [x] T009 [US2] Classify and limit relevant API paths before expensive reads and auth. Apply account limits after verification in `src/camply/server/auth.py` and before side effects. Enforce response and store outage behavior via the protection middleware wired in `src/camply/server/app.py`. FR-004, FR-005, FR-006.

## Phase 5 · User Story 3 · Bound body sizes

Independent check: declared and observed oversized bodies return 413 before parsing, while ordinary JSON requests still work.

- [x] T010 [US3] Add explicit length, chunked body, boundary and normal-payload tests in `tests/`. FR-007.
- [x] T011 [US3] Enforce the 128 KiB request body ceiling in the middleware wired in `src/camply/server/app.py`. FR-007.

## Phase 6 · Rollout and verification

- [x] T012 [P] Pass supported server settings through `docker-compose.yaml` and document Helm secret injection in `deploy/helm/README.md`. Document private metrics/probe exposure and update `docs/operations/CONFIGURATION.md`, `docs/architecture/DESIGN_API.md` and `docs/development/AGENT_TROUBLESHOOTING.md`. FR-008.
- [ ] T013 Run targeted tests and repository lint, type, and test gates. Record outcomes and deployment checks in `docs/specs/034-api-abuse-prevention/quickstart.md` and update `docs/CHECKLIST.md`. FR-008.
- [x] T014 [P] Bound HTTP metrics route and method labels in `src/camply/server/_prometheus.py` and add regression coverage in `tests/server/test_distributed_runtime.py` for unknown routes, variable paths, and normal probe labels. FR-009.
- [x] T015 [P] Cap Explore offsets at 50,000 in `src/camply/server/routers/search.py`, keeping the reported total and constraining the browsable page count. Verify exact boundary behavior and rejection before search in `tests/server/routers/test_search.py`. FR-010.

## Dependencies and execution

- Establish the shared contract and settings first. Pages tests and backend boundary tests can proceed independently.
- With the provenance boundary in place, validate quota enforcement before extending the same boundary with body protection. Unit coverage for individual controls can be developed independently.
- The first deployable increment protects the hosted origin. Roll out the combined protections after shared-store, proxy and auth tests pass. Stage the Pages binding ahead of backend enforcement.
