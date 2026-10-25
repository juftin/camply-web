# Tasks

- [x] Audit results, grouping and snapshot replacement; define compact-results scope.
- [x] Add regressions for grouping, bounded results and expiration.
- [x] Implement dashboard campground groups and independent pagination inside the upstream stay-date groups.
- [x] Expire past/out-of-range nights before matching saved scans.
- [x] Verify checks with `UV_CONCURRENT_BUILDS=1 task test`: 9 release, 562 backend and 334 frontend tests pass; all 76 visual snapshots match. The four standard grouped result views have zero changed pixels versus main. Preserve the local before/after gallery under `frontend/tmp/compact-results-review/`.
- [x] Update architecture docs and the global checklist.
