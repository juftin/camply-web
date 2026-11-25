# Test Data

- **Scenario** — A unique operation and provider-qualified key, public source, native campground ID, optional native area ID, and independently verified expected fields. Preserve ReserveAmerica campground IDs as opaque contract-qualified strings.
- **Fixture** — Sanitized request and response data for one scenario. Keep shape, pagination, entity attribution, and necessary status information. Use a compact archive fixture when the adapter reads an upstream archive.
- **Stored snapshot** — Expected catalog rows, campsite capabilities, or enrichment fields in test-owned SQLite. A failed refresh preserves the prior successful snapshot.
- **Refresh entry** — Scenario key, public source, capture inputs, fixture path, last successful verification date, and candidate review instructions.
