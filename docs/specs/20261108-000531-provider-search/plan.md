# Implementation plan

Existing logic audit: four API families cover 13 registered providers. UseDirect
has typed places/facilities; GoingToCamp has typed catalogs and overnight category
resolution; ReserveAmerica has validated state pagination and eligibility;
Recreation.gov has a public /api/search endpoint (live response inspected).
No existing provider discovery method is available independently of ingestion.

Add typed query/result DTOs and a shared validated BaseProvider entrypoint.
Each API family supplies database-free discovery through existing retry/pacing
clients. Reuse source eligibility rules and URL builders. ReserveAmerica uses
verified state search, fetching brand states for an unscoped query; this can be
slow and a state filter is recommended. No new endpoint assumptions there.
Recreation.gov paginates the public search endpoint with typed envelopes and
progress checks, applying optional state/parent restrictions locally.

Constitution review: async IO, Pydantic results, base-only dependencies, no server
or worker imports, no schema changes. Synthetic HTTP integration tests verify
normalization, filtering, pagination, errors, and database independence.

Validation: the initial invalid-limit test failed for all 13 providers before
implementation. Final search regressions exercise real HTTP clients with mock
transports, explicitly reject database-session access, and cover all registered
regional variations. A read-only live Recreation.gov query for Yosemite with a
CA filter and limit 3 successfully parsed and returned three native campground
IDs. Live Recreation.gov queries also passed in campground-only, recreation-area-only,
and combined modes with a CA filter. No live search was required for other
families; their established catalog
and state endpoints are exercised with synthetic responses.

Entity selection: add a shared result base with typed campground and recreation
area subclasses, a validated optional string-enum selector defaulting to None (both types), and
entity-scoped deduplication. UseDirect parks and GoingToCamp transaction
locations provide direct area-only discovery without facility requests.
Recreation.gov supports recarea and union entity filters (verified live in all
three modes). Move existing GoingToCamp state/country normalization into shared
provider utilities so recreation-area records without address codes normalize
full state names. Preserve the original import paths via explicit re-exports.
ReserveAmerica remains campground-only and returns early for area-only requests.
