# Interface Contracts: CLI Full-Stack Parity

**Feature**: `031-cli-fullstack-parity`
**Date**: 2026-11-16

## 1. CLI Command Tree (`src/camply/cli/`)

```text
camply [--provider PROVIDER] [--debug | --no-debug] [--help] [--version]
├── providers [--debug | --no-debug] [--json]
├── recreation-areas [--provider PROVIDER] [--debug | --no-debug]
│                    [--search TEXT] [--state CODE] [--limit N] [--json]
├── campgrounds [--provider PROVIDER] [--debug | --no-debug]
│               [--search TEXT] [--state CODE]
│               [--rec-area ID]... [--campground ID]...
│               [--limit N] [--json]
├── campsites [--provider PROVIDER] [--debug | --no-debug]
│             [--rec-area ID]... [--campground ID]... [--campsite ID_OR_NAME]...
│             --start-date YYYY-MM-DD ... --end-date YYYY-MM-DD ...
│             [--day DAY]... [--weekends] [--nights N]
│             [--campsite-type TYPE]... [--electric] [--accessible] [--rv-length FEET]
│             [--notifications CHANNEL]... [--state-file PATH]
│             [--search-once] [--interval SECONDS] [--json]
├── test-notifications [--debug | --no-debug]
│                      --notifications CHANNEL ...
├── serve                       (unchanged)
│   ├── frontend
│   ├── backend
│   ├── worker
│   ├── beat
│   └── healthcheck
└── db                          (info, migrate, delete unchanged)
    ├── info
    ├── migrate
    ├── delete
    └── metadata [--provider-id ID_OR_NAME_OR_ALL] [--provider NAME_OR_ALL]
```

---

## 2. Option & Validation Contracts

### `camply campsites` New Options

| Option            | Type / Choices                                               | Default | Contract & Validation                                                                                                                |
| ----------------- | ------------------------------------------------------------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `--campsite`      | Repeatable string                                            | `()`    | Exact campsite ID or case-insensitive campsite name. Requires at least one `--campground` or `--rec-area`. Rejects blank strings.    |
| `--campsite-type` | Repeatable case-insensitive (`TENT`, `RV`, `CABIN`, `OTHER`) | `()`    | Fails with `UsageError` if the selected provider's `filter_capabilities.preferred_types` is `False`.                                 |
| `--electric`      | Flag (`bool`)                                                | `False` | Require electric hookup (`is_electric is True`). Fails if `filter_capabilities.require_electric` is `False`.                         |
| `--accessible`    | Flag (`bool`)                                                | `False` | Require ADA accessibility (`is_accessible is True`). Fails if `filter_capabilities.require_accessible` is `False`.                   |
| `--rv-length`     | Integer (`1..200`)                                           | `None`  | Minimum compatible vehicle/RV length in whole feet (`max_vehicle_length >= N`). Rejects `<= 0` or `> 200` and unsupported providers. |
| `--notifications` | Repeatable case-insensitive (`pushover`, `ntfy`)             | `()`    | When omitted, console-only mode runs with zero credential reads.                                                                     |
| `--state-file`    | File path                                                    | `None`  | Optional JSON file path storing seen stay keys across runs to suppress duplicate alerts.                                             |
| `--search-once`   | Flag (`bool`)                                                | `False` | Perform one availability check cycle and exit `0`.                                                                                   |
| `--interval`      | Float (`>= 5.0`)                                             | `60.0`  | Wait interval in seconds between continuous checks. Rejects values `< 5.0`.                                                          |
| `--json`          | Flag (`bool`)                                                | `False` | Emit JSON array of stays to `stdout` and route all logs to `stderr`. Requires `--search-once`.                                       |

### `camply test-notifications` Options

| Option               | Type / Choices                                   | Required | Contract & Validation                                 |
| -------------------- | ------------------------------------------------ | -------- | ----------------------------------------------------- |
| `--notifications`    | Repeatable case-insensitive (`pushover`, `ntfy`) | Yes      | Select one or both channels to verify.                |
| `--debug/--no-debug` | Boolean flag                                     | No       | Standard diagnostic switch; never logs secret tokens. |

### `camply recreation-areas` & `camply campgrounds` New Options

| Option    | Type             | Default | Contract & Validation                                                                                                |
| --------- | ---------------- | ------- | -------------------------------------------------------------------------------------------------------------------- |
| `--limit` | Integer `1..500` | `50`    | Maximum results to display; probes `limit + 1` upstream to emit a truncation warning when more than `--limit` exist. |
| `--json`  | Flag (`bool`)    | `False` | Emit JSON array of discovery results to `stdout` and route all logs to `stderr`.                                     |

### `camply providers` New Behavior

- `--json` flag emits structured provider metadata including `filter_capabilities`.
- Standard log output includes supported site-attribute filters (e.g., `site types, electric, accessible, RV length`) alongside discovery and availability capabilities.

### `camply db metadata` New Behavior

- `--provider-id` (and alias `--provider`) accepts numeric provider IDs (`1`–`26`), canonical CLI provider names/aliases (case-insensitive, e.g. `RecreationDotGov`, `ReserveCalifornia`), or `all`.
