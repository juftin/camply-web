# Mobile-responsive UI audit

The 26 production routes below were exercised with Playwright at 375, 390, and 768 px. Mobile visual scenarios cover both themes and include 375 × 667 captures of the scan dialog and date pickers.

| Route                                     | Findings and remediation                                                                                                                                                 |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `/`                                       | Reduced the phone hero heading and bounded the scrollable search suggestions, with full-width rows and truncated long names. Added a view of the open navigation drawer. |
| `/search`                                 | Moved the filters below the search form on phones, spaced RV and pagination controls, and wrapped the selected map marker's actions.                                     |
| `/providers`                              | Provider cards stack on phones, with wrapping title and badge rows.                                                                                                      |
| `/how-it-works`                           | The process grid uses one column on phones, two at intermediate widths, and four on large screens.                                                                       |
| `/faq`                                    | Questions use full-width keyboard-accessible buttons with expanded state and room for wrapping.                                                                          |
| `/contact`                                | The form stacks on phones. The message field uses 16 px text and the submit action has a 44 px target.                                                                   |
| `/ethos`                                  | Reduced the hero heading on phones and retained stacked content cards.                                                                                                   |
| `/contribute`                             | Stacked dense link tiles on compact phones and allowed community callouts to wrap.                                                                                       |
| `/privacy`                                | Legal prose wraps long links and respects dark mode.                                                                                                                     |
| `/terms`                                  | Uses the same compact typography and link wrapping as the privacy page.                                                                                                  |
| `/auth`                                   | Sign-in inputs use 16 px mobile text. Submit actions and wrapped feedback fit the card width.                                                                            |
| `/invite-only`                            | Request and status actions remain full-width with 44 px mobile targets.                                                                                                  |
| `/dashboard`                              | Scan summaries wrap long destination names and badges. Create and Edit keep actions pinned and scroll their fields. Delete errors stay in the confirmation dialog.       |
| `/dashboard/scans/:scanId`                | Preserved the compact calendar and cards. The availability grid scrolls within its own viewport.                                                                         |
| `/profile`                                | Contained notification inputs and device names, and made copy, save, test, and revoke actions easier to tap.                                                             |
| `/campground/:providerId/:campgroundId`   | Wrapped the destination heading and provider row. The photo viewer stays inside the dynamic viewport.                                                                    |
| `/rec-area/:providerId/:recreationAreaId` | Wrapped campground names and badges. The coverage picker expands inside the scan form on phones.                                                                         |
| `/admin`                                  | Kept the KPI cards stacked on phones and gave trend legends space to wrap.                                                                                               |
| `/admin/users`                            | Mobile cards expose scanning, administrator, reset, and details actions. Create and Reset keep their actions pinned.                                                     |
| `/admin/users/:userId`                    | Wrapped email and ID values, stacked mobile metadata, contained the scans table, and bounded the password reset dialog.                                                  |
| `/admin/invitations`                      | Mobile cards expose review actions and timestamps, with wrapping status tabs.                                                                                            |
| `/admin/scans`                            | Mobile cards expose pause and resume, eligibility, and detail links. The existing API has no admin scan delete endpoint.                                                 |
| `/admin/scans/:scanId`                    | Stacked scan metadata on phones and contained the results table.                                                                                                         |
| `/admin/targets/:targetId`                | Stacked target metadata and kept subscribers in a separately scrollable table.                                                                                           |
| `/admin/operations`                       | Wrapped controls and chart legends, contained wide telemetry tables, and pinned the task detail dialog header and Done button.                                           |
| `/admin/audit`                            | Kept audit events in a self-contained horizontal scrolling region.                                                                                                       |

The first sweep identified 74 px of overflow in the shared admin header at 768 px. Compact tablet navigation and account controls resolved it across all nine admin routes.

## Verification

All 78 route and viewport combinations passed the overflow check. Frontend formatting, linting, type checking, and all 501 frontend tests passed. All 130 local visual captures matched their baselines after review and acceptance of the intentional changes.

Docker was unavailable in this workspace. Local Playwright used the Chromium build bundled with Playwright 1.65.1 and the fonts extracted from the pinned Playwright image. Desktop baseline changes cover the pinned dialogs and telemetry layout refinements.

## Convergence verification

Added mobile baselines for the app-owned signup screen, forced password change, and the Operations task-details dialog. The browser exercised the signup handoff, password validation, and the task dialog's Done action using synthetic data.

All 78 route-width checks and 67 overlay and control checks passed locally. The overlay checks covered both themes at 375, 390, and 768 px and a 360 px scan calendar smoke test. They verified pinned dialog actions, picker reachability, long destination and account values, reduced motion, and mobile touch targets.

The frontend suite passed 503 tests, along with formatting, linting, and type checking. All 66 mobile and 67 desktop visual captures matched their baselines locally. Admin scan cards retain pause, resume, and detail access. T024 is resolved within the existing frontend scope because the admin scan API has no delete operation.

The completed local visual comparisons and layout sweeps are the acceptance evidence for this audit. T4.1.6 and Phase 4 Polish are complete.

### Phase 10 verification

Home autocomplete uses the available visual viewport on phones and opens above the field when there is insufficient room below. Both touch checks passed at 375 × 667 and 390 × 844 with long synthetic result text and reduced motion. The updated mobile capture and existing desktop capture matched their baselines.

All 78 route-width combinations passed after the sweep began waiting for route-specific successful content. Regression fixtures rejected loading and error views at the expected URL and accepted successful content after it appeared. The frontend suite passed 503 tests.
