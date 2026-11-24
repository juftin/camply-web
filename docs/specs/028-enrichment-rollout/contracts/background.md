# Background contract

- `camply.catalog.enrich_all_providers`: periodic fan-out, one provider-details job per registered provider; no catalog imports.
- `camply.catalog.enrich_provider_details`: at most 100 due destinations, then enqueue a short-delayed continuation only after successful work if due destinations remain. Unknown/fresh/unsupported providers stop. Periodic discovery recovers interruptions and whole-batch failures.
- Standalone local consumer uses the same enrichment-only engine and repeats pending providers after yielding; idle/failure-only passes wait the configured heartbeat.
- Existing detail API, page reads, availability scans, catalog imports, retry cooldowns, and cache schema retain their contracts.
