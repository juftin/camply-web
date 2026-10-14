# Tasks

- [x] T1 Add regression tests for PostgreSQL relevance and live Explore.
- [x] T2 Implement native full-text matching, indexed typo tolerance, stable ordering, and fast autocomplete.
- [x] T3 Add and verify PostgreSQL search index migration.
- [x] T4 Implement live typing/filtering, navigation synchronization, and cancellation.
- [x] T5 Verify real PostgreSQL using synthetic fixtures.
- [x] T6 Update documentation/checklist and pass lint, type, test, and contract checks.

## Verification

- `task test`: 500 backend tests and 233 frontend tests passed; opt-in suites skipped in the normal run.
- `task search:smoke`: all 9 real PostgreSQL tests passed, including full migration upgrade/downgrade and index selection on 20,000 synthetic rows.
- `task check`, `task lint`, and `task api:check`: passed.
- `task snapshot:check`: all 51 views match existing baselines.
- Pre-commit: all applicable hooks passed except `check-docstring-first`, which rejects intentional module attribute docstrings. The untouched HEAD version of `search.py` fails the same hook; attribute docstrings are required by the repository's agent instructions.

## Existing catalog limitation

Provider imports currently populate names and locations but omit amenity/RV fields from Search rows. Those filters execute live against stored metadata, but need provider metadata enrichment to yield useful catalog results. This change does not infer amenities from incomplete availability results.
