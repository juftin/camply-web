# Implementation Plan: Nights of the week

**Branch**: `loud-catfish` | **Feature**: `20261115-104517-weekday-night-filter` | **Date**: 2026-11-15 | **Spec**: [spec.md](spec.md)

## Summary

Add a saved, per-scan night selection to the existing web scan workflow and preserve the CLI's day/weekend contract. Filter occupied nights before evaluating consecutive stays everywhere results and alerts are matched. Keep shared polling independent of preferences. See [research](research.md), [data model](data-model.md), [contracts](contracts/night-selection.md), and [validation guide](quickstart.md).

## Technical Context

**Language/Version**: Python >=3.11, development 3.14; React/TypeScript using existing locked versions.

**Primary Dependencies**: Existing SQLAlchemy/Alembic, Pydantic/FastAPI, React Hook Form/Zod, and generated API types. No new dependencies.

**Storage**: Nullable JSON array on `user_scans`, portable across SQLite and PostgreSQL; no changes to shared target identity.

**Testing**: Pytest for calendar matching, API, worker delivery, migration, CLI parity; Vitest/Testing Library for form and summaries; existing visual snapshots for changed form/card/detail views.

**Target Platform**: Supported CLI platforms, standalone SQLite runtime, distributed PostgreSQL/Celery runtime; desktop/mobile web.

**Project Type**: Existing CLI and full-stack web application.

**Performance Goals**: No additional provider polling or notification delivery for excluded nights; filtering stays linear in observed nights apart from existing sorting.

**Constraints**: Current exclusive checkout, UTC expiration, same-site consecutive matching, exact CLI versus minimum web stay semantics, ownership, duplicate subscriptions, and queue behavior remain in effect.

**Scale/Scope**: Seven weekdays, all 127 nonempty subsets; existing date range limits. No seasonal parser, holidays, new provider work, or scheduling changes.

## Constitution Check

Pre-research and post-design gates PASS:

- Reliability: observed provider dates remain authoritative; all result/delivery paths use filtered consecutive stays.
- Types: typed validated preference; regenerate public client; run Python and TypeScript checks.
- Workflow: existing Task commands and uv environment; no dependency changes.
- Boundaries: shared matching and models stay in `camply.db`; no imports from server/worker into base.
- Verification: behavior regressions before implementation, synthetic provider observations, API and worker integration tests, portable migration coverage, and frontend interaction coverage.

No constitution exceptions are needed.

## Project Structure

### Documentation (this feature)

`docs/specs/20261115-104517-weekday-night-filter/` retains spec, research, plan, data model, contracts, quickstart, quality checklists, and dependency-ordered tasks.

### Source Code (repository root)

- `src/camply/db/models/user_scans.py`, `db/migrations/versions/`: nullable `allowed_weekdays` with an additive migration.
- `src/camply/db/availability.py`: filter optional weekdays before grouping; calendar feasibility validation shared by create/edit.
- `src/camply/server/schemas.py`, `server/routers/scans.py`: strict day validation, merged-edit feasibility, persistence and response fields.
- `src/camply/worker/engine/alerts.py`, `engine/notifications.py`: filter detection and revalidate distributed delivery; existing `worker/outbox.py` provides shared current-payload logic.
- `src/frontend/components/{ScanForm,ScanCard}.tsx`, `pages/ScanDetail.tsx`, `lib/`: accessible selection, validation and named preference summaries; regenerate `lib/api/generated/schema.ts`.
- `tests/{db,server/routers,worker,core,cli}/`, frontend colocated tests and visual baselines: behavior and compatibility coverage.
- `docs/architecture/DESIGN_{DATA,API,FRONTEND,NOTIFICATIONS}.md`, `docs/cli.md`, `docs/CHECKLIST.md`: current contracts and user instructions.

**Structure Decision**: Extend existing layers and shared helpers; no new service, public route, or standalone abstraction beyond reusable night formatting.

## Execution and validation

1. Establish migration, matcher, and request contract with failing behavioral regressions.
2. Implement web persistence/validation and consistent result/alert matching.
3. Add form controls and saved summaries; preserve and test CLI parity.
4. Regenerate client, update docs and affected visual baselines, run `task fix`, `task lint`, `task check`, `task test`, and `task api:check`; report environmental limitations explicitly.
5. Audit against every requirement and append any remaining tasks through convergence; repeat until no gaps remain.
