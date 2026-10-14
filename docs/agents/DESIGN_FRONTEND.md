# DESIGN_FRONTEND: User Journey & Design System

This document defines the user experience and visual architecture for the `camply` frontend.

## 🎯 Design Goals

1. **Frictionless Search**: Find a campground and start a scan in < 30 seconds.
2. **Real-time Feedback**: Users should know exactly when their scans were last checked.
3. **Mobile-First**: Most users will check alerts on their phones; the dashboard must be responsive.
4. **Professional & Clean**: High-impact "Utility SaaS" aesthetic (inspired by clean, modern tools).

---

## 🏗️ Design System: Shadcn/UI + Tailwind

We use **Shadcn/UI** as the foundation, providing accessible, themeable components.

- **Primary Colors**: Nature-inspired (Forest Green, Slate, Earthy Orange).
- **Typography**: Clean sans-serif (Inter or Geist).
- **Components** (installed and in use):
  - `badge.tsx` — For scan status indicators (Active/Paused/Ended)
  - `button.tsx` — Primary action buttons
  - `card.tsx` — Scan cards and dashboard stat cards
  - `dialog.tsx` — Scan creation form (`ScanForm.tsx`)
  - `dropdown-menu.tsx` — User menu in header
  - `input.tsx` — Form inputs
  - `label.tsx` — Form labels
  - `switch.tsx` — Scan active/paused toggle
- **Icons**: `lucide-react` for all UI icons.

---

## 🛤️ User Journey Map (Implemented)

### 1. Landing & Authentication

- **Hero**: `Home.tsx` landing page with campground search via `SearchBar.tsx`.
- **Authentication**: Two modes controlled by backend config:
  - _Local mode_ (default): auto-authenticated, no login required.
  - _Auth0 mode_: `Auth.tsx` handles OAuth redirect flow.
- **Optional invite-only access**: When enabled, the backend enforces `is_invited` for scan operations. `ProtectedRoute.tsx` shows `InviteOnly.tsx` for uninvited dashboard/scan-detail visitors. Profile access is still allowed.
- **Mode-aware navigation**: The owner selects authentication independently of the environment. `none` automatically logs in and hides sign-in, signup, and logout. `session` offers an in-app password form with HTTP-only cookie persistence and CSRF headers; no signup. `auth0` offers sign-in/signup and requests the API audience supplied by `/api/auth-config`. Marketing links follow these capabilities. Configuration failures show an error instead of selecting another login mode. HTTP Basic authentication is never used.

### 2. Main Dashboard (`/dashboard`)

- **Active Scans**: A responsive grid of `ScanCard` components showing monitoring tasks.
- **Stats**: Summary cards showing total scans, active count, and campsites found.
- **Settings Panel**: Toggle-able slide-down with Pushover key configuration.
- **Navigation**: `Header.tsx` shows "Dashboard" and auth controls for authenticated users.

### 3. Scan Creation Flow (Implemented)

1. **Find Park**: `SearchBar.tsx` or the campground search inside `ScanForm.tsx` dialog.
2. **Action**: Clicking "New Scan" opens the `ScanForm` dialog (`Dialog` component).
3. **Configure**: Select dates, minimum stay length, preferred campsite types (TENT/RV/CABIN/OTHER via toggle badges), and electric hookup requirement.
4. **Validation**: React Hook Form + Zod schema enforces date range validity (check-out after check-in) and field requirements.
5. **Save**: POST to `/api/scans` — on success, the scan list auto-refreshes via TanStack Query invalidation.

### 4. Scan Detail & History

- **ScanCard**: Shows campground name, rec area, dates, found count, filters (badges), last-checked time, and active/paused state.
- **Toggle**: Each scan card has a switch to pause/resume monitoring.
- **Edit**: Each scan card and detail page offers an edit action. `ScanForm` opens with saved campground, dates, and filters, sends PATCH, and refreshes list/detail queries on success. Cancel discards changes; reopening loads current saved values. Failed saves preserve the form and show an error. Suspended users can edit existing scans.
- **Delete**: Each scan card has an accessible delete button and confirmation dialog. Card controls sit outside the detail link. Confirmation awaits the request, disables repeat submissions while pending, and keeps failures visible in the dialog for retry; success refreshes the dashboard.
- **Detail View**: Clicking through from the dashboard is routed to a dedicated detail view.

### 5. Administration & Operations (`/admin/*`)

