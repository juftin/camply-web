---
description: "Actionable tasks for the Checklist Data Layer implementation"
---

# Tasks: Checklist Data Layer

**Input**: Design documents from `/specs/001-checklist-data-layer/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Unit tests are REQUIRED as per Success Criterion SC-001 in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Backend DB Package**: `backend/packages/db/`
- **Models**: `backend/packages/db/db/models/`
- **Tests**: `backend/packages/db/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 [P] Configure export of new models in `backend/packages/db/db/models/__init__.py`
- [x] T002 [P] Initialize model test suite in `backend/packages/db/tests/test_models.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Verify `backend/packages/db/db/models/base.py` compatibility for SQLAlchemy 2.0 Mapped types and composite keys

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Early Access User Identification (Priority: P1) 🎯 MVP

**Goal**: Implement the User model with early access flagging and Auth0 integration support.

**Independent Test**: Create a User in `test_models.py` and verify `is_early_access_user` flag persists and defaults to False.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Write failing unit tests for User model CRUD and constraints in `backend/packages/db/tests/test_models.py`

### Implementation for User Story 1

- [x] T005 [US1] Implement User model with `is_early_access_user`, `auth0_id`, and `email` in `backend/packages/db/db/models/users.py`

**Checkpoint**: User Story 1 is functional and testable independently.

---

## Phase 4: User Story 2 - Efficient De-duplicated Polling (Priority: P1)

**Goal**: Implement the UniqueTarget model with SHA256 hashing for de-duplication.

**Independent Test**: Attempt to create two UniqueTarget records with identical provider/campground/dates and verify the second one fails or returns the first via hash constraint.

### Tests for User Story 2

- [x] T006 [P] [US2] Write failing unit tests for UniqueTarget hashing logic and uniqueness constraints in `backend/packages/db/tests/test_models.py`

### Implementation for User Story 2

- [x] T007 [US2] Implement UniqueTarget model with SHA256 hash calculation and constraints in `backend/packages/db/db/models/unique_targets.py`

**Checkpoint**: User Story 2 is functional and testable independently.

---

## Phase 5: User Story 3 - User-Specific Search Filtering (Priority: P2)

**Goal**: Implement the UserScan model with individual user filters (min stay, preferred types, electric).

**Independent Test**: Create a UserScan record linked to a User and UniqueTarget, and verify the `preferred_types` ARRAY persists correctly.

### Tests for User Story 3

- [x] T008 [P] [US3] Write failing unit tests for UserScan filters and relationships in `backend/packages/db/tests/test_models.py`

### Implementation for User Story 3

- [x] T009 [US3] Implement UserScan model with `ARRAY(String)` and `JSONB` filter support in `backend/packages/db/db/models/user_scans.py`

**Checkpoint**: User Story 3 is functional and testable independently.

---

## Phase 6: User Story 4 - Availability Result Caching (Priority: P2)

**Goal**: Implement the ScanResult model for caching campsite availability findings.

**Independent Test**: Store a ScanResult with a JSONB array of dates and verify it can be retrieved and parsed.

### Tests for User Story 4

- [x] T010 [P] [US4] Write failing unit tests for ScanResult JSONB storage and campsite relationships in `backend/packages/db/tests/test_models.py`

### Implementation for User Story 4

- [x] T011 [US4] Implement ScanResult model with `available_dates` JSONB field in `backend/packages/db/db/models/scan_results.py`

**Checkpoint**: All user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T012 Generate Alembic migration for all new models using `task backend:migration -- "add checklist models"`
- [x] T013 Run and verify migrations against local database using `task backend:migrate`
- [x] T014 Final test execution and verification of `backend/packages/db/tests/test_models.py` across all models
- [x] T015 [P] Update `backend/packages/db/README.md` with documentation for the new checklist data layer models
- [x] T016 Run `quickstart.md` validation steps to ensure developer onboarding is smooth

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - User Story 1 (US1) is independent.
  - User Story 2 (US2) is independent.
  - User Story 3 (US3) depends on US1 and US2 (foreign keys).
  - User Story 4 (US4) depends on US2 (foreign key).
- **Polish (Final Phase)**: Depends on all user stories being complete.

### User Story Dependencies

- **User Story 3 (US3)**: Requires `users` (US1) and `unique_targets` (US2) tables to exist for foreign key relationships.
- **User Story 4 (US4)**: Requires `unique_targets` (US2) table to exist for foreign key relationship.

### Within Each User Story

- Unit tests MUST be written and FAIL before implementation.
- Models before migrations.
- Story complete before moving to next priority if working sequentially.

### Parallel Opportunities

- T001 and T002 (Setup) can run in parallel.
- US1 and US2 can be implemented in parallel.
- Once US2 is complete, US4 can start in parallel with US1.
- All test tasks marked [P] can run in parallel.
- Documenting (T015) can happen once models are stabilized.

---

## Parallel Example: User Stories 1 & 2

```bash
# Developer A: Implement User Story 1
Task: "Write failing unit tests for User model in backend/packages/db/tests/test_models.py"
Task: "Implement User model in backend/packages/db/db/models/users.py"

# Developer B: Implement User Story 2
Task: "Write failing unit tests for UniqueTarget model in backend/packages/db/tests/test_models.py"
Task: "Implement UniqueTarget model in backend/packages/db/db/models/unique_targets.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2)

1. Complete Phase 1 & 2.
2. Complete Phase 3 (US1) & Phase 4 (US2).
3. **STOP and VALIDATE**: Test US1 and US2 independently. This provides the core user and target tracking capability.

### Incremental Delivery

1. Setup + Foundation → Baseline ready.
2. US1 + US2 → Core entities ready.
3. US3 → Filtering logic ready.
4. US4 → Result caching ready.
5. Polish → Schema finalized and documented.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- Unit tests are mandatory to satisfy SC-001.
- SHA256 hashing is the chosen strategy for de-duplication as per research.md.
