# Tasks: Continue destination enrichment

## Phase 1: Diagnosis and design

- [x] T001 Reproduce missing Many Glacier details and partial initial batches with read-only checks; record evidence in `research.md`.
- [x] T002 Define behavior, bounded background contracts, and validation in `spec.md`, `plan.md`, `data-model.md`, `contracts/background.md`, and `quickstart.md`.

## Phase 2: Shared batch engine

- [x] T003 [US1] Add failing >100 destination progression, fresh/unsupported work, and client cleanup tests in `tests/providers/test_enrichment_refresh.py`.
- [x] T004 [US1] Return optional enrichment success in `src/camply/providers/enrichment.py` and add enrichment-only execution in `src/camply/worker/engine/catalog.py`.

## Phase 3: Automatic runtime progress

- [x] T005 [US1] Add failing fan-out/continuation/periodic-registration tests in `tests/worker/test_ingestion.py` and `tests/worker/test_celery_app.py`.
- [x] T006 [US1] Schedule independent provider detail discovery and bounded continuations in `src/camply/worker/tasks/ingestion.py` and `src/camply/worker/celery_app.py`.
- [x] T007 [US2] Add local startup, continuation, failure isolation, and cancellation tests in `tests/worker/test_runtime.py`.
- [x] T008 [US2] Add supervised independent enrichment to `src/camply/worker/runtime.py` using the shared engine.

## Phase 4: Verification and operations

- [x] T009 Update `docs/operations/RUNNING.md`, `docs/architecture/DESIGN_PROVIDERS.md`, and `docs/CHECKLIST.md` with automatic backfill behavior and release instructions.
- [x] T010 Run focused regressions, required quality/full tests and hooks; record results in `validation.md`, inspect convergence, and prepare the follow-up PR.

## Dependencies and execution

T001–T002 precede tests and implementation. T003 precedes T004; T005 precedes T006; T007 precedes T008. Both runtimes depend on T004. T009–T010 close the change after both stories pass. The distributed and standalone adapters can be tested independently after the shared batch engine; no parallel agents are needed for this bounded fix.
