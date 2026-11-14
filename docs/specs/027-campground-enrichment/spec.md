# Campground and recreation-area enrichment

**Created**: 2026-11-13 · **Updated**: 2026-11-14 · **Status**: Implemented and locally verified. See [validation and convergence](validation.md) for results and external release checks.

## Clarifications and scope

### Session 2026-11-14

The user authorized the complete planning and implementation workflow. No additional product question is required: the following defaults resolve the remaining design choices and are recorded as implementation decisions, not user answers.

- Deliver cached destination enrichment for Recreation.gov, all ten UseDirect deployments, and ReserveAmerica. Preserve unsupported providers unchanged. Native GoingToCamp media, Washington HTML scraping, and dated UseDirect narrative searches are deferred because they lack verified metadata-only contracts.
- Use the existing destination pages, showing own-entity photos and practical details. A keyboard-accessible dialog displays larger photos; missing content omits the corresponding section.
- Refresh independently of availability and page reads through the CLI and shared worker metadata workflows. Use a seven-day freshness interval and an oldest-first batch of at most 100 stale entities per provider invocation; subsequent invocations continue the backlog. Recreation.gov uses its existing cached export.
- A failed per-entity refresh keeps its previous successful snapshot. A verified missing image (404/410) is absence; authentication, transport, malformed payloads, and server errors are failures. Source fields that are unsupported do not erase supported data.
- An internal attempt timestamp provides an atomic one-hour claim cooldown, so failures yield to remaining destinations and concurrent refreshes do not duplicate work. The successful refresh timestamp is unchanged by failures. Missing/reclassified Recreation.gov destinations retain their last successful snapshot.
- Remote photos remain on verified upstream hosts; retain supplied credits and source links. No mirroring or automated license claims are introduced.

## User scenarios and acceptance criteria

### See photos and practical details (P1)

A visitor opens a campground or recreation area and sees available upstream photos, directions, accessibility information, activities, and useful links alongside its existing description.

- Photos retain available captions, credits, and source links.
- Campground photos belong to that campground. Recreation-area and campsite photos are not silently presented as campground photos.
- Missing details or broken images leave descriptions, maps, booking links, and monitoring actions usable.

**Independent test**: Import a synthetic Recreation.gov export and verify the correct details on both destination page types, including missing-photo cases.

### Keep enrichment independent of monitoring (P1)

An operator refreshes destination information without making availability scans or ordinary page reads depend on upstream enrichment services.

- Repeated imports do not duplicate photos or change destination identities.
- Failed or incomplete enrichment preserves the last successful data and refresh timestamp.
- A complete successful response containing no photos clears earlier photos. An unsupported or omitted field is not treated as an explicit deletion.
- Detail reads and availability checks issue zero enrichment requests.

**Independent test**: Repeat metadata imports, simulate a failed enrichment, and verify cached detail reads and availability scans still work.

### Extend coverage where verified (P2)

Visitors see additional information from other booking systems where those systems expose usable metadata.

- UseDirect park hours, official website, and vehicle limits appear on the correct recreation area when supplied.
- Park-level limits do not become campsite eligibility rules.
- ReserveAmerica facilities remain campgrounds without fabricated parent recreation areas.
- ReserveAmerica's original/alternate photo renditions appear once per image, while a valid empty gallery leaves practical details available.
- Unsupported provider fields remain absent; photos and descriptions are never invented.

**Independent test**: Replay synthetic UseDirect park information and verify its association and display labels.

## Requirements

- **FR-001**: Preserve provider-scoped IDs, hierarchy, names, booking links, and existing description fields.
- **FR-002**: Retain verified photo URLs, captions, credits, dimensions, and primary-image preferences, with exact provider/entity associations.
- **FR-003**: Support optional directions, accessibility text, fee information, stay limits, activities, and official links where verified upstream.
- **FR-004**: Record provenance and last successful enrichment time; distinguish unsupported, empty, and failed responses.
- **FR-005**: Persist cached details and refresh through metadata workflows independently of availability and rendering.
- **FR-006**: Sanitize narrative HTML using the existing rendering path, validate public HTTP(S) links, and handle unavailable images gracefully.
- **FR-007**: Limit photos deterministically and keep full galleries out of search, map, and list responses.
- **FR-008**: Support SQLite and PostgreSQL and retain compatibility for existing destination responses.
- **FR-009**: Begin with Recreation.gov's existing export; enable other enrichment adapters only after their response shapes and associations are verified.
- **FR-010**: Exclude placeholder/test-host image links and generic banners; preserve the scope of park-level media and distinguish nearby amenities from on-site amenities when upstream distance fields identify them.
- **FR-011**: Use the layouts, dialog interactions, loading/empty/failure states, and keyboard requirements in [the UI/UX plan](ui-ux.md).
- **FR-012**: Bound refresh work to 100 stale entities per provider invocation, with seven-day freshness and oldest-first continuation; never refresh through detail reads or availability scans.

## Key entities

- **Destination details**: Optional structured information attached to an existing campground or recreation area, including source and refresh time.
- **Photo**: An upstream image associated with a provider, entity type, and entity ID, with optional source ID, caption, credit, and dimensions.

## Edge cases

Identical IDs across providers/types; orphaned and campsite media; duplicate URLs; missing credits/dimensions; videos and embeds; unsafe links/HTML; truncated exports; failed requests; successful empty snapshots; and expired image URLs.

## Success criteria

- Both destination page types display their supplied images and practical details in acceptance fixtures.
- All ID-collision fixtures retain the correct associations, including exclusion of campsite media.
- Repeated imports produce stable galleries; complete-empty snapshots clear them and failed snapshots preserve them.
- All missing/failed-enrichment scenarios preserve discovery and monitoring.
- Users can identify the source and last successful refresh of displayed enrichment.

## Assumptions

Upstream coverage varies; no universal photo percentage is promised. Initial images reference upstream URLs after confirming applicable source usage requirements. Image mirroring, uploads, reviews, commercial photo services, generated descriptions, and booking/notification changes are outside this proposal.
