# Research: optional standalone runtime

**Date**: 2026-10-13 | **Status**: Design research complete; implementation verified

## R1. Shared engine and minimal dependencies

**Decision**: Extract async engine functions within the existing worker package. Keep Celery adapters and their locks/retries/metrics separate. Move infrastructure libraries into distributed extras.

**Rationale**: Scanner/discovery/ingestion/delivery already use async functions but eagerly import Celery, Valkey locks, and metric objects. Backend app and operations also eagerly load Prometheus/Celery/Redis. A mode flag alone cannot provide a minimal installation.

**Alternatives considered**: Scanner duplication creates drift; Celery eager mode still needs Celery and does not provide persistent scheduling; another package or generic queue adds unnecessary structure.

## R2. SQLite lifecycle

**Decision**: Extend existing SQLite config with foreign keys, busy timeout, WAL, shared engine resources, and Alembic initialization/upgrades.

**Rationale**: SQLite is already the default driver. Models/migrations have JSON/list variants; SQLite search has portable ranking and PostgreSQL trigram creation is guarded. Existing tests often use `create_all`, so full revision-chain support still needs verification. [SQLite WAL](https://www.sqlite.org/wal.html) supports concurrent readers with one writer and needs local shared memory. [Alembic batch migrations](https://alembic.sqlalchemy.org/en/latest/batch.html) support reconstruction where SQLite cannot alter a table directly.

**Alternatives considered**: A separate storage layer or production `create_all` bypasses existing models/migration history. Support one app on local disk and short transactions.

## R3. Runner lifecycle

**Decision**: Use immediate discovery plus existing heartbeat/cooldown, daily midnight-UTC sync, and dedicated bounded scan/catalog/notification consumers managed by FastAPI lifespan.

**Rationale**: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/) provides resource startup/shutdown boundaries. The current app has no lifespan and Gunicorn defaults to multiple workers; standalone needs a dedicated one-worker launcher. Large initial catalogs cannot block startup.

**Alternatives considered**: Request background tasks cannot manage periodic/recovery work; APScheduler and a generic SQLite queue are unnecessary for these fixed jobs. Multiple web workers would create multiple schedulers.

## R4. Pending alert durability

**Decision**: Standalone commits a notification outbox with scan results; distributed keeps current Celery semantics.

**Rationale**: Current scan results commit before Celery dispatch. Volatile local dispatch would lose alerts during shutdown between persistence and sending. Retain the existing notification policy of three retries with 120-second delays. Upstream acceptance followed by a crash can duplicate delivery; no exactly-once claim.

**Alternatives considered**: A volatile queue loses alerts; adopting a durable queue for all distributed jobs expands scope.

## R5. Python-served frontend

**Decision**: Package root-based frontend assets with Python and use guarded SPA fallback after API routing.

**Rationale**: The API client defaults to `/api`; Vite base changes with `GITHUB_REPOSITORY`, requiring an explicit standalone root build. Existing cookie/CSRF behavior fits one origin but origin validation still applies. Installed assets cannot depend on repository-relative paths.

**Alternatives considered**: Node serving/reverse proxy adds a runtime process; serving TypeScript source bypasses production builds.

## R6. Admin capabilities

**Decision**: Preserve DB administration and basic local health/history. Disable trends and expose unsupported broker fields honestly.

**Rationale**: Current operations queries Celery/Valkey and trends proxies Prometheus. Fake healthy values would hide failures. Explicit local retention is 1,000 records / 24 hours, cleared on restart; durable pending alerts are separate. Sentry remains optional.

**Alternatives considered**: SQLite time-series storage recreates excluded infrastructure; hiding all operations removes useful health/sync controls.

## Implementation verification

Full SQLite revision chain with foreign keys, core-only installation/imports, parsing responsiveness, installed assets, pending delivery recovery, and distributed adapter parity. These checks are complete; see [verification evidence](quickstart.md#verification-evidence-2026-10-14).
