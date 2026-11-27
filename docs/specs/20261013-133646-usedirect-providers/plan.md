# Implementation plan

1. Probe current public metadata, classification filters, sample grids, and reservation pages. Record endpoint failures and current hosts.
2. Move shared Pydantic models and the async adapter into `providers.usedirect`. Keep thin concrete provider classes, using explicit URL configuration and booking-method overrides.
3. Add stable provider rows and a seed-only migration. Derive CLI choices/help from the registry so the metadata CLI can ingest every supported provider.
4. Verify date clipping, provider-specific request URLs and errors, per-instance caches, location defaults, atomic catalog/search refreshes, seed rollback, booking routes, and ingestion fan-out with synthetic tests.
5. Run Task quality gates and pre-commit, verify migration round trips in an isolated SQLite database, and update the roadmap/checklist and provider documentation.

## Constitution check

- Shared backend logic stays independent from the synchronous legacy CLI.
- Async I/O, DTO interfaces, Task workflows, and strict typing follow the existing architecture.
- Shared behavior is extracted once; concrete implementations contain only real provider differences.
- Specifications precede implementation; API probes and synthetic regressions verify assumptions.
