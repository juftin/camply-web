# Quickstart Validation Guide: CLI Full-Stack Parity

**Feature**: `031-cli-fullstack-parity`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Contract**: [contracts/cli-contract.md](contracts/cli-contract.md)

## Prerequisites

- Python >=3.11 (default 3.14) and `uv` / `task` installed.
- Dependencies synced (`task install`).

## Validation Scenarios

### 1. Provider Capabilities & Discovery Pagination / JSON (`FR-002`, `FR-006`, `FR-007`)

- Verify `camply providers` displays supported site-attribute filters and supports `--json`:
  ```bash
  uv run camply providers
  uv run camply providers --json
  ```
- Verify `camply recreation-areas` and `camply campgrounds` support `--limit` beyond 50 items and `--json` output with clean stdout/stderr separation:
  ```bash
  uv run camply recreation-areas --search Yosemite --state CA --limit 100 --json
  uv run camply campgrounds --rec-area 2991 --limit 100
  ```
- Verify `camply db metadata` accepts canonical provider names as well as numeric IDs:
  ```bash
  uv run camply db metadata --help
  ```

### 2. Campsite, Equipment & Accessibility Filtering (`FR-001`, `FR-005`)

- Verify `camply campsites` filters by `--campsite-type`, `--electric`, `--accessible`, `--rv-length`, and `--campsite`, supports `--search-once`, `--interval`, and `--json`, and rejects unsupported provider filters or `--campsite` without a parent target before making HTTP requests:
  ```bash
  uv run pytest tests/cli/test_search.py tests/core/test_search.py
  ```

### 3. Pushover & ntfy Notifications + Deduplication (`FR-003`, `FR-004`)

- Verify `camply test-notifications` and `camply campsites --notifications` validate credentials and settings from environment variables (`PUSHOVER_USER_KEY`, `PUSHOVER_APP_TOKEN`, `NTFY_TOPIC`, `NTFY_SERVER_URL`, `NTFY_ACCESS_TOKEN`), suppress duplicate alerts across continuous cycles and `--state-file` single-pass runs, and redact secrets on errors:
  ```bash
  uv run pytest tests/cli/test_notifications.py
  ```

### 4. Installed Base-Wheel Verification (`FR-008`, `SC-005`)

- Verify all new CLI flags and commands run from an isolated base-only wheel installation without `server` or `distributed` extras:
  ```bash
  task backend:packaging:test
  ```

### 5. Full Quality Gates

```bash
task fix
task lint
task check
task test
task docs:check
```
