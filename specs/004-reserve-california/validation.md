# Verification

- `task lint`: backend Ruff and frontend Oxlint/Oxfmt passed.
- `task check`: backend mypy (109 source files) and frontend native TypeScript passed.
- Pre-commit hooks passed for all changed and new files, including YAML, Python, whitespace, Ruff, and Oxfmt checks.
- `task test`: 328 backend tests and 99 frontend tests passed, including 33 ReserveCalifornia regressions and a notification booking-context assertion.
- New regressions cover inclusive request grids, exclusive check-out, padded windows, UnitId identity, date de-duplication, equipment/electrical translation, blocked/walk-in/locked/draw/closed inventory, empty grids, HTTP failures, invalid dates, idempotent metadata refreshes, cross-provider park-ID collisions, SQLite search ingestion, API booking links, CLI selection/cleanup, and synthetic VCR body matching through the retry transport.
- Review regressions cover HTTP 200 application errors, hidden/offline and retired inventory, atomic metadata/search rollback, discovery of nonreservable parks with bookable campgrounds, connection-pool cleanup, and refusal to downgrade a populated provider catalog. See [the integration review](review.md) for remaining shared-system gaps.
- The metadata integration test rejects any requests except GET `fd/places` and GET `fd/facilities`, verifying that catalog refreshes remain independent of dated availability searches.
- The complete Alembic chain was applied to an isolated temporary SQLite database, downgraded by one revision, and upgraded again. Query evidence:

```text
head:         [(1, 'Recreation.gov'), (2, 'ReserveCalifornia')]
77984a1ae368: [(1, 'Recreation.gov')]
head:         [(1, 'Recreation.gov'), (2, 'ReserveCalifornia')]
```

- Live verification on 2026-10-12: metadata endpoints responded with HTTP 200. The implemented adapter found 33 campsites at facility 327 for arrival 2026-10-13 and check-out 2026-10-15, returning only nights 2026-10-13 and 2026-10-14. Its booking URL was `https://www.reservecalifornia.com/park/2/327`. A separate request beyond the booking horizon returned no free slices.
- Additional live checks found 477 RV-classified pooled units at Oceano Dunes facility 2016 and nine cabin-classified yurts at facility 752. An invalid facility returned HTTP 200 with `NightsActual=0`, confirming that application errors need explicit handling.
- Live responses remain outside the repository. All new committed fixtures use generated synthetic inventory and no reservation identifiers.

## Limits

- Request pacing is per instance; distributed provider rate limiting remains a separate roadmap item.
- Capacity is zero when upstream omits it. Provider minimum stays remain metadata; the shared worker currently enforces only the user's requested minimum stay.
- Existing test warnings remain: pytest-asyncio's unset fixture loop scope, a Pushover mock coroutine warning, and Node's experimental localStorage warning.
