# Implementation plan

1. Extract screenshot comparison/report generation from the capture runner into a testable module; retain existing thresholds and Markdown output.
2. Add a permanent HTML template with before/after, slider, diff and search/status controls. Reference local PNGs using relative URLs and serialize safe comparison metadata.
3. Compare and save the previous baseline in `before/` before overwriting it during updates; preserve normal check exit behavior. Add `task snapshot:report` for existing captures.
4. Treat generated HTML as a local/CI artifact, document the workflow, and update the feature checklist.
5. Verify synthetic unit regressions, local-file browser interactions, existing snapshot capture/check workflows, formatting, lint, types and tests.

Constitution check: no app routes, services, dependencies or production configuration changes. Reuse existing PNG/pixelmatch tooling, accessible native controls, and Task workflows. This feature has its own branch and PR, independent of campsite alerts.

Navigation reliability follow-up: map routes use DOM readiness, loaded search results, rendered canvases and fixture markers instead of global network idleness. Preserve the intentional map-summary failure scenario. Verify with a synthetic browser page whose background request remains pending while results and map content render asynchronously; run this regression through the existing snapshot verification Task and CI job.
