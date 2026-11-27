# Contract: Provider Transport Cooldown, Pacing & Opt-In Proxy Rotation

**Feature**: [037-provider-backoff-proxy-rotation](../spec.md) | **Date**: 2026-11-27

This contract defines the external configuration surface, HTTP retry/cooldown/proxy state transitions, credential redaction rules, failure modes, and observability hooks for `camply.providers`.

## 1. Environment Variable Contract

All settings use the `CAMPLY_` prefix (case-insensitive) and are loaded by `ProviderTransportConfig` in `src/camply/providers/transport_config.py`.

| Variable                               | Type    | Default  | Valid Range / Values       | Semantics                                                                                                 |
| -------------------------------------- | ------- | -------- | -------------------------- | --------------------------------------------------------------------------------------------------------- |
| `CAMPLY_PROVIDER_MAX_CONCURRENCY`      | `int`   | `4`      | `>= 0`                     | Max concurrent in-flight HTTP requests per provider per process. `0` disables the limit.                  |
| `CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS` | `float` | `0.0`    | `0.0 <= x <= 60.0`         | Minimum spacing in seconds between outgoing request starts to the same provider. `0.0` disables spacing.  |
| `CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS` | `float` | `60.0`   | `0.0 < x <= 600.0`         | Upper bound for `Retry-After` clamping, shared cooldown sleeps, and `wait`-policy proxy exhaustion waits. |
| `CAMPLY_PROXY_URLS`                    | `str`   | `""`     | Comma-separated proxy URLs | Opt-in BYO proxy pool. Empty/unset disables proxy rotation with zero overhead.                            |
| `CAMPLY_PROXY_QUARANTINE_SECONDS`      | `float` | `60.0`   | `0.0 < x <= 3600.0`        | Default quarantine window when a proxy fails or receives 403 / 429 without positive `Retry-After`.        |
| `CAMPLY_PROXY_EXHAUSTED_POLICY`        | `str`   | `"wait"` | `"wait"` \| `"fail"`       | Behavior when all configured proxies are quarantined. Never falls back to direct egress.                  |

### Supported Proxy Schemes

- **Native (zero extra dependencies)**: `http://` and `https://`, with optional `user:pass@` basic auth and optional `:port`.
- **Optional SOCKS5**: `socks5://` and `socks5h://`, accepted only when `socksio` is installed in the active Python environment.
- **Invalid inputs**: Any missing scheme, unsupported scheme (e.g., `ftp://`, `socks4://`), empty hostname, invalid port, or SOCKS5 URL without `socksio` raises `ValueError` during configuration parsing with credentials stripped from the message.

### Example Configurations

```bash
# Default (zero proxies, shared 429 cooldown + concurrency cap of 4):
# No environment variables required.

# Stricter polite pacing without proxies:
CAMPLY_PROVIDER_MAX_CONCURRENCY=2
CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS=0.25

# Single BYO proxy (e.g. Gluetun, Tailscale exit node, or Cloudflare WARP):
CAMPLY_PROXY_URLS="http://gluetun:8888"

# Multi-proxy rotation with credentials and fail-fast exhaustion:
CAMPLY_PROXY_URLS="http://proxy1.internal:8080,http://user:pass@proxy2.internal:8080"
CAMPLY_PROXY_QUARANTINE_SECONDS=90
CAMPLY_PROXY_EXHAUSTED_POLICY=fail
```

## 2. `Retry-After` Parsing Contract

`parse_retry_after(raw_header: str | None, *, max_seconds: float, now_utc: datetime | None = None) -> float | None`

1. `None` or blank string → returns `None`.
2. Numeric string (integer or float, e.g., `"5"`, `"2.5"`):
   - Non-finite (`nan`, `inf`) or `<= 0` → returns `None` (caller falls back to exponential backoff or default quarantine window).
   - Positive finite value → returns `min(value, max_seconds)`.
3. RFC 9110 HTTP-date string (via `email.utils.parsedate_to_datetime`, e.g., `"Wed, 21 Oct 2026 07:28:00 GMT"`):
   - Convert naive parsed datetime as UTC; compute `delta = (parsed - now_utc).total_seconds()`.
   - If `delta <= 0` → returns `None`.
   - Otherwise → returns `min(delta, max_seconds)`.
4. Unparseable string → returns `None`.

