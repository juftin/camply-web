# Implementation validation and convergence

**Date**: 2026-11-14. Implementation and local verification complete. External environment limits are recorded below rather than treated as successful checks.

## Spec Kit workflow

Completed clarification and scope decisions, detailed UI/UX design, data model, API contract, quickstart, requirements-quality checklist, dependency-ordered task generation, cross-artifact analysis, implementation, and convergence inspection. The reviewer-owned UX checklist remains available for user review; its unchecked markers do not mean implementation is missing, and the user explicitly authorized proceeding through implementation.

The final inspection covers 12 functional requirements, all three user stories, and the five project constitution principles. No unbuilt feature work remains within the recorded release scope. Native GoingToCamp media, Washington scraping, and dated UseDirect narrative harvesting remain explicitly deferred.

## Requirement coverage

| Requirements           | Implementation and verification evidence                                                                                                                              |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-001, FR-008         | Existing IDs/description columns and summary schemas retained; SQLite migration round trips and provider/type collision API tests                                     |
| FR-002, FR-007         | Typed photo snapshots, primary-first deduplication/cap, RIDB Asset-to-catalog association, original-photo handling, summary exclusion tests                           |
| FR-003, FR-010         | Provider-specific practical information, URL/signature validation, placeholder exclusion, distance-qualified amenities, source-scope tests                            |
| FR-004, FR-005, FR-012 | Last-successful snapshots, atomic attempt claims, seven-day freshness, one-hour cooldown, bounded batch continuation, CLI/worker dispatch and request-isolation tests |
| FR-006, FR-011         | Sanitized narratives/links, accessible dialogs, keyboard/focus handling, broken/all-broken images, own-versus-parent isolation, responsive theme scenarios            |
| FR-009                 | Recreation.gov, ten UseDirect deployments, and ReserveAmerica extensions; unsupported provider no-op                                                                  |

Convergence inspection confirmed retention for failed, incomplete, missing, or reclassified source destinations. Regression coverage also guards batch starvation, concurrent duplicate claims, cross-entity media association, alternate rendition duplication, malformed archives, and normal catalog merges.

## Verification outcomes

| Check                           | Result                                                                                                                                                                                             |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `task test`                     | Passed end to end: 17 release tests; 1,417 backend tests with 23 opt-in/environment skips; 81 installed-package tests; 370 frontend tests; 10 Pages tests and HTTP/proxy verification              |
| `task check`                    | Passed formatting, lint, six import-boundary contracts, MyPy, and TypeScript                                                                                                                       |
| `task lint`                     | Passed                                                                                                                                                                                             |
| `task api:check`                | Passed; generated declarations match the backend                                                                                                                                                   |
| `task docs:check`               | Passed build plus all three tooling/link tests                                                                                                                                                     |
| Pre-commit on changed/new files | Passed all applicable hooks                                                                                                                                                                        |
| Enriched visual scenarios       | All 10 new scenarios match local baselines; both changed mobile campground scenarios match and were inspected                                                                                      |
| Full visual suite               | 12 matching views and 76 differences against existing macOS baselines in this Linux workspace; see environment note below                                                                          |
| SQLite migration                | Prior-head upgrade, nullable defaults, retained JSON/catalog data, downgrade/re-upgrade, and reference checks passed                                                                               |
| PostgreSQL migration            | Offline PostgreSQL DDL compilation passed; live database check unavailable without Docker/local PostgreSQL                                                                                         |
| Public source parser            | Verified source taxonomy and photo coverage; full 100-destination enrichment parse measured at 8.01 seconds and approximately 85 MiB peak process RSS, retaining at most 12 photos per destination |

## Visual environment and release verification

CI runs the visual suite on `macos-latest`; this workspace is Linux. An isolated checkout of the unchanged base revision reproduced the same admin-page mismatch (1.92%). Its current PNG is byte-identical to this branch's PNG, SHA-256 `27f68aaebefe61882a689faadf5e202fc8499fab65f5fac74076ead12a036218`. The broad suite's mismatch must therefore not be reported as a fully passing visual gate or resolved by replacing unrelated baselines.

Only the ten new enriched baselines and the two mobile campground baselines affected by the accessibility/layout change were added/updated. Initial captures came from Linux; the PR follow-up below records their replacement with reviewed macOS captures.

The local Docker daemon is unavailable and no local PostgreSQL server is installed. PostgreSQL verification subsequently ran in PR CI as recorded below; no production database was touched. Provider availability and source-photo usage are not universal guarantees.

## PR CI follow-up

