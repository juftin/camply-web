# Implementation Plan: Recreation-area and selected-campground monitoring

**Branch**: `flawless-elk` | **Date**: 2026-11-15 | **Spec**: [spec.md](spec.md)

**Input**: [Recreation Area Monitoring specification](spec.md). **Status**: Design complete; implementation explicitly not started.

## Summary

Allow one saved scan to cover all eligible campgrounds in one recreation area or a fixed selected subset. Keep campground scans and campground/date shared targets, add a resolved scan-to-target association, and make catalog membership, result attribution, lifecycle controls, and notification guards area-aware. Preserve shared provider observations and both deployment modes.

The deliverable in this change is the pre-implementation design, requirements review checklist, and task backlog. No migrations, application code, generated client, or implementation tests are changed now.

## Technical Context

**Language/Version**: Python >=3.11, Python 3.14 development/CI defaults; existing React 18 and TypeScript toolchain.

**Primary Dependencies**: Existing SQLAlchemy 2, Alembic, Pydantic 2, FastAPI, asyncio, Celery/Valkey adapters; React, TanStack Query, React Hook Form/Zod, Shadcn/UI. No new dependency is planned.

**Storage**: PostgreSQL for distributed mode and file-backed SQLite for standalone; portable JSON and named constraints. Existing migrations remain packaged in `camply.db`.

**Testing**: pytest with synthetic provider/notification responses, Vitest/Testing Library, browser fixtures and visual snapshots, populated-database migration checks, installed-package regressions, generated OpenAPI checks.

**Target Platform**: Existing standalone Python server and distributed application; mobile/desktop browsers.

**Project Type**: Existing full-stack web application and shared polling engine; foreground CLI behavior is outside scope.

**Performance Goals**: Exhaustive coverage of a 125-campground fixture; three logical checks for ten users sharing three campground/date targets; five-second summary windows and one-second delivery discovery preserve the 60-second healthy-path notification objective.

**Constraints**: No provider request per subscriber, no provider I/O from page reads, bounded queues and retries, short write transactions, no service imports in base persistence/providers, and no speculative scheduling framework. Whole-check budget is 90 seconds; distributed lock leases must exceed it by at least 15 seconds. Existing target cooldown and runtime backoffs remain authoritative.

**Scale/Scope**: One provider-defined area per area scan, either dynamic all coverage or fixed one-or-more selections. No custom cross-area collections, per-campground preferences, new providers, or CLI changes.

## Constitution Check

Gates evaluated before research and rechecked after design; both pass at design level. Passing design gates does not claim implementation or test completion.

| Principle                           | Before research                                                      | After design evidence                                                                                                                     |
| ----------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| I. Reliability and precision        | Pass: preserve provider-verified observations and failure retention. | Pass: qualified matches, atomic catalog publication, persisted coverage state, short durable summary windows and timing tests.            |
| II. Type safety and static analysis | Pass: use existing typed boundaries.                                 | Pass: request variants, response contracts, generated types, mypy/native TypeScript and lint gates in tasks.                              |
| III. Modern workflow and automation | Pass: existing Task/uv workflow.                                     | Pass: validation uses root Task commands; no dependency or runtime process is added outside existing adapters.                            |
| IV. Monorepo and separation         | Pass: reuse existing distribution and layers.                        | Pass: `camply.db` owns persistence/coverage queries; worker owns scheduling/delivery; server owns HTTP; React stays under `src/frontend`. |
| V. Automated verification           | Pass: tests will precede behavior changes.                           | Pass: story-specific unit/integration/browser tasks plus both-database migrations and both-runtime regression gates.                      |

No constitution amendment or exception is needed.

## Project Structure

### Documentation (this feature)

```text
docs/specs/20261115-200611-recreation-area-monitoring/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── scans.md
│   ├── worker.md
│   └── ui.md
├── checklists/
│   ├── requirements.md
│   └── monitoring.md
└── tasks.md
```

### Source Code (repository root, planned changes only)

