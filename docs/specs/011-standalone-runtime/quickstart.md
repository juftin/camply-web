# Quickstart validation: standalone runtime

**Status**: Implemented. Local verification evidence is recorded below.

## Prerequisites

Checkout: Python 3.12, uv, Task, Node 24, and pinned pnpm. No Docker/database/broker/monitoring service.
Prepared wheels: Python and an environment installer; no Task/Node at runtime.
Provider/notification access needs internet; automated checks use synthetic transports and no credentials.

## Build and launch (US1)

```bash
task standalone:install
task standalone:build
CAMPLY_DB_DRIVERNAME=sqlite+aiosqlite \
CAMPLY_DB_HOST=/tmp/camply-standalone-validation/camply.db \
task standalone:run
```

Use fresh test-owned storage. Expect one Python app at `http://127.0.0.1:8000`, ready API health, and root/deep links. Migrations finish before serving. Missing `/api/unknown`, `/assets/missing.js`, and `/metrics` return errors rather than entry HTML.

## Catalog / scan journey (US2)

1. Open Admin Operations with existing default automatic login; request initial sync. Expect prompt job ID, progress, per-provider outcomes, and searchable metadata. Repeated requests share active refresh.
2. In smoke fixtures, create two synthetic subscriptions sharing a target. Expect one due provider check and individually filtered delivery. Browser API calls use the real server, not intercepted responses.
3. Pause/edit/delete a scan or suspend its user before sending; expect skip when current owner/target/dates/eligibility/filters no longer match.
4. Hold provider/catalog work pending; unrelated health completes within 2 seconds. With no backlog and successful external responses, alert delivery begins within 60 seconds of detection.

## Auth / administration (US3)

Inject synthetic session credentials and signing secret securely at runtime. Use `CAMPLY_AUTH_MODE=session`, `CAMPLY_CORS_ORIGINS='["http://127.0.0.1:8000"]'`, and explicitly `CAMPLY_SESSION_COOKIE_SECURE=false` for HTTP-only tests; keep secure defaults for HTTPS.

Verify login, profile, authenticated mutation, rejected missing CSRF, user administration, and suspension. Local operations shows runtime health/history and intentional broker/trend limits. A direct trends call is unavailable by design. Inject runner failure and expect unhealthy health/status.

## Persistence / recovery

Interrupt after detection commits but before sending; restart with the same DB and expect saved state and pending retry. Exercise retry exhaustion and external acceptance before acknowledgment; the latter permits a documented duplicate. History clears without losing pending delivery.

Test fresh and populated upgrades with foreign keys enabled, portable UUID/JSON/list/date values, and UTC serialization. Stop the app before copying its DB, or use SQLite online backup. Do not copy just a live WAL database file. Restore to a new path and verify all state.

## Installed artifacts

Install core workspace wheels from `backend/dist` and their core dependencies into a clean environment. From outside the checkout, run `CAMPLY_RUNTIME_MODE=standalone python -m backend.standalone`. Verify packaged assets, deep links/login, and dependency inventory excluding Celery/Redis/Prometheus client/psycopg. No Node/Vite process runs. `task standalone:test` automates this scenario.

## Implementation gates

```bash
task standalone:test
task fix
task lint
task check
task test
task api:check
task pre-commit -- --all-files
```

Separately run `task admin:smoke` with Docker for distributed regression and applicable snapshots for changed admin states. These are implementation acceptance gates.

## Verification evidence (2026-10-14)

- `task test`: 558 Python tests and 235 frontend tests passed; the three opt-in integration checks run separately.
- `task check`, `task lint`, and `task api:check`: passed.
- `task snapshot:check`: all 51 existing desktop/mobile/light/dark baselines match.
- `task backend:migration:test`: PostgreSQL prior-head → current-head → repeat upgrade passed in a disposable container. SQLite fresh/populated upgrades, FK enforcement, UUID/JSON/date round trips, online backup/restore, and WAL contention checks passed.
- `task admin:smoke`: real distributed Celery/Valkey/Prometheus/API/Chromium regression passed.
- `task standalone:test`: a clean installation of the four wheels outside the checkout passed dependency/import audits excluding Celery, Redis, Prometheus client, and psycopg; packaged migrations/assets, two subscribers sharing one check, saved state and pending-delivery restart recovery, real local upstream HTTP, responsive health during a held provider request, session login/CSRF, deep-link reload, and Chromium desktop/mobile checks passed. Screenshots are generated in `tmp/standalone-smoke*.png` and uploaded by CI.
- The distributed backend Docker image built successfully with explicit distributed extras.

Unit tests additionally cover coalesced refreshes, provider failure isolation, 60/120/240-second target backoff, bounded/expired local history, current subscription eligibility and UTC minimum-stay rechecks, atomic rollback when intent insertion fails, delivery failure classification, four-attempt exhaustion, interrupted-send recovery, and terminal retention. Synthetic upstreams and temporary databases avoid real bookings or notifications.

The initial repository-wide pre-commit run encountered a duplicate-module-docstring false positive. Current main has addressed the hook configuration. TOML formatting remains owned by the dedicated pretty-format-toml hook.

## Verification evidence (2026-10-28)

The PR was rebased onto `7da9ea8` and reviewed against current search/maps, summarized notifications, result expiration/details, dependency upgrades, compression, and release workflows. See [review decisions](review.md).

- `task test`: 633 Python tests, 337 frontend tests, and nine release tests pass. All 14 opt-in backend cases are covered by separate standalone/admin/map/PostgreSQL smoke commands. `task fix`, `task lint`, `task check`, `task api:check`, and repository-wide `task pre-commit -- --all-files` pass.
- Three explicit distributed-runtime regressions verify fresh-process default startup without local runner/resources/migrations or frontend serving, real Prometheus request instrumentation, and Celery scan/summary/direct alert dispatch without outbox writes. All three pass; temporary mutations activating local startup/frontend serving, removing instrumentation, or disabling Celery alert dispatch each cause the new tests to fail. The mutations are restored and no production code changes are required.
- `task standalone:test` verifies fresh installed core wheels outside the checkout, map APIs, saved site details, summary links, gzip/immutable map worker assets, real login/CSRF, shared target checks, and alert recovery after restart. A synthetic stale wheel confirms build output is cleared before packaging.
- SQLite upgrades cover fresh storage, populated current-main data, earlier PR pending payloads, online backup/restore, foreign keys, and write contention. `task backend:migration:test` verifies the merged PostgreSQL migration graph in a disposable container.
- `task admin:smoke`, `task search:smoke`, and `task maps:verify` pass against real distributed services/PostgreSQL and Chromium where applicable. Search verification upgrades, explicitly downgrades to pre-index revision `9b2c3d4e5f6a`, and upgrades again through the merged history.
- `CAMPLY_SNAPSHOT_PORT=51866 task snapshot:check` matches all 76 current-main visual baselines. The dedicated port avoids another development server; no baselines were regenerated. Distributed admin smoke uses an already-bound API socket so other services cannot claim its port before startup.
- The distributed backend Docker image builds with the upgraded locked dependencies and distributed extras. Generated `uv.lock` formatting remains owned by uv, while manifest TOML and multi-document pnpm lock YAML use their dedicated hooks. `task test` also verifies version stamping, source distributions rebuilding into wheels, and image-publication plans without publishing.

New failure tests cover summary recounting after edited filters, qualifying stays, accepted-send acknowledgment contention without resend, fatal storage readiness, and distinct polling-cycle job identities with stable retry identities. The original outbox revision is preserved; merge revision `4d64e0e4ae18` provides a single head for both prior schemas.
