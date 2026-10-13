# UseDirect provider TODOs

## Providers awaiting working endpoints

These candidates are intentionally absent from the provider registry and seed migration. Checks on 2026-10-12 used the deployed paths from the legacy CLI and current upstream UseDirect variations.

- [ ] **Alabama State Parks:** `GET https://alabamardr.usedirect.com/alabamardr/rdr/fd/places` returned **HTTP 404**. Discover the current catalog/grid host from the official booking application, verify parks/facilities/filters/grids and booking routes, then add an identity, concrete provider, migration, and synthetic regressions.
- [ ] **Maricopa County Parks:** `GET https://maricopardr.usedirect.com/maricopardr/rdr/fd/places` returned **HTTP 404**. Inspect the current county reservation application to determine whether it still uses RDR; verify its catalog/grid endpoints before selecting UseDirectProvider or implementing a separate adapter. Then seed and test the supported integration.

Endpoint failure does not establish that a park system is unavailable; its current reservation system may have changed host or backend.

## Follow-ups for verified providers

- [ ] Verify facility deep links for Fairfax County, Oregon Metro, and Northern Territory. Current implementations open the verified booking application; they preserve the legacy CLI's search-page fallback rather than assume support for state-park hash routes.
- [ ] Improve electrical classification where groups omit hookups, notably Florida. Until an explicit upstream indication is verified, unknown hookups remain false rather than inferred.
- [ ] Apply provider booking restrictions in the shared worker, including minimum stays and Florida's residency-dependent advance window. The provider preserves per-night minimum stays but eligibility still uses only user filters.
- [ ] Implement shared request pacing and classification caching across polls and worker processes.
- [ ] Add individual campsite metadata persistence and an independent site-catalog ingestion path once the planned `campsites` schema exists.
- [ ] Bootstrap metadata on worker startup or provide an explicit initial-ingestion deployment step. Automatic refresh currently requires Celery Beat and runs daily at midnight UTC.

Other shared-worker findings are documented in [the California integration review](../004-reserve-california/review.md).
