# Validate API Abuse Prevention

## Local tests

Set up the project with `task install`. Run `task backend:test`, `task frontend:test`, and `task frontend:pages:check`. Use synthetic gateway secrets and simulated requests. Verify the [HTTP contract](contracts/http.md) against tests for authenticated transport, account and IP quota isolation, reset, store failure, oversized bodies, and current session behavior. Run `task lint`, `task check`, and `task test` before proposing changes.

To check real shared quota accounting, set `CAMPLY_API_TEST_VALKEY_URL` to a disposable Valkey instance and run `task backend:test -- tests/server/test_rate_limits.py`.

## Verification

- Two independent protected FastAPI processes shared one real Valkey 8.0.1 budget. Ten login attempts reached endpoint validation and four received HTTP 429 with a retry interval. An unavailable store returned HTTP 503 while direct liveness kept responding. Ungated origin requests received HTTP 403.
- The 77 focused backend tests covered API protection, sessions, metrics, and search. The opt-in Valkey test passed separately against a disposable instance. Explore tests verified the last permitted offset, rejection before database search, and the capped page count with the full match count preserved.
- The 25 focused Pages tests and the local Wrangler route check passed. OpenAPI client generation, Helm lint and Compose config validation passed.
- Repository formatting, lint, six import boundaries, mypy, and TypeScript checks passed through `task check` and `task lint`.
- Hosted verification requires the deployed Pages binding, API origin and ingress rules described below.

## Hosted deployment

1. Configure an HTTPS API origin distinct from the frontend host. Use private networking or ingress rules for `/metrics`, readiness and liveness. Avoid exposing raw local development service ports.
2. Provision a high-entropy server credential of at least 32 characters. Use a runtime secret on Pages and inject the same value into the backend. Set `CAMPLY_API_ORIGIN` on Pages and keep the browser API base at `/api`. Give preview environments separate credentials and backend origins if they should be isolated.
3. Configure `CAMPLY_AUTH_MODE=session` or `auth0` on the backend, and check the frontend origin and HTTPS settings. Deploy the Pages Function with the new runtime binding before enabling backend enforcement. Test public search, sign-in and an authenticated read on the frontend. Confirm app cookies, redirects and API headers are preserved.
4. Connect the distributed backend to shared Valkey and enable `CAMPLY_API_PROXY_REQUIRED=true` across all its instances. Repeat the frontend smoke checks. An unauthenticated direct-origin API request should now get 403, including direct requests for docs and schema. Infrastructure probes should still pass on their private route.
5. Exercise quota thresholds and temporarily interrupt the quota store on a staging deployment. Check 429 with `Retry-After`, then 503 while accounting is unavailable, and recovery after reconnect. Confirm the deploy has no rate limit bypass through a second listener.

See the [configuration reference](../../operations/CONFIGURATION.md) for broker, gateway and Pages settings. Direct local or self-hosted deployments can leave gateway enforcement off and continue to use their existing frontend workflow.
