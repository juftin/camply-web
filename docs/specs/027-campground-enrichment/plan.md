# Enrichment implementation proposal

**Date**: 2026-11-14 · **Status**: Implementation design · [Specification](spec.md) · [UI/UX](ui-ux.md) · [Data model](data-model.md) · [API contract](contracts/details.md) · [Validation](quickstart.md) · [Evidence](research.md) · [Provider matrix](provider-matrix.md) · [Backlog](tasks.md)

## Recommendation

Start with Recreation.gov. Extend the export ingestion we already run to retain photos and practical destination details. Cache them on existing destination records, expose them through detail endpoints, and display galleries and information sections on the two existing page types.

Next, add UseDirect park images and practical information across all ten verified deployments, plus facility images where they exist. ReserveAmerica now has verified facility details and original-photo galleries from multiple contracts. Washington's official operator site provides a park-gallery fallback; native GoingToCamp media remains unverified.

## Technical context

Use the existing Python >=3.11 provider package, Pydantic, SQLAlchemy/Alembic, FastAPI, generated TypeScript client, and React pages. Support SQLite standalone and PostgreSQL distributed installations. The Recreation.gov export path needs no new service or API credentials.

Enrichment belongs in `camply.providers` and `camply.db`, independent of optional server/Celery bootstraps. Reuse metadata workflows; leave availability polling and upstream search contracts unchanged.

## Shared representation and persistence

Propose one nullable `details` column on each of `Campground` and `RecreationArea`, using SQLAlchemy's portable JSON type. Retain existing descriptions. No photo queries or indexing requirements currently justify a separate media table.

Validate both through a shared `DestinationDetails` DTO:

| Field                                                          | Proposed content                                                                                      |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `photos`                                                       | At most 12 ordered objects: source ID, URL, title/caption, credit, dimensions, primary flag           |
| `directions`, `accessibility`, `fee_information`, `stay_limit` | Optional provider text, preserving meaning                                                            |
| `activities`, `links`                                          | Activity labels and labeled official website/map/information links                                    |
| `hours`, `vehicle_limits`                                      | Verified UseDirect park fields; preserve labels and units, or source text where units are unspecified |
| `source_url`, `fetched_at`                                     | Provenance and the successful refresh time                                                            |

Order primary images first, then stable source ID/URL; deduplicate before the cap. Preserve distinct titles, descriptions, and credits where supplied. Replace validated snapshots rather than relying on nested JSON mutation tracking. Add a forward migration and verify both databases; old rows remain valid with null details.

## First delivery: Recreation.gov

1. Retain directions, accessibility, fees, and stay limits alongside existing area/facility descriptions.
2. Read `Media_API_v1.json` from the same cached ZIP. Join by provider, exact entity discriminator, and entity ID. Verify destination discriminator values first; exclude campsite/video/embed records and orphaned media.
3. Read links and entity activities, joining the activities catalog when needed for labels.
4. Persist bounded destination snapshots in batches. Explicitly test that ordinary catalog merges preserve enrichment they do not update.

The media member is approximately 137 MB uncompressed. Measure peak memory/runtime before choosing a parser. Use incremental parsing if complete deserialization exceeds the existing ingestion resource envelope; retain at most 12 selected images per entity while accumulating results. Do not assume adding another full in-memory catalog is harmless.

Reuse the existing cached full archive. Range requests were a research aid, not the proposed production mechanism: size metadata differed between probes and one range request failed. Avoid another full download or mandatory RIDB API key.

Validate complete members before replacing their results; use staging if necessary for bounded processing. A failed/malformed/missing required member preserves previous enrichment and freshness. A complete successful snapshot can clear images absent from that snapshot. Existing catalog imports commit in stages; this plan does not assume whole-provider atomicity or require an unrelated catalog refactor.

## API and interface

- Add optional details to the single-campground and single-area responses; regenerate types with `task api:generate`.
- Keep galleries out of search, maps, and area-child lists. Child lists currently reuse the campground model; introduce an explicit summary representation if necessary.
- Read cached data only. Show a responsive gallery, captions/credits, source and freshness, plus populated practical sections. Lazy-load images with dimensions and handle failures gracefully.
- Reuse `CollapsibleDescription` and the existing HTML sanitizer for narrative content; verify new URL/image contexts separately. Keep park-level information on its area or label parent information explicitly.

## Subsequent providers, informed by expanded research