[PR #329](https://github.com/juftin/camply-web/pull/329), initial [CI run 43558073061](https://github.com/juftin/camply-web/actions/runs/43558073061), verified commit `a019076463942d44414a2fd2030a23a0d5672c7e`. All 25 nonvisual checks passed, including Python 3.11–3.14, Docker build, browser/live smoke checks, packaging, and deployment checks. The PostgreSQL search smoke fixture exercised upgrade to the new head, downgrade, and re-upgrade on an isolated PostgreSQL 17 container.

The macOS visual job reported 76 unchanged views and 12 differences: precisely the ten enrichment views and the two affected mobile campground views. Inspection of all 12 current captures and representative highlighted diffs confirmed platform font/emoji rendering and resulting text wrapping differences, with readable content, accessible gallery controls, and intact mobile layouts. The reviewed captures from [artifact 14099780376](https://github.com/juftin/camply-web/actions/runs/43558073061/artifacts/14099780376) replace those 12 baselines. Every prior artifact baseline was verified byte-for-byte against the committed version before replacement. No unrelated baseline or comparison threshold changed. A fresh PR CI run must confirm the updated baselines.

## Convergence result

**Converged for implemented feature scope:** the source, API, UI, persistence, and regression coverage satisfy the recorded behavior. Local tests and static checks pass, and live PostgreSQL verification passed in PR CI. Reviewed macOS visual baselines are updated; their independent CI confirmation follows the baseline-fix commit. The reviewer-owned UX checklist remains available for user review.

## Carousel and layout amendment (2026-11-14)

The requested UI amendment uses `embla-carousel-react` 8.6.0, the engine behind [shadcn/ui Carousel](https://ui.shadcn.com/docs/components/carousel), with existing shadcn buttons. Arrows overlay the left/right image edges in both the carousel and dialog; the photo count appears only in the opened dialog. Only captions appear below images; the credit line and “Photo source” link are omitted. Both destination pages place “Know before you go” after the overview/map, preserving the overview without a snapshot. No API, provider, database, or caching behavior changed.

| Check                                                 | Result                                                                                                                                                                         |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Test-first regressions                                | New carousel/title tests and both page-order tests failed against the original implementation before the changes                                                               |
| `task frontend:test`                                  | 39 files, 372 tests passed; covers navigation/wrapping, selected-photo focus, single/failed/all-failed images, source validation, destination reset, and overview preservation |
| `task frontend:check` / `task frontend:lint`          | Passed                                                                                                                                                                         |
| `task frontend:build:static`                          | Production app and bundled documentation built successfully                                                                                                                    |
| `task docs:check`                                     | Documentation build and all three documentation checks passed                                                                                                                  |
| `task frontend:snapshot:check -- --filter=enrichment` | All 10 affected views match updated local baselines                                                                                                                            |

Browser scenarios exercise the real Embla engine: overlaid-control geometry and one accessible slide, explicit navigation, desktop mouse dragging, mobile Chromium touch input, no accidental dialog after dragging, and keyboard/focus behavior in the full-screen viewer. Unit tests isolate Embla because jsdom does not supply browser layout. The swipe fixture moves beyond the half-slide snap boundary to avoid an ambiguous endpoint. Enriched captures paint the below-fold map before capture; a repeated check confirmed stable images.

Inspected all 10 updated views across campground/area pages, desktop/mobile, light/dark, and two photo dialogs. Only those 10 baselines changed. These amendment captures were produced on Linux; independent macOS CI confirmation remains a PR release check, as described in the visual environment notes above. The amended UI requirements and T027–T029 are complete, with the reviewer-owned UX checklist still available for user review.

Before opening the PR, `task fix`, `task lint`, `task check`, and the full `task test` passed: 17 release checks, 1,428 backend tests (23 environment-dependent skips), 81 packaging tests, 372 frontend tests, 10 Pages tests, and the Pages static/proxy HTTP checks. Pre-commit hooks passed for all changed files. The full macOS visual suite remains a CI check; only the ten affected views were rerun locally.

### Carousel PR CI follow-up

[PR #332](https://github.com/juftin/camply-web/pull/332), [initial CI run 43641711391](https://github.com/juftin/camply-web/actions/runs/43641711391), checked commit `752e94eddd0c39e5ba63f7e36060f85686d97db4`. The full macOS visual suite reported 78 unchanged views and differences only in the ten updated enrichment views. Inspection of all ten current images and representative highlighted diffs confirmed macOS font/emoji rendering and resulting text wrapping, with correctly placed overlay controls and visit information below the map. The browser gesture/geometry assertions completed successfully.

Replaced only those ten baselines with the reviewed macOS captures from [artifact 14131744760](https://github.com/juftin/camply-web/actions/runs/43641711391/artifacts/14131744760), after verifying each artifact's prior baseline byte-for-byte against the checked commit. Comparison thresholds and the 78 unrelated baselines remain unchanged. The baseline follow-up requires independent CI confirmation; runtime code is unchanged from the fully tested commit.

### Caption-only review refinements

The user subsequently requested removal of per-photo credit/source lines from both views and a count shown only after opening a photo. Updated unit assertions failed against the earlier UI, then passed with these display changes. The full frontend suite (372 tests), `task fix`, `task lint`, `task check`, the production build, and the ten browser scenarios were rerun. The browser assertions now check selection through accessible slide names and explicitly reject visible count or credit/source text in the page carousel. Captions and the opened viewer's count remain visible, and stored photo metadata is unchanged. The updated layout requires new macOS baselines.

The intermediate macOS check of commit `f64e3ff0f277a966780466363588f1374c82ba64` matched 87 of 88 views; the remaining difference was the auto-hiding header captured before it finished returning after the map scroll. The enriched scenario now waits for the header to reach the top before capture. This changes only screenshot timing, without changing comparison thresholds or product behavior.

[CI run 43643072704](https://github.com/juftin/camply-web/actions/runs/43643072704) exercised the refined UI at commit `581c8adc514b9bd78dd50fb5cbffe47ab1a9c026`: all browser assertions completed, 78 unrelated views matched, and the ten changed views reflected the requested removal of credit/source lines and the inline count. Reviewed all ten captures from [artifact 14132946312](https://github.com/juftin/camply-web/actions/runs/43643072704/artifacts/14132946312), verified each prior baseline against that commit, and replaced only those ten images. T031 is complete; independent confirmation of the final baselines follows in PR CI.

Verified the updated Many Glacier preview in a fresh, unauthenticated Chromium browser with real provider data: decoded all eight photos, checked carousel wrapping and full-screen navigation, checked selected-photo focus restoration and the visit-information order, and verified that count text is absent from the page carousel but present in the opened viewer, with no credit/source lines in either view. The screenshot and browser log were retained as local review evidence; no production data was changed.
