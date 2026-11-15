# Validation guide: Nights of the week

## Prerequisites

Use the checkout's `task install` environment. No provider credentials are needed for synthetic tests. SQLite exercises the complete local migration chain; Docker is needed only for the existing PostgreSQL migration smoke.

## Automated checks

- `task backend:test -- tests/db tests/core tests/cli tests/server/routers/test_scans.py tests/server/routers/test_scan_editing.py tests/server/routers/test_scan_results.py tests/worker`
- `task frontend:test -- src/frontend/components/ScanForm.test.tsx src/frontend/components/ScanForm.dates.test.tsx src/frontend/components/ScanCard.test.tsx src/frontend/pages/ScanDetail.test.tsx`
- `task api:generate` then `task api:check`
- `task fix`, `task lint`, `task check`, `task test`
- `task backend:migration:test` when Docker is available.
- Update only affected scan creation/editing, dashboard card and detail snapshots through the existing `task frontend:snapshot:update` workflow; inspect the generated comparison gallery.

## User scenarios

1. Start the app with `task dev` or the existing standalone development workflow. Select a synthetic campground and June 1–September 1, 2027. Select Weekends and a two-night minimum. Save one scan: complete Friday/Saturday openings have Sunday checkout; midweek and isolated nights do not match.
2. Edit to Monday/Wednesday with one night: gaps create separate stays. Reload and reopen editing to see the saved selection. Cancel another edit and verify the prior values remain.
3. Choose Sunday/Monday with two nights: a consecutive cross-week stay qualifies. Choose Friday/Saturday with three nights: an actionable error prevents saving. Any night restores unrestricted matching.
4. Operate every night button and shortcut with keyboard focus and inspect a mobile viewport. Each selected state has an accessible name and pressed state.
5. Use two synthetic subscribers on identical campground dates with different weekdays: raw polling stays shared while results/counts/alerts differ. Change a selection before delivering a queued alert: newly excluded dates cannot be delivered.
6. Run `camply campsites --campground <id> --start-date 2027-06-01 --end-date 2027-09-01 --weekends --nights 2` against a supported test campground. Compare with the web scan; adding `--day Sunday` includes Sunday nights. The CLI remains an ongoing console search until canceled.

See [contracts](contracts/night-selection.md) for exact request/default/error behavior and [data model](data-model.md) for compatibility rules.

## Recorded verification — 2026-11-15

- `task fix`, `task lint`, and `task check`: passed, including import boundaries and both TypeScript projects.
- `task test`: passed. Backend: 1,737 passed / 24 environment-dependent skips; isolated packaging: 81 passed; frontend: 399 passed; Pages checks: 10 passed plus bundled Function/static/proxy HTTP verification. Release tests and production frontend/documentation builds also passed within this task.
- `task api:generate` and `task api:check`: passed; committed client types match the backend contract.
- Migration: populated SQLite upgrade/downgrade/re-upgrade, reopened persistence, full SQLite history, and PostgreSQL SQL generation passed. Live PostgreSQL smoke was not run because the Docker daemon is unavailable.
- Changed-file pre-commit hooks: all passed. The optional all-files run additionally encountered the pre-existing formatter/Helm-template parsing issue on files outside this feature; no unrelated Helm changes were made.
- Visuals: updated and inspected affected scan form/edit/detail/expanded-card baselines and DOM snapshots. New desktop/mobile keyboard-selection scenarios passed, then matched their baselines with `task frontend:snapshot:check -- --filter=scan-night-selection`. Browser checks assert accessible pressed states and viewport fit.
- Red/green evidence: initial shared-matcher regressions failed before implementation; worker regressions initially produced 18 failures; frontend selector tests failed on the missing Monday control. Final behavior suites pass.
- Convergence: the first audit added T022 for the exact single-scan summer-weekend scenario; it now verifies all 13 complete weekends, zero midweek/isolated-night sites, and consistent detail/list counts. Final audit covers all 12 functional requirements, six success criteria, three user stories and five constitution principles with no remaining buildable gaps.
