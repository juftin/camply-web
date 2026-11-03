# Authentication and optional invitations

## Requirements

- The owner selects `none` (automatic login), `session` (in-app password form and cookie session), or `auth0`. Never use HTTP Basic authentication.
- Authentication is independent of the environment. Automatic login is the default and uses the single admin without login, signup, or logout UI.
- Password session login requires configured credentials and a signing secret; use HTTP-only expiring cookies and CSRF protection. Signup is unavailable for shared-account modes.
- Invite-only access is optional and disabled by default. When enabled, every scan operation requires an invited user. Profile and public browsing stay accessible.
- Expose the API audience and auth capabilities to the frontend. Request that audience from Auth0. Show configuration failures explicitly.
- Signup appears only in Auth0 mode. Marketing links follow login capabilities.
- Rename the public access flag to `is_invited`; preserve its existing database column.
- Invitation approval, revocation, account linking, and notification delivery remain TODOs.

## Acceptance

Test enabled/disabled invite policy, all scan operations, owner-selected auto-login, cookie login/logout, expiry/tampering/CSRF checks, rejection of Basic credentials, audience propagation, signup visibility, protected routes, and configuration failures.
