# Validation Log: Independent CLI Rebuild

## Baseline Test Results (2026-10-12)

- Command: `uv run -- pytest packages/providers/tests packages/worker/tests -v`
- Execution time: 13.20s
- Result: **159 passed, 5 skipped** (Valkey integration tests requiring live service skipped as expected).
- Status: Baseline established cleanly before extraction.

## Step 0.2: Contract Characterization Tests

Contract regressions to add:

1. Provider checkout date exclusion: nights searched are `[arrival, departure)` and checkout day availability is excluded from stay runs.
2. Provider status handling: Unrecognized availability statuses are treated as incomplete/invalid, not available.
3. Multi-month window querying: Date runs are sorted, unique, and bounded within the searched nights.
