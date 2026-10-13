# Implementation plan

1. Validate the current public API and booking routes against upstream source and live responses.
2. Add provider-local Pydantic models and an async adapter with shared retries, bounded grids, and conservative availability translation.
3. Seed and register ReserveCalifornia, ingest metadata, scope search joins by provider, and pass park context to booking links.
4. Verify synthetic HTTP and database regressions, migration upgrade/downgrade, and project quality gates. Update documentation and checklist.

## Constitution check

- Async HTTP and database operations use existing packages, Task workflows, and strict typing.
- The worker sees only CampsiteDTO; provider parsing stays isolated from the CLI.
- No dependency or schema changes are needed beyond seeding the provider.
- Fixtures are synthetic and tests cover externally observable behavior and provider isolation.

The subsequent [shared UseDirect implementation](../005-usedirect-providers/plan.md) extracts models and common scanning/ingestion into `providers.usedirect`, preserving California's ID and concrete-provider import path.

## API research

- The checked-in CLI points at a retired host. Current upstream source uses `https://california-rdr.prod.cali.rd12.recreation-management.tylerapp.com/rdr` and booking routes `/park/{place_id}/{facility_id}`: [upstream variation](https://raw.githubusercontent.com/juftin/camply/main/camply/providers/usedirect/variations.py).
- GET `fd/places`, `fd/facilities`, and `search/filters` responded successfully on 2026-10-12.
- Metadata maps PlaceId to recreation areas and FacilityId to campgrounds; grid dictionaries use composite keys, so campsite identity must come from UnitId.
