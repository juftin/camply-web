# Implementation plan

Use Tauri 2 with the official notification plugin and a mobile library entrypoint. Generate a checkout-local config overlay from CAMPLY_MOBILE_URL, binding both the WebView URL and remote capability to the same HTTPS origin. No native shell or filesystem capabilities. Reuse the hosted React frontend rather than creating a second UI or cross-origin authentication scheme.

Add an opt-in React notification controller inside the authenticated layout. TanStack Query polls all active user scans and their detail results while visible. Compare campsite/date keys against the preceding successful snapshot; suppress the initial snapshot and unchanged results. Account changes reset the baseline. Display permission and delivery errors. Keep notification body text private (campground only, no credentials).

Constitution review: Python and frontend boundaries preserved, no API contract or schema changes, strict TypeScript, task entrypoints, unit coverage for config and notification diff behavior. Native builds require Android SDK/NDK or macOS/Xcode, and real-device notification verification remains required.

The native Rust application, icons, and mobile config tooling live in `src/tauri/`. Mobile tasks explicitly select that directory with `TAURI_APP_PATH` and preserve the root frontend manifest through `TAURI_FRONTEND_PATH`.

Android environment fix: resolve a JDK 21 from JAVA_HOME, Android Studio's bundled JBR, or macOS java_home; resolve the standard platform SDK directory and latest stable installed NDK unless explicitly overridden. A shared internal Android task exports these paths using the env command, because inherited shell variables take precedence over Taskfile env entries. Verify selection and all three public Android commands with synthetic toolchains and a fake pnpm executable.
