# Validation Quickstart: Full Mobile-Responsive UI Audit & Polish

**Feature**: `034-mobile-responsive-audit`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Contract**: [responsive-ui-contract.md](contracts/responsive-ui-contract.md)

## Prerequisites

- Node >=24 and `pnpm` installed (`task frontend:install`)
- The project-locked Playwright Chromium build and its system libraries (`task frontend:browser:install`). Use the CI image's fonts locally to match baseline rendering.

## 1. Static Checks & Unit / Component Tests

Run formatting, linting, type checking, and the full Vitest suite:

```bash
task frontend:fix
task frontend:check
task frontend:lint
task frontend:test
```

**Expected outcomes**:

- Zero TypeScript (`tsc`), Oxlint, or Oxfmt errors or warnings.
- 100% of Vitest tests pass, including new tests for:
  - `Sheet` slide-over drawer and sticky `Header` mobile menu dismissal (`Layout.test.tsx` / `Header.test.tsx`)
  - Bounded `Dialog` + `DialogBody` + `DatePicker` mobile clamping (`date-picker.test.tsx`, `ScanForm.test.tsx`)
  - Hybrid mobile card views and interactions in `AdminUsers`, `AdminInvites`, and `AdminScans` (`AdminPages.test.tsx`, `AdminInvites.test.tsx`, `AdminInteractions.test.tsx`)

## 2. Automated Mobile Visual & Zero-Overflow Verification

Run the mobile and desktop visual comparisons, the 26-route overflow sweep, and the overlay matrix with local Chromium.

```bash
task frontend:browser:install
task frontend:snapshot -- --check --filter mobile
task frontend:snapshot -- --check --filter desktop
task frontend:snapshot -- --overflow-only
task frontend:snapshot -- --overlay-only
```

Review visual diffs in the comparison gallery. For an intentional change, replace the affected baseline with its reviewed capture or run `task frontend:snapshot -- --update --filter <scenario>` and repeat its check.

```bash
task snapshot:report
```

**Expected outcomes**:

- Every mobile scenario (`375×667`, `375×812`, `390×844`) and tablet check (`768×1024`) passes the automated `document.documentElement.scrollWidth <= window.innerWidth` assertion with zero violations.
- All newly added representative mobile baselines render cleanly with no clipped dialogs, truncated popovers, overlapping chart legends, or broken dark/light contrast.
- All existing desktop baselines (`1280×800`) pass with zero unintended diffs.

## 3. Manual / Dev-Server Smoke Checks (Spot Verification)

Start the frontend locally (`task frontend:dev`) and spot-check in browser device emulation:

1. **375×667 (Compact Phone)**:
   - Open the header menu mid-scroll → confirm sticky header, slide-over drawer with backdrop, Escape/backdrop close, and route-change reset.
   - Open Create Scan → scroll the dialog body while confirming header and Save/Cancel footer stay pinned; open Check-in and Check-out calendars and verify they remain inside the viewport.
   - Open Profile → verify long custom ntfy server URLs, copy buttons, and Active Sessions rows wrap cleanly.
2. **390×844 (Standard Phone) — Admin**:
   - Visit `/admin/users`, `/admin/invitations`, `/admin/scans` → confirm stacked mobile cards with comfortable action tap targets.
   - Visit `/admin`, `/admin/operations`, `/admin/audit`, and detail pages → confirm charts are legible and dense tables scroll inside contained wrappers without moving the whole page.
3. **768×1024 (Tablet Transition)**:
   - Confirm header navigation switches cleanly between mobile drawer and desktop links without wrapping or clipping.

## 4. Closing Artifacts

Before opening the PR:

- Confirm `docs/specs/034-mobile-responsive-audit/audit-report.md` records all 26 audited routes and resolutions (`FR-015` / `SC-007`).
- Mark `T4.1.6` complete in `docs/CHECKLIST.md` and Phase 4 Polish in `docs/PLAN.md`.
- Update `docs/architecture/DESIGN_FRONTEND.md` with the mobile navigation drawer, bounded dialog, and hybrid admin list patterns.
