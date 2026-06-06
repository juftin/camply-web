<div align="center">
<a href="https://github.com/juftin/camply">
  <img src="https://raw.githubusercontent.com/juftin/camply/main/docs/_static/camply.svg"
    width="400" height="400" alt="camply">
</a>
</div>

<div align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue.svg" alt="License: PolyForm Noncommercial 1.0.0"></a>
</div>

**`camply`**, the campsite finder ⛺️, is a tool to help you book a campsite online. Finding
reservations at sold out campgrounds can be tough. That's where camply comes in. It searches
thousands of campgrounds across the ~~USA~~ world via the APIs of booking services like
[recreation.gov](https://recreation.gov). It continuously checks for cancellations and
availabilities to pop up - once a campsite becomes available, camply sends you a notification
to book your spot!

---

## Directory Structure

```text
📂 camply
├── README.md
├── docker-compose.yaml
├── cli/
|   ├── pyproject.toml
|   └── camply/
├── frontend/
|   ├── Dockerfile
|   ├── docker-compose.yaml
|   ├── package.json
|   ├── tsconfig.json
|   ├── src/
|   └── public/
└── backend/
    ├── Dockerfile
    ├── docker-compose.yaml
    ├── pyproject.toml
    ├── uv.lock
    └── packages/
        ├── backend/
        |   ├── pyproject.toml
        |   └── backend/
        ├── db/
        |   ├── pyproject.toml
        |   ├── migrations/
        |   └── db/
        ├── providers/
        |   ├── pyproject.toml
        |   └── providers/
        └── worker/
            ├── pyproject.toml
            ├── tests/
            └── worker/
```

### cli

- This directory contains the legacy command-line interface (CLI) for the project.
  There will be no further development on this CLI and it can be ignored for new
  features.

### frontend

- **Stack**: React 18 + TypeScript + Vite + Tailwind CSS + Shadcn/UI.
- **State**: TanStack Query for server state; React Context for auth.
- **Forms**: React Hook Form + Zod for strict validation.
- **API**: Axios client with OpenAPI TypeScript codegen.
- **Auth**: Auth0 redirect or local auto-auth, toggleable via backend config.
- **Pages**: Home (search), Dashboard (scan management), Early Access gate,
  Campground/Rec Area detail, static content pages.
- The frontend can be published as a static site served by any web server.

### backend

- **Stack**: Python 3.12 + FastAPI + SQLAlchemy (async) + Pydantic v2.
- **API Endpoints**: Search, campground/rec-area lookup, user profile (`/me`),
  scan CRUD (`/scans`) — all with OpenAPI docs at `/api/docs`.
- **Auth**: Two modes — local (auto-admin, no token needed) and Auth0 (JWT
  validation via PyJWT + JWKS).
- The backend is a `uv` workspace containing multiple packages:
  - `backend/`: FastAPI application serving API endpoints and auth.
  - `db/`: Database models (User, UniqueTarget, UserScan, ScanResult, etc.)
    and Alembic migrations.
  - `providers/`: Third-party API providers (Recreation.gov) with pluggable
    `BaseProvider` ABC.
  - `worker/`: Celery-powered background task worker for campsite polling,
    availability diffing, de-duplicated scanning, and Pushover notifications.
