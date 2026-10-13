# Campsite experience research

Status: planning and research only. Repository re-audited October 12, 2026
against `main` at `f17106f`.

## Method and limitations

Reviewed camply's frontend components, API schemas/routers, polling/notification
implementation, and current UI snapshots. The snapshots use synthetic component
fixtures, not live provider or delivery validation. Source findings identify
implementation gaps; recommendations are design hypotheses pending hands-on
accessibility review and camper usability testing.

## Interaction hypotheses to validate

| Pattern                                       | Proposed application to camply                                                                       |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Destination search and useful starting points | Improve existing search and add supported suggestions; geographic exploration follows a usable list. |
| Relevant date/stay explanations               | Explain consecutive-night matching beside existing date and minimum-stay controls.                   |
| Optional refinement and clear booking handoff | Keep guidance in the existing alert dialog and link to the official reservation provider.            |
| Understandable scan summaries and actions     | Show what is watched, monitoring eligibility, and available actions in existing cards.               |
| User-defined scan names                       | Consider trip names after core management works; persisted metadata is required.                     |
| Exact stays and flexible windows              | Explain both rules through the current date-window/minimum fields and inline summary.                |

The source audit points to discoverability, understandable choices, and visible
monitoring state as useful starting points. Preserve camply's current visual
identity, familiar layouts, and free, open-source, self-hostable product direction.

## Current repository baseline

The implementation baseline includes these merged changes. Treat them as existing
capabilities to preserve, not additional implementation tasks in this plan.

