# Upstream enrichment research

**Checked**: 2026-11-13. Public read-only requests only. No operator database, credentials, or secret files were used. No raw provider responses or upstream JavaScript are committed.

**Expanded follow-up**: The [provider matrix](provider-matrix.md) verifies images and practical information across all ten UseDirect deployments, real ReserveAmerica galleries, and Washington's official operator-site gallery. It records exact sources and supersedes the narrower confidence limits from the initial pass below.

## Implementation verification, 2026-11-14

Downloaded the public ZIP to temporary storage and streamed complete source members. The current facility and recreation-area ID sets are disjoint: 15,438 facilities (5,808 classified as campgrounds) and 3,651 recreation areas. Image media use `EntityType="Asset"`, not `Facility`/`Rec Area`: 46,441 Asset image records cover 9,724 distinct IDs. Those IDs match 4,694 campground IDs and 2,090 recreation-area IDs, with 906 matching neither source catalog. Campsite and tour media were counted separately and are excluded. These figures describe source associations, not validated-image or enabled-application coverage.

Links also use `Asset`; activities use several discriminators including `Campground`, `Facility`, and `Rec Area`. The implementation resolves Asset IDs using both catalogs, skips ambiguous matches, and preserves prior snapshots for missing/reclassified destinations.

A complete media census took 1.79 seconds with approximately 29 MiB peak process RSS. The implemented full enrichment parser, including catalog/link/activity validation for a selected 100-destination batch, took 8.01 seconds with approximately 85 MiB peak process RSS, retained 292 photos across 62 destinations, and never exceeded 12 photos per destination. Measurements are from this environment and this export; the process includes normal Python/provider imports. `ijson` provides incremental parsing rather than deserializing the 137 MB media member. No public payloads or images were added to fixtures.

The final design adds an independent attempt timestamp and one-hour claim cooldown so failing records do not monopolize bounded batches. Successful content remains fresh for seven days. This closes a starvation issue found during convergence review.

## Findings

| Provider family                 | Already retained                                                    | Additional information                                                                                   | Evidence and confidence                                                                                                                    |
| ------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Recreation.gov                  | Descriptions, locations, hierarchy, reservability                   | Photos with captions/credits/dimensions; directions, accessibility, fees, stay limits, links, activities | Export members and sampled schemas verified live. Strongest first delivery.                                                                |
| UseDirect, including California | Park/facility descriptions and location                             | Park photos, some facility photos, richer narratives, hours, official websites, vehicle-limit fields     | All ten deployments sampled live; five had a verified facility image. API image fields can contain placeholders. See the expanded matrix.  |
| GoingToCamp / Washington        | Localized park/facility descriptions and coordinates                | Official operator-site gallery and practical park information                                            | Native catalogs remain 403; Cape Disappointment's official site supplied 13 gallery images and an explicit booking-ID link.                |
| ReserveAmerica                  | Facility descriptions and coordinates; no separate recreation areas | Original-photo galleries, amenities, narratives, directions, seasons, fees                               | Three facility responses verified live; photo counts 4, 6, and 0. Original JPEGs loaded for two destinations. Access remains intermittent. |

## Existing application behavior

- `src/camply/db/models/{campgrounds,recreation_area}.py` already have nullable description columns. Neither has photos or structured destination details.
- All four provider families map descriptions during ingestion. Their narrow models discard other upstream fields by default.
- Destination detail responses already expose descriptions. Both frontend pages render them through `CollapsibleDescription`; enrichment needs persistence/API/UI work, not merely another provider request.
- Recreation.gov already downloads `RIDBFullExport_V1_JSON.zip`, caches it for 12 hours, and reads recreation areas/facilities plus addresses. It ignores media, links, and activities.
- Search and map discovery use lightweight records; galleries should not add upstream calls or large payloads to these paths.

## Recreation.gov: verified export path

