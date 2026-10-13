# AGENT_TROUBLESHOOTING: Common Issues & Solutions

This document helps agents and contributors resolve common environment and runtime issues encountered during the development of `camply`.

## 🛠️ Infrastructure Issues

### 1. "Valkey Connection Refused" or "Broker Connection Error"

- **Cause**: The Valkey container is not running or the worker can't reach it.
- **Solution**:
  - Ensure Docker is running: `docker compose ps`.
  - Restart infrastructure: `docker compose up -d valkey`.
  - Check `.env`: Ensure `REDIS_URL` points to `redis://localhost:6379/0`. (Note: Celery uses the `redis://` protocol even for Valkey).

### 2. "Postgres: Password Authentication Failed"

- **Cause**: Local DB credentials mismatch.
- **Solution**:
  - Check `DATABASE_URL` in `.env`.
  - If needed, reset the DB container: `docker compose down -v db && docker compose up -d db`.

---

## 🐍 Backend (Python) Issues

### 3. "Alembic: Multiple Heads Detected"

- **Cause**: Two agents created migrations simultaneously.
- **Solution**:
  - Run `uv run alembic merge heads` to create a new merge migration.
  - Or, delete the conflicting migration if it hasn't been pushed yet.

### 4. "VCR Cassette Missing" or "No Match Found"

- **Cause**: A new provider test was added but the API response wasn't recorded.
- **Solution**:
  - Run the test with record mode: `task backend:test -- --vcr-record=new_episodes`.
  - Ensure you have the necessary API keys in your `.env`.

---

## ⚛️ Frontend (React) Issues

### 5. "TypeScript Error: Module './lib/api' has no exported member..."

- **Cause**: The frontend SDK is out of sync with the FastAPI backend.
- **Solution**:
  - Ensure the backend is running.
  - Run the codegen: `task frontend:codegen`.

### 6. "Auth0: Callback URL Mismatch"

- **Cause**: Local dev URL (`http://localhost:5173`) isn't allowed in the Auth0 dashboard.
- **Solution**:
  - Add `http://localhost:5173/auth/callback` to "Allowed Callback URLs" in your Auth0 Application settings.
  - Or, use `CAMPLY_AUTH_MODE=none` for automatic admin login.

### Password login succeeds but scan requests return 401

- **Diagnosis**: `Sign in required` means the backend received no usable `camply_session` cookie. `Session expired or invalid` means the cookie reached the backend but failed verification. Never copy cookie values into logs or reports.
- **Cross-site requests**: Check the failed request's `Sec-Fetch-Site` header and the cookie's blocking reason in browser DevTools. Password-session cookies use `SameSite=Strict`; CORS permissions do not override that cookie policy. HTTPS subdomains of the same parent domain can be same-site, while unrelated frontend and API domains are cross-site.
- **Solution for cross-site requests**: Route `/api` through the frontend host. The Docker frontend's Nginx configuration already proxies `/api/` to the backend service, and Vite provides the same proxy for development. Leave `VITE_API_URL` unset or set it to `/api`, then rebuild the frontend. The backend can remain on a separate internal host. A separately hosted static frontend needs an equivalent `/api` proxy on its hosting platform.
- **Cloudflare Pages**: This repository includes a Pages Function for `/api`. Use Pages project root `frontend`, set runtime `CAMPLY_API_ORIGIN` to the HTTPS backend origin without `/api`, leave build-time `VITE_API_URL` unset or `/api`, and redeploy with Functions included. Keep the frontend origin trusted by the backend. See [Cloudflare Pages configuration](CONFIGURATION.md#cloudflare-pages-frontend) for production and preview settings. Nginx configuration does not apply to Pages hosting.
- **HTTPS**: Keep `CAMPLY_SESSION_COOKIE_SECURE=true`. After correcting routing, sign in again and confirm the session cookie is sent with `/api/me` and `/api/scans`.

---

## 🤖 Agent Workflow Issues

### 7. "Git Worktree Conflict"

- **Cause**: Trying to create a worktree for a branch that is already checked out.
- **Solution**:
  - Check existing worktrees: `git worktree list`.
  - Use a unique name: `git worktree add .worktrees/feature-v2 -b feature-v2`.

### 8. "Pre-Commit Hook Failure"

- **Cause**: Linting or formatting errors detected on commit.
- **Solution**:
  - Run `task fix` to automatically resolve most issues.
  - Review manual fixes for type errors (`mypy`/`tsc`).
