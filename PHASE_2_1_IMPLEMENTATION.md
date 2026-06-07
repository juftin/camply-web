# Phase 2.1 Implementation: Auth0 & Profile

## Overview
Implement Auth0 frontend integration, a dedicated User Profile page, and
Request Access endpoint for the Early Access gate.

## Tasks

### T2.1.3 — Auth0 Frontend Integration

Install `@auth0/auth0-react` and wire up Auth0 in the frontend.

**Files to touch:**
- `frontend/package.json` — add `@auth0/auth0-react` dependency
- `frontend/src/main.tsx` — wrap with `Auth0Provider` (domain, clientId, audience from VITE_AUTH0_* env vars)
- `frontend/src/hooks/useAuth.tsx` — integrate Auth0 state (isAuthenticated, user from Auth0) alongside the `/api/me` endpoint. In Auth0 mode, pass the access token via Axios interceptor. In local mode, keep current behavior.
- `frontend/src/pages/Auth.tsx` — add "Continue with Auth0" button that triggers `loginWithRedirect()`. Keep existing form but with backend-not-ready messaging.
- `frontend/src/lib/api.ts` — add Axios request interceptor that injects `Authorization: Bearer <token>` when Auth0 is configured and an access token is available.

**Env vars used:**
```
VITE_AUTH0_DOMAIN
VITE_AUTH0_CLIENT_ID
VITE_AUTH0_AUDIENCE
VITE_API_URL
```

**Key considerations:**
- Don't break local mode — all Auth0 integration should be gated on the env vars being set
- Use `@auth0/auth0-react`'s `useAuth0()` hook inside the `useAuth` context provider

### T2.1.4 — User Profile Page

Create a dedicated `/profile` page for Pushover key management and account settings,
separate from the Dashboard settings panel.

**New files:**
- `frontend/src/pages/Profile.tsx` — Profile page with:
  - User email display
  - Pushover token input with save
  - Account creation date
  - Early access status badge
  - Sign out button

**Modified files:**
- `frontend/src/App.tsx` — add route for `/profile`
- `frontend/src/components/Header.tsx` — add Profile link in user dropdown/settings

### T2.1.6 — Request Access Endpoint

Create a backend endpoint and database model for collecting early access requests.

**Backend:**
- `backend/packages/db/db/models/access_request.py` — New `AccessRequest` model:
  - `id`: UUID PK
  - `email`: String, unique
  - `created_at`: DateTime
- `backend/packages/db/db/models/__init__.py` — export `AccessRequest`
- `backend/packages/db/migrations/versions/` — New Alembic migration
- `backend/packages/backend/backend/routers/access_request.py` — New router:
  - `POST /api/request-access` — accepts `{email: string}`, creates/upserts AccessRequest record
  - Returns `201` on success, `409` if already requested
- `backend/packages/backend/backend/app.py` — register new router
- `backend/packages/backend/backend/schemas.py` — add `AccessRequestResponse` schema

**Frontend:**
- `frontend/src/lib/api.ts` — add `requestAccess(email: string)` function
- `frontend/src/lib/structs.ts` — add `AccessRequestResponse` interface
- `frontend/src/pages/EarlyAccess.tsx` — actually POST to the API instead of simulated auto-submit

### Tests

**Backend tests:**
- `backend/packages/backend/tests/routers/test_auth.py` — Add tests for Auth0 token validation flow
- `backend/packages/backend/tests/routers/` — Add `test_access_request.py` for the new endpoint

**Frontend tests:**
- Update `frontend/src/App.test.tsx` — mock the new Auth0 provider
- `frontend/src/pages/Profile.test.tsx` — basic test for profile page rendering
