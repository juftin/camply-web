# Requirements Checklist: Nights of the week

**Purpose**: Standard author/reviewer review of selection semantics and compatibility before implementation.
**Created**: 2026-11-15
**Feature**: [spec.md](../spec.md)

**Review Ownership**: Reviewer-owned requirements-quality artifact. `[x]` means requirements quality is reviewed and satisfied, not implementation complete. Implementation reads markers without changing them.

## Completeness and clarity

- [x] CHK001 Are occupied-night versus arrival-day semantics and exclusive checkout explicitly defined? [Clarity, Spec FR-003]
- [x] CHK002 Are default, weekend, custom, empty and reset selections defined without contradictory meanings? [Completeness, Spec FR-001/002/007]
- [x] CHK003 Are minimum web stays and exact CLI stays distinguished while preserving eligible-night parity? [Consistency, Spec FR-005/011]
- [x] CHK004 Are omission, old saved data, unrelated edits and explicit reset covered? [Compatibility, Spec FR-007]

## Coverage and measurable outcomes

- [x] CHK005 Are gaps, different sites, cross-week dates, expiry and impossible constraints specified? [Coverage, Spec FR-004/008, Edge Cases]
- [x] CHK006 Are direct/summary alerts and edits before queued delivery covered in both runtimes? [Coverage, Spec FR-009/012]
- [x] CHK007 Are subscriber isolation and unchanged shared polling stated as measurable requirements? [Measurability, Spec FR-010, SC-005]
- [x] CHK008 Are keyboard selection, visible selected states, mobile use and failed-edit recovery defined? [Coverage, Spec FR-001/006, SC-006]
- [x] CHK009 Are matching outcomes measurable across all nonempty selections and representative seasonal openings? [Acceptance Criteria, Spec SC-001/002]
- [x] CHK010 Are dependencies and exclusions clear enough to avoid adding seasonal parsing, providers or scheduling features? [Scope, Spec Assumptions]

## Notes

Generated during the checklist phase. Review each item before implementation. See [research](../research.md) for the existing-system audit and [contract](../contracts/night-selection.md) for design-level precision.

Reviewed 2026-11-15: all ten criteria are satisfied by the named specification requirements and the explicit design contracts. No open requirement-quality issues. This review occurs before the implementation gate.
