# Tasks

- [x] Add failing regression tests for scan editing and card/delete interactions.
- [x] Extend PATCH validation and safely relink shared targets.
- [x] Reuse ScanForm for editing from dashboard cards and scan details.
- [x] Fix card navigation and delete pending/error handling.
- [x] Regenerate API types and update architecture/checklist documentation.
- [x] Pass formatting, lint, type, and automated test checks.

Verified: `task test` (469 backend and 220 frontend tests passed; 6 opt-in tests
skipped), `task lint`, `task check`, `task api:check`, and `task snapshot:check`
(48 views). Generated DOM snapshots are excluded from whitespace trimming to
preserve literal whitespace. Visual evidence: [desktop editor](../../../tests/frontend/snapshots/baselines/scan-edit-dialog-desktop-light.png),
[mobile editor](../../../tests/frontend/snapshots/baselines/scan-edit-dialog-mobile-dark.png),
and [delete failure](../../../tests/frontend/snapshots/baselines/scan-delete-error-desktop-light.png).

Calendar integration preserves checkout anchoring and duration presets when
editing saved scans. Both the creation-calendar and editing regression suites
are retained, including an edited check-in advancing checkout by the minimum stay.
