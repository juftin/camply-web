# Quickstart validation: standalone runtime

**Status**: Future validation guide. These commands become available only after [tasks.md](tasks.md) is implemented.

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

## Future implementation gates

```bash
task standalone:test
task fix
task lint
task check
task test
task api:check
task pre-commit -- --all-files
```

Separately run `task admin:smoke` with Docker for distributed regression and applicable snapshots for changed admin states. These are future implementation acceptance results, not claimed by this planning PR.
