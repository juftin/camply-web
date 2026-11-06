# GoingToCamp provider & Washington State Parks

## User stories

- Campers discover, map, and monitor Washington State Parks campgrounds and overnight lodging (`https://washington.goingtocamp.com`) through the existing application.
- Operators sync complete park and campground metadata independently of availability scans via CLI or scheduled background ingestion.
- Maintainers add future GoingToCamp park systems (Parks Canada, BC Parks, Wisconsin, Maryland, Michigan, etc.) as thin deployment variations on a shared async ABC rather than duplicating adapters or hardcoding fake recreation-area IDs.

## Requirements

- Implement a shared async base `GoingToCampProvider(BaseProvider, ABC)` in `camply.providers.going_to_camp.provider` with source Pydantic v2 models in `camply.providers.going_to_camp.models`.
- Model each GoingToCamp website as a concrete provider variation with its own persistent `Provider` identity because upstream `transactionLocationId` and `resourceLocationId` sequences independently start at `-2147483648` across deployments and would otherwise collide on `(id, provider_id)` primary keys.
- Register `WashingtonStateParksProvider` in `camply.providers.going_to_camp.variations` under permanent provider ID `12` (`Washington State Parks`, `https://washington.goingtocamp.com`).
- Seed provider ID `12` through an immutable Alembic migration revising the current head, and block downgrade when dependent rows exist in `campgrounds`, `recreation_areas`, `unique_targets`, or `search`.
- Ingest complete park (`GET /api/transactionlocation`) and campground (`GET /api/resourceLocation`) catalogs independently of availability scans, resolving active overnight camping/lodging categories dynamically from `GET /api/bookingcategories` and `GET /api/resourcecategory` instead of upstream's hardcoded negative category IDs.
- Retain day-use, marina/moorage, disabled, and unmapped facilities in `campgrounds` with `reservable=False` while excluding them from searchable `Campground` entries in `search`, and retire disappeared upstream records (`enabled=False`, `reservable=False`) without deleting historical scan references.
- Scan campsite availability asynchronously in bounded date windows (`_GRID_DAYS = 60`) using bulk facility resource metadata (`GET /api/resourcelocation/resources`) and map daily availability (`GET /api/availability/map?getDailyAvailability=true&isReserving=true`), traversing child loop maps via `mapLinkAvailabilities` only when potentially available (`0` or `7`) and treating only status `0` (`Available`) as bookable online.
- Treat `end_date` as check-out (exclusive), clip padded or check-out daily entries to `[start_date, end_date)`, merge multi-window results per `resourceId`, and raise `ValueError` when an unknown campground ID is requested so cached worker scan results are preserved.
- Decode equipment across all `equipmentCategories` from `GET /api/equipment` and filterable multi-enum/scalar site attributes from `GET /api/attribute/filterable`, conservatively classifying `CampsiteType` (`CABIN`, `RV`, `TENT`, `OTHER`), `is_electric` (excluding explicit non-electric values), and `is_accessible` (restricting matches to accessibility attributes rather than adjacent amenities).
- Generate verified GoingToCamp reservation deep links (`/create-booking/results?transactionLocationId=...` and `/create-booking/results?resourceLocationId=...`) for parks and campgrounds.
- Keep all committed fixtures and VCR cassettes synthetic, with behavior regressions covering HTTP replay, map traversal, category/equipment/attribute decoding, metadata atomicity, provider isolation, CLI help/invocation, packaging, and migration round trips.

## Scope limits

Remaining GoingToCamp deployments from the legacy CLI are documented in [provider TODOs](TODO.md) for per-deployment endpoint verification and rollout. Individual campsite catalog persistence, cross-worker distributed rate limiting, and shared-worker minimum/maximum stay enforcement remain platform-wide follow-ups. No legacy CLI code is imported and no new third-party dependencies or database schema changes are introduced.
