# Tasks

- [x] Optional invite-only API enforcement and public `is_invited` flag.
- [x] Remove HTTP Basic and local auth modes; the owner selects automatic login, in-app password sessions, or Auth0 independently of the environment.
- [x] Password login/logout, cookie flags, absolute expiry, credential rotation, and CSRF protection.
- [x] Verify password-session cookies before entering the dashboard, stop automatic scan retries on authentication/access failures, and return to sign-in with cleared scan data when a session scan query receives 401.
- [x] Verify secure HTTPS scan requests and add a Cloudflare Pages `/api` proxy with tested cookie/CSRF forwarding and deployment configuration for cross-site backends.
- [x] Allow HTTPS production, deployment-hash, and branch-alias origins for `camply-81r.pages.dev` through the shared CORS/login policy; reject unrelated Pages projects, HTTP, and lookalike domains.
- [x] Auth0 audience and configuration validation.
- [x] Mode-aware signup, protected routes, and invitation UI.
- [x] Regression tests and documentation.
- [ ] TODO: approval/revocation workflow, identity linking, and invitation notifications.
