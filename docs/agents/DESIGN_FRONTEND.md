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
    - *Local mode* (default): auto-authenticated, no login required.
    - *Auth0 mode*: `Auth.tsx` handles OAuth redirect flow.
- **Early Access Check**: Backend verifies `is_early_access_user` flag; unauthorized users are redirected to `EarlyAccess.tsx` (see `Dashboard.tsx` guard logic).

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
- **Delete**: Each scan card has a delete button (with confirmation via trash icon).
- **Detail View**: Clicking through from the dashboard is routed to a dedicated detail view.

---

## 🔄 Frontend Architecture (Implemented)

- **Framework**: React 18 + TypeScript + Vite.
- **State Management**: **TanStack Query** (React Query) for server-state synchronization with auto-invalidation on mutations.
- **Form Handling**: **React Hook Form** + **Zod** for strict validation.
- **API Client**: Axios-based client in `frontend/src/lib/api.ts` with auto-generated TypeScript types via `codegen.ts`.
- **Routing**: **React Router** (v7) with nested routes in `App.tsx`.
- **Auth**: `AuthProvider` context wrapping the entire app in `main.tsx`.

### Key Files

| File | Purpose |
|------|---------|
| `src/main.tsx` | Root render with `QueryClientProvider` and `ThemeProvider` |
| `src/App.tsx` | Route definitions (root, dashboard, campgrounds, etc.) |
| `src/lib/api.ts` | Axios HTTP client for all backend endpoints |
| `src/lib/structs.ts` | TypeScript interfaces matching backend Pydantic models |
| `src/lib/codegen.ts` | OpenAPI → TypeScript codegen script |
| `src/hooks/useAuth.tsx` | Auth context provider (current user, login, sign-out) |
| `src/hooks/useScans.ts` | TanStack Query hooks for scan CRUD |
| `src/hooks/useSearch.ts` | TanStack Query hook for campground search |
| `src/pages/Dashboard.tsx` | Scan management dashboard |
| `src/pages/EarlyAccess.tsx` | Early-access gate page |
| `src/components/ScanCard.tsx` | Individual scan status card |
| `src/components/ScanForm.tsx` | Dialog-based scan creation form |

---

## 📱 Responsiveness Requirements
- **Mobile (< 640px)**: Single-column scan cards, simplified search, bottom navigation.
- **Desktop (> 1024px)**: Multi-column grid (up to 3 columns), detailed scan cards.
- Both views share the same component tree — grid layout adjusts via Tailwind `sm:`/`lg:` breakpoints.
