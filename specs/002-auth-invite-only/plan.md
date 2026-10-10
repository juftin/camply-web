# Implementation plan

1. Support owner-selected automatic login, in-app password sessions, and Auth0 independently of the environment. Remove HTTP Basic credentials and challenges. Update configuration and auth dependencies; retain the existing database column. Verify API behavior with pytest.
2. Use signed, expiring HTTP-only session cookies with CSRF protection. Propagate capabilities and audience; add protected-route handling and mode-aware links. Verify UI behavior with Vitest.
3. Update configuration, API, frontend design, and checklist documentation. Run task lint, check, and test.

## Cross-site session transport fix

Route Cloudflare Pages `/api` requests through a Pages Function to a configured HTTPS `CAMPLY_API_ORIGIN`, with the browser using the relative `/api` base URL. Preserve request bodies, session/CSRF headers, and both host-only cookies; disable API caching and keep upstream redirects on the frontend host. Keep static assets outside Function routing. Verify proxy transport with Vitest and HTTPS session scan operations with pytest. Verify login cookies before entering the dashboard and recover from scan-query 401s without retries or stale scan data.

## Constitution check

Changes stay within backend/frontend auth boundaries, use typed configuration and responses, and include automated regressions. No new dependency or database migration is needed because the mapped column is unchanged.
