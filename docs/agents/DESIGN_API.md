# DESIGN_API: API Contract & Security

This document defines the interface between the `camply-backend` (FastAPI) and `camply-frontend` (React). It also outlines the security flow for Auth0 and early access whitelisting.

## 🎯 API Philosophy
1. **OpenAPI-First**: Every endpoint must be documented so that the frontend TypeScript client can be automatically generated.
2. **Standardized Responses**: All successful responses use `ORJSONResponse` for performance.
3. **Strict Validation**: Every request payload must be a Pydantic v2 model.
4. **Auth-Gated**: All user-specific endpoints are gated by the `CurrentUserDep` dependency.

---

## 🔒 Security & Middleware

### 1. Auth Modes
The backend supports two authentication modes, controlled by the `CAMPLY_AUTH_MODE` environment variable:

**Local mode** (`auth_mode=local` — default):
- No bearer token is required.
- A synthetic admin user is created on first access, configured via `CAMPLY_ADMIN_EMAIL`.
- Suitable for single-user self-hosted deployments.

**Auth0 mode** (`auth_mode=auth0`):
- Frontend sends the Auth0 JWT in the `Authorization: Bearer <token>` header.
- Backend validates the signature, issuer, and audience against Auth0's JWKS endpoint.
- Users are upserted into the database on first login.
- See `backend/packages/backend/backend/auth.py` for implementation details.

### 2. Early Access (Whitelist) Middleware
- **Check**: For every request to `/api/v1/scans/*`, the backend checks the user's `is_early_access_user` flag.
- **Action**: If the user is not whitelisted, the backend returns `403 Forbidden` with error code `ERR_EARLY_ACCESS_REQUIRED`.
- **UI Interaction**: The frontend catches `403` and the `Dashboard` component redirects to the Early Access page.

---

## 🏗️ Endpoint Definitions

### 1. Search & Metadata (Public/Auth-Light)
- **`GET /api/search?query=<term>`**: Full-text search for campgrounds and recreation areas (uses the `Search` FTS table).
- **`GET /api/providers`**: List supported providers and their scanning capabilities.
- **`GET /api/provider/{id}`**: Get a single provider by ID.
- **`GET /api/campground/{provider}/{id}`**: Get a single campground.
- **`GET /api/rec-area/{provider}/{id}`**: Get a recreation area.
- **`GET /api/rec-area/{provider}/{id}/campgrounds`**: List campgrounds within a recreation area.

### 2. User & Profile (Auth-Required)
- **`GET /api/me`**: Get current user profile and whitelist status.
- **`PATCH /api/me`**: Update user-specific settings (e.g., `pushover_token`).

### 3. Scan Management (Auth-Required + Whitelist)
- **`GET /api/scans`**: List all scans belonging to the current user (paginated).
- **`POST /api/scans`**: Create a new scan.
    - **Logic**: Backend calculates the target `hash`, creates/links the `UniqueTarget` (de-duplication), and creates the `UserScan`.
    - Returns `201 Created` on success, `409 Conflict` if a duplicate scan exists.
- **`GET /api/scans/{id}`**: Detailed view of a scan, including recent `scan_results`.
- **`PATCH /api/scans/{id}`**: Update scan filters (`min_stay_length`, `preferred_types`, `require_electric`) or toggle `is_active`.
- **`DELETE /api/scans/{id}`**: Unsubscribe from a scan (returns `204 No Content`).

---

## 📦 Request / Response DTOs (Pydantic)

All schemas are defined in `backend/packages/backend/backend/schemas.py`.

### `ScanCreateRequest`
```python
class ScanCreateRequest(BaseModel):
    provider_id: int = Field(..., description="Provider identifier")
    campground_id: str = Field(..., description="Provider-internal campground ID")
    start_date: date = Field(..., description="Check-in date")
    end_date: date = Field(..., description="Check-out date")
    min_stay_length: int = Field(default=1, ge=1)
    preferred_types: list[str] = Field(default_factory=list)
    require_electric: bool = Field(default=False)
```

### `ScanResponse`
```python
class ScanResponse(BaseModel):
    id: UUID
    provider_id: int
    campground_id: str
    campground_name: str
    recreation_area_name: str
    start_date: date
    end_date: date
    is_active: bool
    min_stay_length: int
    preferred_types: list[str]
    require_electric: bool
    last_checked_at: datetime | None
    found_count: int
    created_at: datetime
```

### `ScanDetailResponse` extends `ScanResponse`
Adds:
```python
    results: list[ScanResultItem]
```

### `ScanResultItem`
```python
class ScanResultItem(BaseModel):
    campsite_id: str
    campsite_name: str
    available_dates: list[str]
```

---

## 🔄 Client Generation Workflow
1. Backend developer updates the FastAPI router.
2. Run `task backend:check` to ensure types are correct.
3. Start the backend: `task backend:dev`.
4. Run: `npx tsx src/lib/codegen.ts` from `frontend/`.
    - Fetches `http://localhost:8000/api/openapi.json`.
    - Generates TypeScript types in `frontend/src/lib/api/generated/schema.ts`.
5. Register new endpoints in `frontend/src/lib/api.ts` and `frontend/src/lib/structs.ts`.

---

## 🗺️ Endpoint Summary

| Method | Path | Auth | Whitelist | Purpose |
|--------|------|------|-----------|---------|
| GET | `/api/search?query=` | — | — | Search campgrounds/rec areas |
| GET | `/api/providers` | — | — | List providers |
| GET | `/api/provider/{id}` | — | — | Single provider |
| GET | `/api/campground/{provider}/{id}` | — | — | Single campground |
| GET | `/api/rec-area/{provider}/{id}` | — | — | Single rec area |
| GET | `/api/rec-area/{provider}/{id}/campgrounds` | — | — | Campgrounds in rec area |
| GET | `/api/me` | ✓ | — | Current user profile |
| PATCH | `/api/me` | ✓ | — | Update profile |
| GET | `/api/scans` | ✓ | ✓ | List user scans |
| POST | `/api/scans` | ✓ | ✓ | Create scan |
| GET | `/api/scans/{id}` | ✓ | ✓ | Scan detail |
| PATCH | `/api/scans/{id}` | ✓ | ✓ | Update scan |
| DELETE | `/api/scans/{id}` | ✓ | ✓ | Delete scan |
| GET | `/api/health` | — | — | Health check |
