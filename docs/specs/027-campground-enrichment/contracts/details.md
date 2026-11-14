# Destination detail API contract

`GET /api/campground/{provider}/{id}` returns the existing campground fields plus optional `details: DestinationDetails | null` through a distinct `CampgroundDetail` schema. `GET /api/rec-area/{provider}/{id}` adds the same optional property. Existing errors, IDs, URLs, reservability rules, and authentication are unchanged.

`GET /api/rec-area/{provider}/{id}/campgrounds` retains the existing campground summary schema with no `details` property. Search and map APIs remain unchanged. Detail reads access cached database values only, without upstream traffic.

The snapshot schema and field semantics are defined in [the data model](../data-model.md). Timestamps serialize as ISO 8601, arrays as arrays even when empty, and absent optional narrative fields as null. Source links and credits are presented as supplied, without implying an image license.

Update OpenAPI-generated TypeScript declarations and the hand-maintained frontend detail response structs/API return types together. Older rows with no enrichment continue to render through `details = null`.

Provider refresh is an internal `BaseProvider.enrich_metadata()` extension with an unsupported-provider no-op. CLI metadata and shared worker catalog ingestion call it after catalog ingestion, with failure isolation. It is never called by search, detail routers, or availability scanners.
