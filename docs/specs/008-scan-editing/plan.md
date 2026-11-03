# Implementation plan

1. Extend the existing PATCH contract with optional campground/provider/date
   fields. Resolve a de-duplicated target instead of mutating shared targets;
   validate merged dates and reject duplicate subscriptions.
   Verify with API tests for partial updates, ownership, target reuse and isolation.
2. Reuse ScanForm for creation and editing, resetting to saved values on open.
   Add edit actions on cards and details, and invalidate scan queries after save.
   Verify prefill, submission, cancellation, failures, and suspension behavior.
3. Move card controls outside the detail link and await deletion in its dialog.
   Verify navigation isolation, pending state, failures, cancel, and success.
4. Regenerate OpenAPI types, update architecture/checklist documentation, and run
   Task formatting, lint, type, and test workflows.

Constitution check: retain existing auth and ownership guards, Pydantic DTOs,
TanStack Query, Shadcn dialogs, and monorepo boundaries. No model changes or
migration are necessary. Use synthetic test data; no external provider requests.
