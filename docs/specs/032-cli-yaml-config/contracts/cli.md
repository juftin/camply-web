# CLI Contract for YAML Search Batches

## Invocation

```text
camply [--debug | --no-debug] campsites --yaml-config PATH
    [--debug | --no-debug] [--search-once [--json]]
```

File mode accepts `--yaml-config` alone for the file path. The file uses the checked-in Draft 2020-12 `docs/cli-yaml-config.schema.json`, with runtime checks described in the [data model](../data-model.md). Every search specifies a provider. Explicit provider, target, date, filter, interval, notification, and state-file flags conflict with file mode, including the root provider flag. In the absence of `--yaml-config`, the existing flag-based invocation remains available.

## Lifecycle and exit status

| Event                                            | Result                                                                                                                                                                          |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| File or invocation fails local validation        | Usage error, exit 2, diagnostic on stderr, and no stdout in JSON mode. No search starts and no state file is written.                                                           |
| Continuous mode                                  | Each search attempts a check immediately, then waits for its configured interval after each completed attempt. An upstream failure is attributed and retried in the next cycle. |
| All single-pass checks succeed                   | Exit 0 after all checks and notification attempts finish. Empty matches count as success.                                                                                       |
| Any single-pass check fails                      | Exit 1 after every search has attempted its check. Available results from successful searches are retained.                                                                     |
| User interrupts the batch                        | Cancel active and waiting searches, release owned clients, and follow the current CLI abort behavior.                                                                           |
| Notification delivery or state-file access fails | Emit an attributed warning and continue. The availability outcome and exit status still depend on the provider check.                                                           |

## Output

Terminal results and search-specific diagnostics identify the search name and canonical provider. Diagnostics use known field paths and safe messages. Provider responses, credentials, and raw rejected values are excluded.

For `--search-once --json`, stdout contains exactly one array, ordered as the input file. Progress and diagnostics go to stderr. Example with an empty successful search and a failed search:

```json
[
  {
    "name": "no-openings",
    "provider": "RecreationDotGov",
    "status": "ok",
    "stays": []
  },
  {
    "name": "coastal-trip",
    "provider": "ReserveCalifornia",
    "status": "error",
    "stays": []
  }
]
```

Each stay uses the existing keys `provider_id`, `provider_name`, `recreation_area_id`, `recreation_area_name`, `campground_id`, `campground_name`, `campsite_id`, `campsite_name`, `arrival`, `checkout`, `nights`, and `booking_url`. Arrival and checkout use ISO dates. Optional values retain the current serializers' representations.
