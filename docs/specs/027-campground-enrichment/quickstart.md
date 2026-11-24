# Enrichment validation guide

1. Run `task install` and the focused destination/provider/migration tests named in `tasks.md`. Fixtures are synthetic; no operator database or API credentials are required.
2. Apply migrations only to a disposable SQLite database and verify old rows, enriched rows, downgrade, and upgrade. Run the existing disposable PostgreSQL workflow when Docker is available.
3. Regenerate client declarations with `task api:generate`. Verify the two detail endpoints include typed cached details while child/search/map responses exclude them.
4. Run frontend gallery tests and inspect campground and area pages using synthetic enriched fixtures at desktop/mobile sizes in both themes. Exercise keyboard dialog navigation, caption/source display, and missing/broken-image fallbacks.
5. Run `task fix`, `task lint`, `task check`, `task test`, `task docs:check`, and configured pre-commit hooks. Use the existing visual workflow for any changed baseline.

For an operator deployment after migration, `camply db metadata --provider-id 1` imports the catalog and a bounded stale-details batch. Repeating metadata refreshes continues the backlog; successful snapshots remain fresh for seven days. Scheduled standalone/distributed ingestion follows the same path. Remote image failure must never block discovery or monitoring.
