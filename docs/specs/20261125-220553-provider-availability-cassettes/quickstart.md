# Verification for Provider Availability Cassettes

Run these checks after implementing the feature. Start with the project's normal backend development setup and run commands from the repository root.

## Replay the suite

```sh
task backend:install
task backend:test -- tests/providers/test_availability_cassettes.py
```

After dependencies are installed, repeat with outbound network access disabled. Expect at least 52 positive cases for the initial 26 providers, plus the registry-coverage check. Include at least one case with a stay date before the verification day. Check that the backend test workflow discovers the suite without case-specific flags.

## Check failures

In temporary test edits, remove one cassette, change a campground or date input without re-recording, and change one expected site or night. Each change should fail for the named case. Confirm that the equipment assertions fail when a known incompatible site is included. Restore the edits after each check.

## Refresh one case

Follow the developer refresh guide to choose one exhausted or historical scenario and find a currently open stay using the same equipment category and length if supported. For a year rollover, confirm that the new dates are in season and within the booking window. Use the documented recording command to stage only the selected case and review its fixture diff. Verify the candidate offline, publish the updated inputs and cassette together, and replay another scenario for the same provider. Check that a failed refresh leaves the original cassette usable.

## Verified Jumbo Rocks rollover

The maintenance check used January 1, 2027 as its verification date. On that controlled calendar, the original RV stay from December 7 to December 9, 2026 had expired and the replacement from January 11 to January 12, 2027 was upcoming. Live capture ran on November 25, 2026 against the January inventory.

1. In a temporary copy of the case inputs, select the original December dates and replay its original fixture with outbound traffic blocked. The suite uses the case's arrival as its search clock so historical recordings remain useful.
2. Restore the January inputs and stage a fresh candidate for site 089 accepting a 30-foot RV. Use the single-case recording and candidate replay commands in the [refresh guide](../../development/PROVIDER_CASSETTES.md).
3. Replay the candidate and the December tent case with outbound traffic blocked. Both passed. The saved original RV fixture and the tent fixture matched their pre-refresh checksums.