```text
src/camply/db/
  coverage.py                              # shared definition/membership/eligibility queries
  availability.py
  models/{user_scans,scan_targets,unique_targets,notification_outbox,providers}.py
  migrations/versions/                     # generated revision during implementation
src/camply/providers/recreation_gov/
  provider.py
  models/{recreation_area,campgrounds}.py
src/camply/worker/
  engine/{coverage,area_alerts,discovery,scanner,catalog}.py
  runtime.py, outbox.py, config.py, celery_app.py
  tasks/{heartbeat,scanner,notifications}.py
src/camply/server/
  schemas.py
  routers/{scans,recreation_areas,admin}.py
src/frontend/
  components/{ScanForm,ScanCard,FoundCampsites,ExploreMap}.tsx
  pages/{RecreationArea,SearchPage,Dashboard,ScanDetail}.tsx
  pages/admin/
  hooks/useScans.ts
  lib/{api,structs}.ts
  lib/api/generated/schema.ts
tests/{db,providers,worker,server,packaging}/
src/frontend/**/*.test.tsx
src/frontend/tooling/                       # synthetic browser/visual scenarios
```

**Structure Decision**: Extend the existing monorepo and shared engine. New modules isolate only reused coverage queries and area-specific scheduling/summary behavior. Keep the existing optional dependency boundaries and installed migration resource path.

## Phase 0: Research and decisions

[research.md](research.md) resolves polling identity, membership publication, round durability, actual timeout gaps, summary concurrency, compatible contracts, and migration safety. The clarification review found no product question blocking design. Repository research identified that the specification's original “existing check failure deadline” was not present in code; the spec now delegates that bounded policy to planning, and R4 supplies it.

## Phase 1: Data and interface design

1. **Definitions and migration**: Persist provider/destination/dates/mode/fixed selection on each scan; add one `scan_targets` association for current resolved coverage. Backfill campground scans without changing IDs or snapshots. Add normalized unique definitions and publication/revision guards. See [data-model.md](data-model.md).
2. **Membership and rounds**: Reconcile complete confirmed membership on creation/edit and before area rounds. Retain unavailable selections independently. Use one durable current round per area scan, outcomes per target link, shared attempt identities, bounded deadlines and restart recovery. Retire excluded links and revalidate coverage immediately before using results or sending alerts. See [worker contract](contracts/worker.md).
3. **HTTP and UI**: Accept old campground creation and patch shapes; add area all/selected variants. Add a separate bounded eligible-choice route, qualified results, explicit freshness/coverage fields, and area-aware admin views. See [scan contracts](contracts/scans.md) and [UI contracts](contracts/ui.md).
4. **Notifications**: Accumulate area summary candidates in existing outbox rows for fixed five-second windows; use unique intent identity, versioned appends and atomic claims. Deliver from either runtime independently of availability heartbeat. Recheck each candidate's target coverage, current filters/access/channel before sending. Preserve existing campground paths and use the same qualified guards for area direct alerts.
5. **Verification and rollout**: Follow [quickstart.md](quickstart.md). Stop all application roles before migration, validate both databases and backfill, then deploy matched API/worker/frontend versions. Old workers must not run against generalized scans. No production migration or deployment is part of this planning work.

## Delivery order and acceptance gates

Foundation includes portable schema/backfill, centralized coverage queries, and confirmed catalog publication. US1 delivers all-area creation and shared execution; US2 adds fixed selection; US3 completes attributed results, truthful coverage status and summary delivery; US4 completes lifecycle/admin isolation. Tests precede each slice. US1 is a useful development increment; the release requires US1–US4, including selected coverage and notification guards.

Use [tasks.md](tasks.md) as the executable backlog after explicit authorization to implement. The reviewer-owned [monitoring checklist](checklists/monitoring.md) remains unchecked pending review; it measures requirements quality, not implemented behavior. Convergence belongs after implementation and is intentionally not run now.

## Complexity Tracking

No constitution violations. One new association table is necessary for shared many-campground coverage. Current-round fields and the existing outbox avoid new history and batch table families. Compatibility pointers remain campground-only; centralized queries prevent two competing eligibility paths.
