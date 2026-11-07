# Implementation plan

Use Tauri 2 with the official notification plugin and a mobile library entrypoint. Generate a checkout-local config overlay from CAMPLY_MOBILE_URL, binding both the WebView URL and remote capability to the same HTTPS origin. No native shell or filesystem capabilities. Reuse the hosted React frontend rather than creating a second UI or cross-origin authentication scheme.

Add an opt-in React notification controller inside the authenticated layout. TanStack Query polls all active user scans and their detail results while visible. Compare campsite/date keys against the preceding successful snapshot; suppress the initial snapshot and unchanged results. Account changes reset the baseline. Display permission and delivery errors. Keep notification body text private (campground only, no credentials).

Constitution review: Python and frontend boundaries preserved, no API contract or schema changes, strict TypeScript, task entrypoints, unit coverage for config and notification diff behavior. Native builds require Android SDK/NDK or macOS/Xcode, and real-device notification verification remains required.
