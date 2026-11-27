# UseDirect provider TODOs

## Legacy candidates no longer on UseDirect

Live verification on 2026-11-16 confirmed all 10 registered UseDirect deployments remain active, while both legacy 404 candidates have migrated off UseDirect/Tyler RDR to different reservation platforms (future support would require separate provider adapters rather than `UseDirectProvider`):

- [x] **Alabama State Parks:** Legacy `https://alabamardr.usedirect.com/alabamardr/rdr/fd/places` returns **HTTP 404**. The current portal at `https://reserve.alapark.com` runs on **Itinio**, not UseDirect/RDR.
- [x] **Maricopa County Parks:** Legacy `https://maricopardr.usedirect.com/maricopardr/rdr/fd/places` returns **HTTP 404**. The current portal at `https://www.exploremaricopacountyparks.org/` runs on a **Cedar** Next.js application, not UseDirect/RDR.

## Follow-ups for verified providers

- [ ] Verify facility deep links for Fairfax County, Oregon Metro, and Northern Territory. Current implementations open the verified booking application; they preserve the legacy CLI's search-page fallback rather than assume support for state-park hash routes.
- [ ] Improve electrical classification where groups omit hookups, notably Florida. Until an explicit upstream indication is verified, unknown hookups remain false rather than inferred.
- [ ] Apply provider booking restrictions in the shared worker, including minimum stays and Florida's residency-dependent advance window. The provider preserves per-night minimum stays but eligibility still uses only user filters.
- [ ] Implement shared request pacing and classification caching across polls and worker processes.
- [ ] Add individual campsite metadata persistence and an independent site-catalog ingestion path once the planned `campsites` schema exists.
- [ ] Bootstrap metadata on worker startup or provide an explicit initial-ingestion deployment step. Automatic refresh currently requires Celery Beat and runs daily at midnight UTC.

Other shared-worker findings are documented in [the California integration review](../20261013-133646-reserve-california/review.md).
