# Monitoring Requirements Checklist: Recreation-area coverage

**Purpose**: Reviewer assessment of coverage selection, shared observations, lifecycle and failure requirements before implementation.
**Created**: 2026-11-15
**Feature**: [Specification](../spec.md) and [technical plan](../plan.md)

**Note**: Generated through `/speckit-checklist` at standard depth, for pre-implementation review. Scope is area/all/subset correctness and shared monitoring/recovery; existing authentication and provider behavior are dependencies.
**Review Ownership**: This is a reviewer-owned requirements-quality artifact. Mark an item `[x]` only when the reviewer determines its requirements-quality criterion is satisfied.
**Marker Semantics**: `[x]` means reviewed requirements quality, not implemented behavior. All newly generated items remain unchecked.

## Requirement Completeness

- [ ] CHK001 Are all-area and fixed selected-campground coverage both explicitly required, including a one-campground subset? [Completeness, Spec §FR-001–FR-004]
- [ ] CHK002 Are area monitoring entry points and complete choice discovery defined independently of map bounds and discovery pages? [Completeness, Spec §FR-002–FR-004]
- [ ] CHK003 Are shared dates/preferences, one saved-scan identity, and unavailable-selection representation specified? [Completeness, Spec §FR-001, §FR-005, §FR-007]
- [ ] CHK004 Are migration, compatibility and rollback requirements stated without claiming existing data can be discarded? [Completeness, Spec §FR-016; Data model §Migration and rollback]

## Requirement Clarity

- [ ] CHK005 Is “eligible campground” defined by exact provider/parent membership and enabled/reservable status? [Clarity, Spec §FR-004]
- [ ] CHK006 Is selecting all current members explicitly distinguished from dynamic all-area coverage? [Clarity, Spec §User Story 2, §FR-003]
- [ ] CHK007 Are duplicate-definition semantics precise for order, repeated IDs, dates, modes and preferences? [Clarity, Spec §FR-009]
- [ ] CHK008 Are round completion, retry/deadline failure and full-success freshness defined independently from notification windows? [Clarity, Spec §FR-013–FR-015; Worker contract §Scheduling and completion]

## Requirement Consistency

- [ ] CHK009 Do subset membership-change rules consistently exclude automatic additions while retaining unavailable choices? [Consistency, Spec §FR-005; HTTP contract §Create and update]
- [ ] CHK010 Do unavailable-coverage edit rules agree with creation validation and preserved active preferences? [Consistency, Spec §FR-006–FR-008]
- [ ] CHK011 Do one-scan management and one-shared-check rules distinguish subscriptions, destinations and polling targets consistently? [Consistency, Spec §FR-007, §FR-010; Plan §Summary]
- [ ] CHK012 Are timely summaries compatible with bounded retries and slow/failed campgrounds rather than waiting for a full round? [Consistency, Spec §FR-013–FR-015; Research §R4–R5]

## Acceptance Criteria Quality

- [ ] CHK013 Does all-area acceptance measure complete coverage beyond the first discovery page? [Measurability, Spec §SC-001]
- [ ] CHK014 Do subset acceptance criteria isolate unselected/new members from results, counts and alerts? [Measurability, Spec §SC-002–SC-003]
- [ ] CHK015 Are shared-check counts and independent preference matching measurable for overlapping users/scans? [Measurability, Spec §SC-004]
- [ ] CHK016 Are healthy-path alert timing and logical-intent deduplication distinguished from external receipt during outages/crashes? [Measurability, Spec §SC-005; Worker contract §Notification aggregation and delivery]

## Scenario and Edge Case Coverage

- [ ] CHK017 Are primary, alternate, validation-failure and recovery flows specified for both coverage modes? [Coverage, Spec §User Stories 1–4, §Edge Cases]
- [ ] CHK018 Are empty areas, disabled/removed parents, moved members and restored fixed selections addressed? [Coverage, Spec §Edge Cases, §FR-005–FR-006]
- [ ] CHK019 Are repeated campsite IDs and separated/expired nights covered without combining sites or campgrounds? [Coverage, Spec §FR-011, §SC-003]
- [ ] CHK020 Are concurrent duplicate creates/edits and callbacks after scope changes addressed without losing another subscriber's state? [Coverage, Spec §FR-008–FR-010; HTTP contract §Create and update]
- [ ] CHK021 Are failed/incomplete catalogs distinguished from complete membership removal and post-publication enrichment failure? [Coverage, Spec §FR-005; Research §R3]
- [ ] CHK022 Are successful empty observations, retained failed observations, restart recovery and abandoned attempts separately specified? [Coverage, Spec §FR-013–FR-014; Worker contract §Scheduling and completion]

## Non-Functional Requirements

- [ ] CHK023 Are existing ownership, invitation, suspension, credentials and CSRF boundaries preserved for every area operation/delivery? [Security, Spec §FR-008, §FR-016; HTTP contract]
- [ ] CHK024 Are both runtime modes, bounded scheduling, provider pacing and cached-only page reads required? [Reliability, Spec §FR-017]
- [ ] CHK025 Are keyboard access, mobile/desktop selection, draft preservation and honest partial-result messages defined? [Accessibility, Spec §FR-018, §SC-007; UI contract]

## Dependencies and Assumptions

- [ ] CHK026 Are provider-defined membership and catalog refresh latency explicit dependencies rather than live-discovery promises? [Dependency, Spec §Assumptions]
- [ ] CHK027 Are SQLite/PostgreSQL portability and packaged-migration constraints aligned with the project constitution? [Dependency, Plan §Constitution Check; Data model §Migration and rollback]
- [ ] CHK028 Are cross-area collections, per-campground preferences, new providers, and CLI changes clearly outside scope? [Scope, Spec §Assumptions]

## Notes

- This checklist is new and has 28 reviewer-owned items. No item has been marked reviewed by the agent.
- `/speckit-implement` reads checklist state as a gate and must not modify these markers.
- The built-in [requirements checklist](requirements.md) has its separate specification/clarification lifecycle.
- Add review findings beside the relevant numbered item. Technical validation procedures are in [quickstart.md](../quickstart.md), not in this requirements checklist.
