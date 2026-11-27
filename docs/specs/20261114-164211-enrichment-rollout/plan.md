# Implementation Plan: Continue destination enrichment

**Branch**: `fix/enrichment-rollout` | **Date**: 2026-11-14 | **Spec**: [spec.md](spec.md)

## Summary

Add independent periodic enrichment discovery and bounded continuations. Daily catalog ingestion continues to import catalogs and seed one batch. The new work resumes existing backlog after rollout, performs no catalog import, and chains successful batches until no eligible work remains. Local standalone work follows the same provider engine and yields between passes.

## Technical Context

Python >=3.11 (development 3.14), existing SQLAlchemy JSON cache, asyncio local runner, and optional Celery adapter. No dependency, schema, HTTP contract, or UI changes. Pytest synthetic storage and mocked task transport verify behavior. Keep 100-record batches, seven-day freshness, one-hour retry cooldown, and atomic claims.

## Constitution Check

Pre-design and post-design: all five principles satisfied. Availability paths remain independent; functions are typed and tested; workflows use Taskfile; shared engine imports no Celery/Valkey; mocks and isolated databases reproduce the production rollout gap. No exceptions required.

## Research and Design

See [research.md](research.md). All constraints are established in the existing code; no new technology choice or unresolved research requires delegation.

1. Make the existing optional enrichment wrapper return success/failure while preserving catalog failure isolation.
2. Add an enrichment-only function in `src/camply/worker/engine/catalog.py`. Skip unsupported/fresh providers before client creation, run one batch, close the client, and return whether eligible work remains. Do not continue a whole-batch failure immediately.
3. Add Celery fan-out and per-provider detail tasks in `tasks/ingestion.py`, scheduled each heartbeat in `celery_app.py`. A successful batch with due work schedules a continuation with a short delay, yielding the queue to availability work. Periodic discovery recovers failures/restarts without relying on catalog imports.
4. Add a supervised local enrichment loop before the notification consumer in `worker/runtime.py`. Cycle providers independently, immediately repeat successful pending work after a short yield, and wait one heartbeat when no successful backlog remains. Preserve notification supervision order and shutdown cancellation.
5. Verify >100 destination progress, empty/fresh/unsupported work, client cleanup, failure isolation, cooldowns, continuation dispatch, registration, runtime startup, and cancellation. Update operating docs and global checklist.

## Project Structure

Source changes are confined to `src/camply/providers/enrichment.py`, `src/camply/worker/engine/catalog.py`, `src/camply/worker/tasks/ingestion.py`, `src/camply/worker/celery_app.py`, and `src/camply/worker/runtime.py`. Tests extend provider and worker suites. Design artifacts stay in `docs/specs/20261114-164211-enrichment-rollout/`.

## Complexity Tracking

No new infrastructure, queues, configuration settings, migrations, provider APIs, or cache formats. Existing worker adapters and persistent attempt claims handle scheduling and concurrency. Remaining images depend on upstream coverage and successful background processing.
