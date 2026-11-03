# PostgreSQL search and live Explore

## User stories

- Find parks and campgrounds by name, partial name, location, or misspelling, with strong name matches ahead of weak matches.
- Explore the catalog while typing and changing filters without pressing Search; bookmark and revisit the query, sort, and page.
- Keep all search infrastructure inside PostgreSQL, with no external indexing service.

## Requirements

- Use PostgreSQL's native weighted full-text search and GIN indexes, with indexed pg_trgm word matching for typo tolerance. Every query token must match; punctuation must not become SQL wildcards or query operators.
- Rank exact displayed names ahead of parent-name and fuzzy matches. Use deterministic tie breakers so pagination is stable.
- Preserve existing response contracts, provider isolation, facets, pagination, and filters. Avoid counts and facets for autocomplete.
- Maintain indexes automatically through PostgreSQL on catalog commits. Provide an Alembic migration and verify upgrade/downgrade on a real PostgreSQL instance.
- Debounce typing by 300 ms; filters and explicit submission act immediately. Reset pagination on query/filter changes, synchronize browser navigation, cancel obsolete HTTP requests, and show updating/error states.

## Acceptance

Synthetic real-PostgreSQL tests demonstrate typo tolerance, exact/name relevance, cross-field multi-token matching, filters, facets, stable pagination, and index-backed matching. UI tests verify typing, filters during pending typing, reset, back/forward, and request cancellation. Task lint, check, test, and API contract checks pass.
