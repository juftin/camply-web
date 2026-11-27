# Quickstart Validation Guide: Shared Provider Cooldown, Pacing & Opt-In Proxy Rotation

**Feature**: [037-provider-backoff-proxy-rotation](spec.md) | **Contract**: [provider-transport-contract.md](contracts/provider-transport-contract.md)

Use this guide after implementing the tasks in [tasks.md](tasks.md) to verify every user story, contract invariant, import boundary, and documentation check locally.

## Prerequisites

- Working checkout with `uv`, `task`, and `pnpm` available.
- Dependencies synchronized via `task backend:install` (or `uv sync --locked --all-extras`).

## 1. Targeted Provider Transport & Cooldown Unit Tests (US1 & US2)

Verify shared per-provider cooldown, `Retry-After` delta/HTTP-date parsing, concurrency limiting, pacing, circuit-breaker composition, proxy rotation, quarantine, fail-closed exhaustion, credential redaction, and `aclose()` cleanup:

```bash
task backend:test -- tests/providers/test_base_provider.py tests/providers/test_provider_cooldown.py tests/providers/test_proxy_rotation.py -v
```

**Expected outcome**: All tests pass with zero skipped assertions, zero `RuntimeWarning: coroutine was never awaited` warnings, and zero credential leaks.

## 2. Optional Worker Prometheus Metrics Tests (US3)

Verify that importing `camply.worker.metrics` registers the transport observer and records low-cardinality cooldown and proxy counters/histograms without leaking credentials or proxy URLs into labels:

```bash
task backend:test -- tests/worker/test_worker_metrics.py -v
```

**Expected outcome**: Worker metrics tests pass, including multiprocess safety and transport observer assertions.

## 3. Import Linter & Static Analysis Gates

Verify that `camply.providers.**` remains completely free of optional `prometheus_client`, `celery`, `redis`, `fastapi`, or `sentry_sdk` imports, and that Ruff formatting, linting, and MyPy strict type checking pass cleanly:

```bash
task backend:imports
task backend:lint
task backend:check
```

**Expected outcome**: All three commands exit `0` with zero contract violations, lint warnings, or type errors.

## 4. Isolated Base-Wheel Packaging Check

Verify that the base `camply-web` distribution (without `server`, `distributed`, `postgres`, or `sentry` extras) supports shared cooldown, pacing, and `CAMPLY_PROXY_URLS` configuration cleanly:

```bash
task backend:packaging:test -- tests/packaging/test_base_install.py -v
```

**Expected outcome**: Base wheel builds and passes all import/runtime assertions without optional dependencies installed.

## 5. Full Provider & Backend Regression Suite

Run the complete provider suite and documentation hygiene checks:

```bash
task backend:test -- tests/providers/ tests/docs/test_docs.py -q
task backend:test
```

**Expected outcome**: Full backend test suite passes with zero regressions across all 26 providers and documentation tests.

## 6. Interactive Smoke Check (Optional Manual Sanity Check)

Verify fast-fail proxy validation and credential redaction directly from the shell without touching any live upstream API:

```bash
CAMPLY_PROXY_URLS="http://alice:supersecret@invalid-scheme" uv run python -c "
from camply.providers.transport_config import ProviderTransportConfig
try:
    ProviderTransportConfig().parsed_proxies()
except ValueError as exc:
    assert 'alice' not in str(exc) and 'supersecret' not in str(exc)
    print('Redacted validation error:', exc)
"

CAMPLY_PROXY_URLS="socks5://alice:supersecret@proxy.example:1080" uv run python -c "
from camply.providers.transport_config import ProviderTransportConfig
try:
    ProviderTransportConfig().parsed_proxies()
except ValueError as exc:
    assert 'alice' not in str(exc) and 'supersecret' not in str(exc)
    print('Redacted SOCKS5 error:', exc)
"
```

**Expected outcome**: Both invocations catch `ValueError`, confirm neither `alice` nor `supersecret` appears in the error message, and print an actionable redacted diagnostic.