| Upstream change                                                          | Existing behavior                                                                                                                                           | Effect on this plan                                                                                                                                              |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UI snapshots (#42), copy tweaks (#43)                                    | `DevPreview`, committed light/dark/mobile baselines, `task snapshot`, `snapshot:update`, and `snapshot:check`.                                              | Use actual component snapshots as the visual baseline; standalone wireframes illustrate additions only. Preserve current copy except specific misleading claims. |
| Authentication/invitations (#45), session deployment fixes (#47/#49/#50) | Owner-selected `none`, `session`, or `auth0`; capability-aware navigation; in-app cookie login/CSRF; same-origin Pages proxy; protected invite-only routes. | Reuse auth config, account links, session transport, and route guards. Draft return/recovery remains new work; HTTP Basic is no longer supported.                |
| Development/Compose workflows (#46)                                      | Network-accessible development, Task-based Compose lifecycle, corrected Docker builds.                                                                      | Use current Task workflows; this feature requires no deployment redesign.                                                                                        |
| Frontend performance (#48)                                               | Pinned pnpm, Node 24+, Oxlint/Oxfmt, Vite 8, Vitest 5, native TypeScript 7.                                                                                 | Use repository tasks and current tooling; no npm/ESLint/Prettier migration work remains.                                                                         |
| Native admin monitoring (#44)                                            | Guarded `/admin/*`, audited management, scanning suspension, operational telemetry/Prometheus trends, generated admin contracts and `task api:check`.       | Preserve admin navigation/authorization and effective scan eligibility. Admin monitoring is not a camper notification history or a public health endpoint.       |

## Current camply journey: findings from source

| Area and evidence                                                                                                          | Current finding                                                                                                                                                                                                              | Remaining product work                                                                                                                                              |
| -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `frontend/src/pages/Home.tsx`, `Header.tsx`                                                                                | CTA uses `accountPath`; sign-in/signup visibility follows `autoLogin`/`signupEnabled`; Admin entry is role-gated. Static coverage/channel claims and missing suggestions remain.                                             | Keep current header and auth-aware actions; add suggestions and correct only unsupported claims.                                                                    |
| `frontend/src/components/SearchBar.tsx`, `SearchDropdown.tsx`, `hooks/useSearch.ts`                                        | Debounced search retains previous data; no combobox/listbox semantics; Escape requires nonempty results; Enter requires arrow selection.                                                                                     | Prevent old-query selection and provide accessible, predictable keyboard/retry behavior.                                                                            |
| `frontend/src/pages/RecreationArea.tsx`                                                                                    | Unfiltered campground list, clickable-div navigation, no connected map/list selection.                                                                                                                                       | Add name filter/counts and semantic links inside current cards.                                                                                                     |
| `frontend/src/pages/Campground.tsx`                                                                                        | Existing Monitor action and description/map layout; no clear reservation handoff or readiness summary.                                                                                                                       | Clarify the existing action and add the provider URL without page replacement.                                                                                      |
| `frontend/src/components/ScanForm.tsx`                                                                                     | Search is separate/un-debounced; internal IDs and clickable badges remain; minimum/window validation is incomplete. Suspension warning disables submission.                                                                  | Enhance the single dialog, preserve suspension checks, share accessible search, show matching rule and readiness.                                                   |
| `frontend/src/pages/Auth.tsx`, `App.tsx`, `components/ProtectedRoute.tsx`, `pages/InviteOnly.tsx`                          | Session/Auth0 sign-in still returns to Dashboard; no campground draft return. Invite-only guards protect dashboard/details; Profile stays reachable. Invite request collection provides no approval/delivery flow.           | Restore safe drafts through existing sign-in and invitation states. Preserve guards; do not promise invitation emails or automatic approval.                        |
| `frontend/src/pages/Dashboard.tsx`, `ScanCard.tsx`                                                                         | Resume/toggle failures now show `actionError`, including suspended-account refusal. Delete failures remain undisplayed. Stats count the loaded page; card controls remain nested in a Link; Ended/Active badges may coexist. | Keep existing resume feedback. Add deletion recovery and per-card pending/errors; repair link semantics, pagination/counts, and state wording.                      |
| `frontend/src/pages/ScanDetail.tsx`                                                                                        | Results remain date badges without booking action; scan queries avoid retries on 401/403.                                                                                                                                    | Add matching night blocks/freshness/provider URL; reuse existing auth-error handling.                                                                               |
| `frontend/src/components/MapComponent.tsx`                                                                                 | Map assumes a key; coordinate checks use truthiness; markers do not navigate.                                                                                                                                                | Preserve list fallback and valid zero coordinates; full geographic browsing stays later work.                                                                       |
| `backend/.../schemas.py`, `routers/scans.py`                                                                               | One campground/window per scan; PATCH edits filters/active flag, not dates; duplicates return 409. Server rejects suspended create/resume and enforces invitation policy. Date/window consistency remains incomplete.        | Preserve ownership/invitation/suspension checks while adding date validation or retargeting.                                                                        |
| `backend/.../routers/scans.py`, `worker/tasks/scanner.py`                                                                  | Result serialization/counts still use shared snapshots without user filters; snapshots replace previous availability.                                                                                                        | Align results with personal requirements; do not call shared observations matching stays or notification history.                                                   |
| `backend/packages/providers/providers/recreation_gov/provider.py`                                                          | Extraction still includes `start_date <= date <= end_date`, while UI says checkout.                                                                                                                                          | Resolve exclusive departure and existing saved-date compatibility before exact-stay claims.                                                                         |
| `backend/packages/db/db/eligibility.py`, `worker/tasks/scanner.py`, `worker/tasks/notifications.py`                        | Effective eligibility requires `scanning_enabled && is_active`; suspension preserves saved scan settings and prevents polling/delivery. Notifications recheck scan ownership/active state.                                   | Distinguish a saved Active setting from eligibility. Suspended users can view saved data, pause/edit/delete, and configure notifications, but cannot create/resume. |
| `backend/packages/backend/backend/routers/admin.py`, `services/operations.py`, `services/trends.py`, `worker/telemetry.py` | Admin-only operations, task outcomes, partial/stale states, trends and audit exist; Grafana is replaced.                                                                                                                     | Reuse available signals via an ownership-safe camper projection if needed. Do not expose admin endpoints or treat telemetry as device-delivery proof.               |
| Provider registry, Providers page, Pushover task/provider                                                                  | Recreation.gov/Pushover are reviewed implementations; static integration claims exceed that support. A saved user key is not a delivery test; missing host token is still a separate failure.                                | Accurate claims and real delivery readiness/test endpoint remain work.                                                                                              |

Paths abbreviated with `backend/...` refer to `backend/packages/backend/backend`.
Findings are source-level observations, not claims of reproduced production incidents.

## Technical feasibility boundaries

Existing public APIs support name search, provider metadata, recreation-area
metadata/lists, and campground details. Existing authenticated APIs support one
campground per scan, scan snapshots, filter/pause edits, deletion, and saving a
Pushover user key. Campground details include an official booking URL.

Missing contracts include geographic/state/date search filters, search pagination,
provider capability summaries, photos/amenities/equipment metadata, favorites,
trip groups, date edits, verified delivery/test status, owner-visible monitoring error details,
owner-visible notification history, and user-confirmed booking outcomes. Admin
operations/telemetry contracts now exist, but ordinary scan responses still expose
only `last_checked_at`, not a complete monitoring/delivery state. Broad filter categories
and map inventories should not be simulated by filtering only 20 text-search hits.

## Accessibility and notification references

- Use the [W3C combobox pattern](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/)
  as a reference for search behavior and focus relationships.
- Use the [W3C modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
  for builder focus management; a custom calendar also requires dedicated keyboard
  interaction and assistive-technology testing.
- Aim for 44px touch targets as a camply design choice. The [WCAG 2.2 minimum target
  criterion](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)
  uses 24px with exceptions; do not conflate those values.
- [Pushover licensing](https://pushover.net/licensing) describes a paid client
  license after its trial. Explain third-party costs before setup; avoid presenting
  the complete notification journey as cost-free unless another channel exists.

## Research still needed

The follow-up [implementation brief](implementation.md) checks notification-test
semantics against [Pushover's API](https://pushover.net/api): destination validation,
provider acceptance, and user-confirmed receipt are separate states. The
[design review](design-review.md) documents current-theme constraints and proposed
availability previews, arrival weekdays, comparisons, and grouped notifications.
These are planning/design findings, not a completed camper usability study.

1. Walk camply's current flows on mobile and desktop with authorized test accounts;
   record search, date-selection, notification setup, and error recovery screens.
2. Observe 5–8 campers completing camply discovery/alert tasks, including beginners,
   RV users, a flexible-weekend camper, and someone using keyboard/screen reader.
3. Verify actual provider metadata, refresh intervals, closures, and reservation
   boundaries with synthetic fixtures and recorded provider responses.
4. Establish completion-time, abandonment, and comprehension baselines before
   measuring improvements. Recruiting/accounts are not part of this session.
