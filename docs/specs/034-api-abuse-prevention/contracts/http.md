# API Protection HTTP Contract

## Hosted traffic

The Pages Function takes browser requests at same-origin `/api` and `/api/*`, including auth configuration and API documentation. It sets `X-Camply-Proxy-Secret` from `CAMPLY_API_PROXY_SECRET` and `X-Camply-Client-IP` from the platform's visitor IP. The gateway replaces any inbound values. It sends these only to its configured HTTPS backend, disables caching and automatic redirect following, and preserves application cookies, CSRF and bearer headers. An explicit foreign `Origin` or cross-origin `Sec-Fetch-Site` is denied. Any client can use a public frontend route within its quota.

The backend enforces both private headers when `CAMPLY_API_PROXY_REQUIRED=true`, which also requires session or Auth0 user authentication. A request lacking valid gateway provenance receives HTTP 403. Exact `GET` and `HEAD` requests to `/api/ping` and `/api/health` are exempt for existing probes. Pages keeps the readiness endpoint private, and operators must also restrict it at backend ingress. Other API paths, including schema, docs and unknown endpoints, are protected. Existing authorization and CSRF checks still apply. Transport details belong only in server runtime configuration.

## Counting policy

Each quota starts a fresh window when its prior window expires. A request can be subject to multiple rows, such as an account mutation plus an IP pre-authentication budget. Quota keys use route families and trusted identities. IPv4-mapped IPv6 addresses use their IPv4 value, and other IPv6 addresses are grouped by /64. IDs, query strings, request headers and cookies supplied by the user are never used directly as keys.

| Policy             | Identity               | Initial budget      | Scope                                                                |
| ------------------ | ---------------------- | ------------------- | -------------------------------------------------------------------- |
| General            | Client IP              | 240 per minute      | Public requests under `/api` without a more specific scope           |
| Discovery          | Client IP              | 120 per minute      | Search, Explore, map, campground, recreation-area and provider reads |
| Pre-authentication | Client IP              | 240 per minute      | Private API routes before user verification                          |
| Login              | Client IP              | 10 per five minutes | Password login attempts, including unsuccessful attempts             |
| Request access     | Client IP              | 5 per hour          | Access request submissions                                           |
| Account writes     | Verified account       | 30 per minute       | Authenticated mutations                                              |
| Notification test  | Verified account       | 3 per ten minutes   | Test delivery                                                        |
| Provider sync      | Verified administrator | 3 per ten minutes   | Manual provider sync                                                 |

## Errors

| Condition                                                       | Status | Behavior                                                                                                |
| --------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------- |
| Gateway denies foreign browser context or API denies provenance | 403    | Generic denial before API processing                                                                    |
| Gateway misconfigured or trusted client IP unavailable          | 503    | Upstream request is skipped                                                                             |
| Request body exceeds 128 KiB                                    | 413    | API parsing and side effects are skipped                                                                |
| Explore offset exceeds 50,000                                   | 422    | The database search is skipped. `total_pages` reports browsable pages, and `total` reports all matches. |
| Budget exhausted                                                | 429    | Positive integer `Retry-After` in seconds                                                               |
| Shared accounting unavailable                                   | 503    | `Retry-After: 5` and no protected operation                                                             |

Protective error responses are non-cacheable. Successful and ordinary application error responses preserve the existing API shapes.