Sources: [RIDB download page](https://ridb.recreation.gov/download), [official API documentation](https://ridb.recreation.gov/docs), and the [export already configured in camply](https://ridb.recreation.gov/downloads/RIDBFullExport_V1_JSON.zip).

Small HTTP range requests inspected the ZIP directory and selected member prefixes without downloading the entire archive, approximately 574 MB at inspection:

| Member                         | Relevant sampled fields                                                                                                                                                                          |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Media_API_v1.json`            | `EntityMediaID`, `EntityID`, `EntityType`, `MediaType`, `Title`, `Subtitle`, `Description`, `URL`, `Credits`, `Width`, `Height`, `IsPrimary`, `IsPreview`, `IsGallery`                           |
| `Facilities_API_v1.json`       | Description plus `FacilityDirections`, `FacilityUseFeeDescription`, `FacilityMapURL`, `FacilityReservationURL`, `FacilityAdaAccess`, `FacilityAccessibilityText`, `StayLimit`, `LastUpdatedDate` |
| `RecAreas_API_v1.json`         | Description plus `RecAreaDirections`, `RecAreaFeeDescription`, `RecAreaMapURL`, `RecAreaReservationURL`, `RecAreaAccessibilityText`, `StayLimit`, `LastUpdatedDate`                              |
| `Links_API_v1.json`            | `EntityLinkID`, `EntityID`, `EntityType`, `LinkType`, `Title`, `Description`, `URL`                                                                                                              |
| `EntityActivities_API_v1.json` | `EntityID`, `EntityType`, `ActivityID`, `ActivityDescription`, `ActivityFeeDescription`                                                                                                          |
| `Activities_API_v1.json`       | Member existence verified; record schema not inspected                                                                                                                                           |

The media member was approximately 137 MB, stored without ZIP compression in the observed archive. The first decoded image belonged to a **campsite**, confirming that joining image IDs directly to campgrounds would be wrong. It contained a Recreation.gov CDN URL, dimensions, descriptive fields, and gallery/primary flags.

Member/schema verification does **not** establish destination photo coverage, exact facility/recreation-area discriminator values, or whether representative image URLs load. Those require a content audit before implementation. The official docs describe media associated with recreation areas, facilities, and campsites, but documentation alone is not a coverage measurement.

Archive size metadata differed between probes, and a later range request returned HTTP 416. Regeneration or inconsistent cached responses could explain this; the cause was not established. Production ingestion should reuse the existing full-download/cache path, with no hardcoded offsets or sizes.

### Optional web detail API

[Upper Pines campground JSON](https://www.recreation.gov/api/camps/campgrounds/232447) returned HTTP 200 with a `campground` wrapper. The sample includes `facility_description_map` with overview/facilities/natural-features/recreation/nearby-attractions sections, plus directions, accessibility, fee/cancellation text, amenities, activities, notices, rules, links, and timezone fields. Key presence does not guarantee populated values everywhere.

A guessed `/api/camps/campgrounds/232447/media` route returned HTTP 404 and must not be treated as supported. RIDB's documented media endpoints are a separate API requiring key provisioning; the export avoids that dependency.

**Decision**: Retain more of the existing export first. Consider the web detail API later if sectioned descriptions or facility amenities justify extra requests. It is an undocumented frontend API, not a promised public contract.

## UseDirect: initial California park-information probe

The current [California application](https://www.reservecalifornia.com) supplied these request shapes in shipped JavaScript. Paths are relative to the configured [California RDR API](https://california-rdr.prod.cali.rd12.recreation-management.tylerapp.com/rdr/):

| Request                                    | Observation                                                                                                                            |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| `GET fd/places`                            | HTTP 200, 299 records. Sample description repeats the place name; keys contain no photo collection.                                    |
| `GET fd/facilities`                        | HTTP 200, 515 records. Sample facility 327 belongs to place 2 and has a short name-like description; keys contain no photo collection. |
| `GET fd/facilities/327`                    | HTTP 200; mostly operational metadata, without a photo collection in the sampled response.                                             |
| `GET fd/placeinfo/additional-place-info/2` | HTTP 200; website, park/office hours, trailer and camper/motorhome length fields, and a display flag.                                  |

These are raw catalog counts, not counts of enabled overnight campgrounds. Sample park-information keys include `ParkHeadquartersHours`, `DayUseParkHours`, `BackCountyTrailCampOfficeHours`, `NatureMuseum`, `TrailerMaxLength`, `CamperMotorHomeMaxLength`, and `DisplayMaxTrailerLengthOnWeb`. Confirm nonempty values and units before presentation.

The initial probe found an image base URL and map/icon assets but did not establish photo support. The [expanded survey](provider-matrix.md#park-and-facility-images) subsequently verified the frontend's destination-image paths across all ten deployments.

**Decision**: Enrich recreation areas from the additional-information route and verified public park-image paths. Validate each image and keep broader gallery coverage explicit; official-site extraction remains a separate source integration.

## Other families: initial access limits and follow-up

For Washington, `https://washington.goingtocamp.com`, `/api/transactionlocation`, and `/api/resourceLocation` returned HTTP 403. Existing models expose localized descriptions and accept `websiteUrl`/`website`, but no current media payload was verified. Inspect actual gallery requests from an accessible environment before designing an adapter.

For ReserveAmerica, [prior validation](../024-reserve-america/validation.md) recorded a successful anonymous facility-details request on 2026-11-07. The initial research pass encountered a bootstrap 403; expanded research subsequently obtained three successful facility responses and verified two original-photo URLs. The [matrix](provider-matrix.md#reserveamerica-verified-multi-photo-galleries) records fields, sample coverage, and remaining intermittent access failures.

**Decision**: ReserveAmerica can proceed to enrichment design using the verified details/gallery fields. Washington has an official-site fallback, while native GoingToCamp media remains unverified. Preserve signed deployment IDs and ReserveAmerica contract-scoped IDs; do not fabricate parent areas.

## Alternatives and remaining checks

- **Existing exports**: preferred; no new service or request-per-destination cost for Recreation.gov.
- **Fetch rich details for every destination immediately**: defer until access/schema stability and the extra refresh cost are justified.
- **Scrape official park pages**: possible later, but adds source-specific parsers and reliable entity matching. Name-only matching is insufficient.
- **Commercial photo services, uploads, generated imagery**: outside scope; upstream sources offer a useful starting point.

Before displaying photos, preserve available credits/source links, inspect source usage requirements, and verify representative image loading in the deployed browser. Finding a URL does not establish permission to mirror it; this research makes no license conclusion.

The implementation census and benchmark above resolve the initial Recreation.gov association and parsing-resource questions. Broader operational image-availability rates and destination coverage beyond these samples remain ongoing observations, not universal guarantees. See the [backlog](tasks.md) and [expanded provider matrix](provider-matrix.md).