- **AdminRoute Guard**: Protects `/admin/*` routes, checking `user.is_admin`. Non-admin users are denied access.
- **Admin Overview (`/admin`)**: Top-level KPI stat cards (users, active scans, targets, 24h results) plus native usage trend charts (`AdminTrendsPanel`).
- **User Management (`/admin/users`, `/admin/users/:id`)**: Searchable user table, per-user scanning suspension toggle, scan list, and audit trail. Suspended users are clearly badged.
- **Scan Management (`/admin/scans`, `/admin/scans/:id`)**: System-wide scan table with status filter, active toggle, and links to target and owner details.
- **Target Detail (`/admin/targets/:id`)**: Shared target inspection displaying provider details, date ranges, and list of all subscribing user scans.
- **Operations & Health (`/admin/operations`)**: Worker status cards, queue depth, discovery run metadata, recent task execution stream (Valkey telemetry, auto-refreshed every 15s) with task detail dialog, and worker/API/provider performance trend graphs.
- **Audit Log (`/admin/audit`)**: Immutable log of administrative actions with timestamps, admin email, action type, target ID, and metadata inspector.

---

## 🔄 Frontend Architecture (Implemented)

- **Framework**: React 18 + TypeScript + Vite.
- **State Management**: **TanStack Query** (React Query) for server-state synchronization with auto-invalidation on mutations.
- **Form Handling**: **React Hook Form** + **Zod** for strict validation.
- **API Client**: Axios-based client in `frontend/src/lib/api.ts` with auto-generated TypeScript types via `codegen.ts`.
- **Routing**: **React Router** (v7) with nested routes in `App.tsx`.
- **Auth**: `AuthProvider` context wrapping the entire app in `main.tsx`.

### Key Files

| File                                        | Purpose                                                       |
| ------------------------------------------- | ------------------------------------------------------------- |
| `src/main.tsx`                              | Root render with `QueryClientProvider` and `ThemeProvider`    |
| `src/App.tsx`                               | Route definitions (root, dashboard, campgrounds, etc.)        |
| `src/lib/api.ts`                            | Axios HTTP client for all backend endpoints                   |
| `src/lib/structs.ts`                        | TypeScript interfaces matching backend Pydantic models        |
| `src/lib/codegen.ts`                        | OpenAPI → TypeScript codegen script                           |
| `src/hooks/useAuth.tsx`                     | Auth context provider (current user, login, sign-out)         |
| `src/hooks/useScans.ts`                     | TanStack Query hooks for scan CRUD                            |
| `src/hooks/useSearch.ts`                    | TanStack Query hook for campground search                     |
| `src/pages/Dashboard.tsx`                   | Scan management dashboard                                     |
| `src/pages/InviteOnly.tsx`                  | Optional invitation gate page                                 |
| `src/components/ScanCard.tsx`               | Individual scan status card                                   |
| `src/components/ScanForm.tsx`               | Dialog-based scan creation form                               |
| `src/components/AdminRoute.tsx`             | Administrator route authorization guard                       |
| `src/components/AdminNav.tsx`               | Administration tabbed sub-navigation                          |
| `src/components/admin/AdminTrendsPanel.tsx` | Reusable Recharts metrics visualization with accessible table |
| `src/pages/admin/AdminOverview.tsx`         | System overview KPIs and usage trend charts                   |
| `src/pages/admin/AdminUsers.tsx`            | User management and scanning suspension controls              |
| `src/pages/admin/AdminScans.tsx`            | System scan management and active status toggling             |
| `src/pages/admin/AdminOperations.tsx`       | Worker health, queue telemetry, and operational trend charts  |
| `src/pages/admin/AdminAudit.tsx`            | Immutable audit event log inspector                           |

---

## Admin terminology and chart labels

- **Scan setting** is the saved active/paused preference. **Eligible for checks** means active with the owner's scanning access enabled; it does not mean a check is currently running.
- **Scanning suspended** stops scans and new scan creation while preserving login and saved settings.
- A **shared target** is one provider, campground, and date range. Its linked-scan count counts scans, not distinct users. Dormant targets have no eligible scans; overdue targets are a subset of eligible targets.
- Charts and tables show readable series names, explicit units, and the browser's local time zone. Tooltips and table rows include full dates. Legends distinguish multiple monitoring sources; missing table measurements remain distinct from zero.
- Creation bars estimate counts over the preceding interval; rate charts show averages. Percentile descriptions explain the median, 95th percentile, and 99th percentile. Shared-target results may differ from a scan's personal preferences.

## 📱 Responsiveness Requirements

- **Mobile (< 640px)**: Single-column scan cards, simplified search, bottom navigation.
- **Desktop (> 1024px)**: Multi-column grid (up to 3 columns), detailed scan cards.
- Both views share the same component tree — grid layout adjusts via Tailwind `sm:`/`lg:` breakpoints.