**UseDirect**: Fetch `fd/placeinfo/additional-place-info/{PlaceId}` once per park through the paced request helper. The route worked on all ten configured deployments. Store supported fields on the recreation area, treating zero/placeholder limits as unknown and respecting the upstream display flag. Preserve free text where hours fields contain other information.

Use the verified public booking-root image paths `images/{enterprise}/ParkImages/Place/{PlaceId}.jpg` and optional `Facility/{FacilityId}.jpg`; validate HTTP status, MIME type, and content before retaining them. Park images loaded across all ten deployments; facility images were verified for California, Ohio, Missouri, Fairfax, and Northern Territory. Missing images are normal and do not invalidate practical information. Keep park images on recreation areas or in explicitly labeled parent information. No gallery-enumeration endpoint or static-asset photographer credits were established.

Do not blindly use `search/place` image fields: observed values included placeholder/test hosts and generic California banners. `SelectedPlace.Description` supplied richer text in nine of ten deployment samples, but fetching it requires a dated search that also computes availability. Treat this as a separately measured enrichment operation; never copy its availability into destination metadata or couple it to scans/page loads. Do not add it to ordinary metadata sync without evaluating cost.

**ReserveAmerica**: Fetch `facilities/{contract}/{facility}?detailsOnly=false` through the existing anonymous-session adapter. Three live responses verified narratives, directions, amenities with distance fields, seasons, fees, and gallery lists. Normalize `originalPhotos` paths against their verified source origin, encode literal path characters without double-encoding existing escapes, and preserve captions. `facilityPhotos` is an alternate rendition list, not additional unique photos. Retain only one representation per image and distinguish valid empty galleries from request failures. Keep media source origins separate from public booking links. No parent recreation areas are created.

**GoingToCamp / Washington**: Native access remains 403. A separate official-site adapter could use park pages such as Cape Disappointment: its gallery has 13 images and its booking link supplies the native `resourceLocationId`. Parse only the destination gallery, excluding recommendation cards/icons. Preserve park scope, official source URLs, and alt text; do not relabel park photos as campground-specific. Other deployments and a bulk feed remain unverified. Re-test native metadata/media when access permits, preserving signed deployment IDs and locale selection.

## Validation and delivery gates

1. Add failing synthetic fixtures for media associations/collisions, primary ordering, duplicates/cap, missing fields, URL/HTML handling, complete-empty snapshots, and failed/partial imports.
2. Verify migrations on isolated SQLite/PostgreSQL databases, idempotency, ordinary-merge preservation, and successful freshness updates.
3. Test detail-only payloads, missing/broken media, attribution, keyboard navigation, mobile/themes, and zero enrichment calls from availability or detail reads.
   Include UseDirect placeholder/test-host URLs and generic banners, large/missing static images, ReserveAmerica alternate-rendition deduplication and escaped paths, distance-qualified amenities, and Washington gallery-versus-recommendation separation.
4. Run `task fix`, `task lint`, `task check`, `task test`, and `task docs:check` before a feature PR; inspect visual baselines and update the global checklist. Record actual media coverage and ingestion memory/runtime.

## Constitution check

The design preserves availability reliability, requires typed DTOs/generated clients, uses Task workflows and existing deployment services, keeps provider/database dependency boundaries, and requires synthetic integration plus migration/API/UI verification. No governance exception is proposed. Runtime compliance remains to be established during implementation.

## Execution decisions

The user has authorized implementation. Use `ijson` to stream ZIP JSON records, retaining bounded selected-destination photos and fully validating members before persistence. Add a shared provider-layer DTO/persistence refresh helper with seven-day freshness and a maximum 100 oldest stale entities per provider invocation. CLI and worker entry points both currently call `populate_database()` directly; invoke `enrich_metadata()` after that call in both, isolating enrichment failures from successful catalog ingestion. Unsupported providers use a no-op. This preserves existing catalog-only provider contracts and avoids surprising availability requests.

Implement the shared data and API foundations, Recreation.gov export ingestion, UseDirect static photos/practical fields, ReserveAmerica original-photo details, and both frontend pages. Washington scraping/native media and dated UseDirect narrative searches are explicitly deferred. The detailed UI, schema, contracts, and validation artifacts above replace any earlier open design alternatives. Source licensing remains provider attribution without mirroring or license claims; no blanket reuse assertion is made.
