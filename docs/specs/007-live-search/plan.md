# Implementation plan

1. Replace PostgreSQL's custom substring/fuzzy candidate matching with weighted native full-text search and indexed pg_trgm operators. Require each token and prioritize exact displayed names; keep SQLite's portable matching for local/test environments. Verify regression behavior on PostgreSQL 17.
2. Add an Alembic migration for the weighted search-vector GIN expression and city trigram index. Existing name trigram indexes remain usable because candidate operators act on unmodified columns. Index maintenance occurs transactionally on catalog writes; no indexing workers or external services are needed.
3. Skip totals/facets for autocomplete and add deterministic pagination ordering. Verify query count and ranking.
4. Add debounced URL updates, immediate filters, navigation synchronization, abort signals, and accurate loading/pagination states to Explore. Verify interaction and cancellation tests.
5. Update developer/data/frontend docs and checklist; run Task lint, types, tests, and API drift checks.

## Constitution check

Search concerns catalog metadata, not current campsite availability. Availability checks continue to use provider APIs. Async I/O, strict typing, workspace separation, Task workflows, synthetic integration data, and test-first verification apply. PostgreSQL's full-text search and pg_trgm satisfy the explicit constraint to keep search within PostgreSQL. Migration applies to PostgreSQL and safely does nothing on SQLite.
