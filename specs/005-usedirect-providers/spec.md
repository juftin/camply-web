# Shared UseDirect / Tyler providers

## User stories

- Campers discover and monitor additional supported UseDirect park systems through the existing application.
- Operators sync complete park/facility metadata independently of availability searches.
- Maintainers implement provider variations through a shared backend ABC rather than copying adapters.

## Requirements

- Extract ReserveCalifornia's async requests, grids, models, and transactional catalog ingestion into `UseDirectProvider(BaseProvider, ABC)`.
- Keep ReserveCalifornia's provider ID 2, import path, booking routes, and tested behavior.
- Concrete providers supply persistent identity, API and booking endpoints, state/country defaults, and booking-route variations.
- Verify catalog, filters, grid, and booking endpoints before enabling a provider; record TODOs with failure evidence for unavailable candidates.
- Add responding Florida, Virginia, Minnesota, Ohio, Arizona, Missouri, Fairfax County, Oregon Metro, and Northern Territory candidates after verification.
- Seed new identities through an immutable Alembic data migration, and reject rollback with dependent records.
- Isolate caches, requests, metadata retirement, and search rows by provider even when upstream IDs overlap.
- Preserve conservative availability translation; exclude explicitly non-electric classifications from electrical matches.
- Allow missing source location fields to use the concrete provider's defaults, including country AU for Northern Territory.
- Keep fixtures synthetic and add behavior regressions for all concrete providers and worker ingestion.
- Document manual and scheduled metadata sync and outstanding booking restrictions.

## Scope limits

Individual campsite persistence, distributed rate limiting, startup ingestion, provider minimum-stay enforcement, and residency-aware booking windows remain shared-system follow-ups. No CLI imports, new dependencies, or new application schemas are required.
