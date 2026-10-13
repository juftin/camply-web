# Tasks

- [x] Add failing regression tests for scan editing and card/delete interactions.
- [x] Extend PATCH validation and safely relink shared targets.
- [x] Reuse ScanForm for editing from dashboard cards and scan details.
- [x] Fix card navigation and delete pending/error handling.
- [x] Regenerate API types and update architecture/checklist documentation.
- [x] Pass formatting, lint, type, and automated test checks.

Verified: `task test` (469 backend and 200 frontend tests passed; 6 opt-in tests
skipped), `task lint`, `task check`, `task api:check`, and `task snapshot:check`
(46 views). Generated DOM snapshots are excluded from whitespace trimming to
preserve literal whitespace. Visual evidence: [desktop editor](../../frontend/snapshots/baselines/scan-edit-dialog-desktop-light.png),
[mobile editor](../../frontend/snapshots/baselines/scan-edit-dialog-mobile-dark.png),
and [delete failure](../../frontend/snapshots/baselines/scan-delete-error-desktop-light.png).
