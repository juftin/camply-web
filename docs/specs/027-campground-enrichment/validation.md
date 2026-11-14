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