## 3. Request Lifecycle & State Transition Matrix

### 3.1 Direct Mode (`CAMPLY_PROXY_URLS` unset or empty)

1. `await circuit_breaker.check()` (if configured) — raises `CircuitBreakerOpenError` when `OPEN`.
2. Buffer request body once (`await request.aread()`).
3. For `attempt` in `0..max_retries`:
   - Enter `cooldown_gate.slot(wait_cooldown=True)`:
     1. Loop sleeping while `monotonic() < cooldown_until` (outside concurrency semaphore).
     2. Acquire per-provider concurrency semaphore (if `max_concurrency > 0`).
     3. Re-check `cooldown_until` (in case a sibling triggered cooldown while queued).
     4. Reserve & wait for `min_interval_seconds` (lock released before sleep).
     5. Send single HTTP attempt via `self._inner.handle_async_request(req)`.
     6. Release concurrency semaphore in `finally` before any retry backoff sleep.
   - Outcome handling:

| Outcome                                                     | Cooldown Gate Action                                                           | Retry?                                                                            | Circuit Breaker (on final exit) | Return / Raise                   |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- | ------------------------------- | -------------------------------- |
| `2xx` / `3xx` / `400` / `401` / `403` / `404`               | None                                                                           | No                                                                                | 1 success                       | Return `Response`                |
| `429` (`retry_on_429=False`)                                | None                                                                           | No                                                                                | 1 success                       | Return `Response(429)`           |
| `429` (`retry_on_429=True`, `attempt < max_retries`)        | `trigger_cooldown(delay)` (`Retry-After` or `base_delay` exp backoff, clamped) | Yes (next loop waits on gate; no duplicate local sleep)                           | Deferred                        | Continue                         |
| `429` (`retry_on_429=True`, `attempt == max_retries`)       | `trigger_cooldown(delay)` (protects subsequent callers)                        | No                                                                                | 1 failure                       | Raise `ProviderRateLimitedError` |
| `5xx` (`retry_on_5xx=True`, `attempt < max_retries`)        | None                                                                           | Yes (local `_5xx_base_delay` exp backoff)                                         | Deferred                        | Continue                         |
| `5xx` (exhausted or `retry_on_5xx=False`)                   | None                                                                           | No                                                                                | 1 failure (if 5xx)              | Return last `Response`           |
| `ConnectError` / `TimeoutException` / `RemoteProtocolError` | None                                                                           | Yes if `retry_on_connection_errors` & `attempt < max_retries` (local exp backoff) | 1 failure on exhaustion         | Raise last exception             |

### 3.2 Proxy Mode (`CAMPLY_PROXY_URLS` non-empty)

**Hard Egress Invariant**: `self._inner` (direct connection pool) is NEVER invoked when `proxy_pool` is active. Each proxy slot lazily creates an `httpx2.AsyncHTTPTransport(proxy=endpoint.raw_url, limits=limits, trust_env=False)`.

