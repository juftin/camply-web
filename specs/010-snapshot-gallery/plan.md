# Implementation plan

1. Extract screenshot comparison/report generation from the capture runner into a testable module; retain existing thresholds and Markdown output.
2. Add a permanent HTML template with before/after, slider, diff and search/status controls. Embed PNGs and safe JSON for portable local reports.
3. Compare and embed the previous baseline before overwriting it during updates; preserve normal check exit behavior. Add `task snapshot:report` for existing captures.
4. Treat generated HTML as a local/CI artifact, document the workflow, and update the feature checklist.
5. Verify synthetic unit regressions, local-file browser interactions, existing snapshot capture/check workflows, formatting, lint, types and tests.

Constitution check: no app routes, services, dependencies or production configuration changes. Reuse existing PNG/pixelmatch tooling, accessible native controls, and Task workflows. This feature has its own branch and PR, independent of campsite alerts.
