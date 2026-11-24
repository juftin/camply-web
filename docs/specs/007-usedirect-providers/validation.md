# Verification

## Automated checks

- `task lint`: backend Ruff and frontend Oxlint/Oxfmt passed.
- `task check`: mypy passed for 115 source files; frontend native TypeScript passed.
- `task test`: **383 backend tests and 99 frontend tests passed**.
- Pre-commit hooks passed for every changed and new file, including Python, YAML, whitespace, Ruff, and Oxfmt checks.
- 42 new shared-provider regressions cover all ten concrete UseDirect providers (California plus nine additions), provider-specific request and booking URLs, application errors, instance-local filters, location normalization, overlapping catalog IDs, metadata-only requests, and explicit non-electric classifications.
- The 33 California regressions continue to pass after extracting shared models and behavior.
- Ten additional seed-migration regressions verify application/seed identity parity, empty-catalog rollback, unrelated-provider preservation, and populated-catalog rollback protection for each new provider ID.
- Three worker ingestion regressions verify registry fan-out, metadata-only operation without active user scans, and client cleanup on both success and failure.

## Migration lifecycle

The complete migration chain was applied to an isolated temporary SQLite database:

- At `ea6111bf3bed`: provider IDs 1–11 exist.
- Downgrade one revision: only Recreation.gov (1) and ReserveCalifornia (2) remain.
- Re-upgrade: all eleven identities return.
- Add a synthetic Northern Territory campground and attempt downgrade: rollback is rejected, all identities remain, and migration head stays `ea6111bf3bed`.

The database was removed after verification. No application database was modified.

## Live adapter checks

On 2026-10-12, each new provider's parks, facilities, classification filters, sample grid, and booking application responded successfully. The implemented adapter then performed independent metadata syncs into one temporary SQLite database, followed by separate availability searches for arrival 2026-10-20 and checkout 2026-10-22:

| Provider           | Parks saved | Facilities saved | Search rows | Available units in sampled facility |
| ------------------ | ----------- | ---------------- | ----------- | ----------------------------------- |
| Florida            | 147         | 313              | 313         | 30                                  |
| Virginia           | 44          | 200              | 215         | 6                                   |
| Minnesota          | 152         | 351              | 374         | 3                                   |
| Ohio               | 71          | 638              | 540         | 45                                  |
| Arizona            | 25          | 115              | 81          | 12                                  |
| Missouri           | 114         | 211              | 252         | 43                                  |
| Fairfax County     | 344         | 134              | 342         | 100                                 |
| Oregon Metro       | 141         | 320              | 31          | 0                                   |
| Northern Territory | 33          | 177              | 193         | 8                                   |

In total, 1,071 parks and 2,459 facilities were saved independently of availability. Catalog and search counts differ because hidden/offline inventory remains in metadata but is excluded from searchable campgrounds. Oregon's grid response was valid with no bookable slices for the sampled dates.

Public API responses and the temporary database remain outside the repository and the database was removed. Committed fixtures are synthetic and contain no reservation identifiers. Live checks also confirmed Ohio/Fairfax non-electric classifications, dirty state fields in Florida/Virginia, current Ohio/Missouri booking hosts, and Australia's country default.

Alabama and Maricopa legacy catalog endpoints returned HTTP 404; no identities were registered or seeded for them. See [provider TODOs](TODO.md).

## Limits

- Booking-page HTTP checks verify application reachability; no reservations were made. Regional facility deep links remain a TODO, with verified reservation-search fallbacks in use.
- Provider minimum stays, residency-dependent advance windows, distributed pacing/cache, initial-ingestion automation, and individual campsite persistence remain the documented shared-system follow-ups.
- Production PostgreSQL, real Celery/Valkey scheduling, and notification delivery were not exercised.
- Existing pytest-asyncio, Pushover mock-coroutine, and Node localStorage warnings remain unchanged.