1. `await circuit_breaker.check()` (if configured) — raises `CircuitBreakerOpenError` when `OPEN`.
2. Buffer request body once (`await request.aread()`).
3. For `attempt` in `0..max_retries`:
   - `endpoint = await proxy_pool.select(provider_name)`:
     - Round-robin across entries where `now >= entry.quarantine_until(provider_name)`.
     - If none are healthy:
       - Compute `soonest_wait = max(0.0, min(e.quarantine_until(provider_name) for e in entries) - now)`.
       - If `exhausted_policy == "fail"` OR `soonest_wait > max_cooldown_seconds`: emit `proxy_exhausted` event and raise `ProxyPoolExhaustedError(provider_name, retry_after=soonest_wait, pool_size=len(entries))` **without** incrementing circuit-breaker failures.
       - If `exhausted_policy == "wait"` and `soonest_wait <= max_cooldown_seconds`: emit `cooldown_wait` (`reason="all_quarantined"`), sleep `soonest_wait`, re-select.
   - Enter `cooldown_gate.slot(wait_cooldown=False)` (enforces `max_concurrency` and `min_interval_seconds`, without blocking healthy alternate proxies on a single IP's 429):
     - Send single HTTP attempt via `proxy_transport.handle_async_request(req)`.
     - Release concurrency semaphore in `finally`.
   - Outcome handling:

| Outcome                                                                    | Proxy Quarantine Action                                                                                       | Retry?                                                                                                    | Circuit Breaker (on final exit) | Return / Raise                                           |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------- |
| `2xx` / `3xx` / `400` / `401` / `404`                                      | None                                                                                                          | No                                                                                                        | 1 success                       | Return `Response`                                        |
| `429` (`retry_on_429=False`)                                               | None                                                                                                          | No                                                                                                        | 1 success                       | Return `Response(429)`                                   |
| `429` (`retry_on_429=True`)                                                | Provider-scoped quarantine on `endpoint.index` (`clamped Retry-After` if positive, else `quarantine_seconds`) | Yes if `attempt < max_retries` (rotates immediately to next healthy proxy)                                | 1 failure on exhaustion         | Continue; on exhaustion raise `ProviderRateLimitedError` |
| `403` (WAF / IP block)                                                     | Provider-scoped quarantine on `endpoint.index` (`quarantine_seconds`, `reason="403"`)                         | Yes if `attempt < max_retries` (rotates immediately to next healthy proxy)                                | 1 failure on exhaustion         | Continue; on exhaustion return last `Response(403)`      |
| `5xx` (`retry_on_5xx=True`)                                                | **None** (do not quarantine healthy proxy for upstream 5xx)                                                   | Yes if `attempt < max_retries` (local `_5xx_base_delay` exp backoff)                                      | 1 failure on exhaustion         | Continue; on exhaustion return last `Response`           |
| `ProxyError` / `ConnectError` / `TimeoutException` / `RemoteProtocolError` | **Global** quarantine on `endpoint.index` (`quarantine_seconds`)                                              | Yes if `retry_on_connection_errors` & `attempt < max_retries` (rotates immediately to next healthy proxy) | 1 failure on exhaustion         | Continue; on exhaustion raise sanitized exception        |

## 4. Credential Redaction Contract

1. Every proxy URL is parsed into a `ProxyEndpoint` whose `label` is strictly `proxy-{index} ({scheme}://{host}:{port})` (or `proxy-{index} ({scheme}://{host})` when no explicit port is given).
2. `ProxyEndpoint.__repr__`, `ProxyEndpoint.__str__`, `ProviderTransportConfig.__repr__`, `ProxyPool.__repr__`, and `ProxyPoolExhaustedError.__str__` MUST NEVER include `username`, `password`, query strings, or raw `CAMPLY_PROXY_URLS`.
3. A shared helper `redact_proxy_url(raw_url: str) -> str` strips `userinfo@`, query, and fragment from any URL string before formatting validation or transport error messages.
4. When re-raising a transport exception in proxy mode, if `str(exc)` contains any configured credential token, the message is scrubbed via `redact_proxy_url` / credential replacement while preserving the original exception class.

## 5. Observability & Boundary Contract

### Structured Logs (`structlog`, always active in base package)

- `Provider cooldown active; waiting` (`level=debug`, fields: `provider`, `delay_seconds`, `reason`)
- `Provider cooldown triggered` (`level=warning`, fields: `provider`, `delay_seconds`, `reason`)
- `Proxy quarantined` (`level=warning`, fields: `provider`, `proxy`, `reason`, `scope` (`"provider"` \| `"global"`), `quarantine_seconds`)
- `Proxy pool exhausted` (`level=warning`, fields: `provider`, `policy`, `pool_size`, `retry_after_seconds`)

### Optional Observer Hook (`camply.providers.transport_config`)

```python
TransportObserver = Callable[[TransportEvent], None]
def register_transport_observer(observer: TransportObserver) -> None: ...
def unregister_transport_observer(observer: TransportObserver) -> None: ...
```

- Observer exceptions are caught and logged at debug level so telemetry can never break provider requests.
- `camply.worker.metrics` registers a Prometheus observer when imported by distributed workers, updating:
  - `camply_provider_cooldown_waits_total` (Counter, labels: `["provider", "reason"]`)
  - `camply_provider_cooldown_wait_seconds` (Histogram, labels: `["provider"]`)
  - `camply_provider_proxy_events_total` (Counter, labels: `["provider", "event", "reason"]`, where `event` is `"selected"` | `"quarantined"` | `"exhausted"`)
- **Import boundary**: `camply.providers.**` MUST NEVER import `prometheus_client`, `celery`, `redis`, `fastapi`, or `camply.worker`.
