# Validation

- `task test`: 551 backend tests and 291 frontend tests passed; 12 opt-in backend tests skipped by the normal suite.
- `task lint` and `task check`: passed for backend and frontend.
- `task api:generate` and `task api:check`: regenerated Explore bounds inputs and verified contract parity.
- `task backend:maps:test-postgres`: passed against an isolated PostgreSQL catalog; viewport item/count/facet/pagination parity matches map queries.
- `CAMPLY_MAPS_SMOKE=1 task backend:test -- -c pyproject.toml packages/backend/tests/integration/test_maps_smoke.py -s`: passed against an isolated synthetic API and Chromium, including IP initialization, real pan/zoom list requests, history, pagination, provider-qualified monitoring, overlapping groups, map failures, touch, keyboard, themes, and static subpath builds.
- `CAMPLY_SNAPSHOT_PORT=5197 task snapshot:check`: all 69 visual scenarios matched, including desktop hover and mobile keyboard focus.
- Pre-commit hooks passed on changed files without installing repository hooks.

Browser evidence: Chromium 156.0.8078.4, macOS arm64 / Apple M1, SwiftShader, 5,000 synthetic matches. All 4,998 mappable places remained discoverable. IP initialization returned 130 nearby places; pan/zoom narrowed the list from 4,998 to 2,935. Initial map representation took 349 ms after list completion. Tiles and IP lookup were intercepted; no live user data or public tile traffic was used.

Visual coverage adds [desktop hover](../../../tests/frontend/snapshots/baselines/map-hover-desktop-light.png) and [mobile keyboard focus](../../../tests/frontend/snapshots/baselines/map-focus-mobile-dark.png), including an assertion that the mobile tooltip fits the viewport. Existing map and non-map scenarios remain in the complete snapshot gate. Local browser/query evidence is written to `frontend/tmp/maps-browser.json`, `frontend/tmp/maps-postgres.json`, and `frontend/tmp/maps-*.png`.

Continuous-motion regression: the previous implementation timed out while waiting for an Explore response during an unreleased drag. The fixed implementation streams camera changes through a 150 ms throttle, and the browser test now observes multiple list responses and verifies the rendered total before releasing the mouse. Unit regressions cover sustained movement and camera events without DOM event metadata. `task frontend:test`, `task lint`, `task check`, and the live API/Chromium smoke passed after the fix.
