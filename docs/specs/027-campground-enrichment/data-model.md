# Destination details data model

Add nullable portable JSON `details` columns to `campgrounds` and `recreation_areas` with a forward Alembic migration. Existing composite identities and descriptions remain intact. Ordinary catalog merges leave the new attribute unset, preserving earlier enrichment.

Each table also has an internal nullable `details_attempted_at` timestamp. An atomic one-hour attempt claim prevents concurrent duplicate work and lets failing batches yield to untouched destinations, without changing successful content or its provenance. This field is not exposed by the API. Null attempt timestamps sort first explicitly on SQLite and PostgreSQL.

Provider-layer Pydantic models in `camply.providers.details` validate snapshots and can be imported without server/worker extras:

- `DestinationPhoto`: `url`, optional `caption`, `credit`, `width`, `height`, `source_url`; `is_primary` defaults false.
- `DestinationLink`: `label`, `url`.
- `DestinationFact`: `label`, `value`.
- `DestinationDetails`: `source_url`, timezone-aware `fetched_at`; optional `description`, `directions`, `accessibility`, `fee_information`, `stay_limit`; arrays `photos`, `activities`, `amenities`, `links`, `hours`, `vehicle_limits` default empty.

Accept only public HTTP(S) URLs without user information or private/local address literals. Validate image origins at the adapter boundary; never fetch arbitrary provider-supplied URLs. Normalize/deduplicate photos by URL, order primary first then URL, and cap at 12. Optional dimensions are positive integers. Narrative HTML is sanitized for rendering by the existing frontend utility.

The complete snapshot is assigned as a new JSON value in a transaction scoped by provider, entity type, and ID. A failed source read preserves the old value and freshness. A successful complete snapshot replaces it, including clearing photos that are now absent. A partial provider response is not a complete snapshot. Seven-day freshness is measured from the successful timestamp, independently of catalog `updated_at`.

Refresh selection orders never-attempted records first, then oldest attempts and successful snapshots, and limits each provider invocation to 100 entities spanning both destination types. Avoid holding database transactions during network work. Recreation.gov reads archive members incrementally before applying snapshots and retains at most 12 photos per selected entity.

RIDB media and links currently identify destinations as `Asset`; resolve those IDs against both complete source catalogs, reject ambiguous matches, and enrich campgrounds only when the current facility classification remains `Campground`. Missing or changed source destinations retain their prior snapshot. Activities use `Campground`/`Facility`/`Rec Area` discriminators. All required members are parsed to completion before persistence.
