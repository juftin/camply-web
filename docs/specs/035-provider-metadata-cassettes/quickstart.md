# Verification for Provider Metadata Cassettes

After implementation, run the metadata suite with outbound networking blocked.

```sh
task backend:install
task backend:test -- tests/providers/test_metadata_discovery_cassettes.py tests/providers/test_metadata_enrichment_cassettes.py tests/providers/test_metadata_catalog_cassettes.py
```

Expect one passing discovery and catalog case per family and enrichment coverage for the three supported families. Verify that missing or mismatched recordings fail and an incomplete refresh preserves existing stored records.

Follow the provider cassette guide to stage, review, and replay one replacement. Compare companion fixture checksums before and after the refresh.

## Verified refresh

A new Recreation.gov discovery candidate for Jumbo Rocks and Joshua Tree was recorded on November 25, 2026 with the metadata recording controls. It replayed with outbound connections blocked. All companion fixture checksums matched their pre-refresh values. The case inputs and commands are in the [provider cassette guide](../../development/PROVIDER_CASSETTES.md#metadata-recordings).

A staged Recreation.gov RIDB archive passed both enrichment and catalog replay offline. A second candidate with `RecAreaAddresses_API_v1.json` removed passed enrichment and failed catalog sync. The shared archive and the listing cassette retained their original checksums.
