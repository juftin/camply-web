# Implementation plan

1. Support owner-selected automatic login, in-app password sessions, and Auth0 independently of the environment. Remove HTTP Basic credentials and challenges. Update configuration and auth dependencies; retain the existing database column. Verify API behavior with pytest.
2. Use signed, expiring HTTP-only session cookies with CSRF protection. Propagate capabilities and audience; add protected-route handling and mode-aware links. Verify UI behavior with Vitest.
3. Update configuration, API, frontend design, and checklist documentation. Run task lint, check, and test.

## Constitution check

Changes stay within backend/frontend auth boundaries, use typed configuration and responses, and include automated regressions. No new dependency or database migration is needed because the mapped column is unchanged.
