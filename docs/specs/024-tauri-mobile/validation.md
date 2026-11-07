# Validation

- Frontend Vitest suite: 38 files, 354 tests passed, including 14 mobile notification permission, UI, delivery and opening-diff tests.
- Mobile config tests: 2 passed, including rejection of missing URLs, HTTP, credentials, wildcard hosts, paths, query strings and fragments.
- Frontend TypeScript check, Oxlint and repository Oxfmt check passed.
- Production standalone frontend and documentation build passed.
- `git diff --check` passed.
- Generated Android/iOS app icons from the existing Camply favicon.
- Cargo resolved and locked native dependencies. Native `cargo check` could not compile: workspace lacks the C linker `cc` and Linux WebKit development libraries.
- Android initialization could not proceed: workspace lacks Java/JAVA_HOME and the Android SDK. iOS compilation requires a macOS/Xcode host.

No signed APK, AAB or IPA has been produced or device-tested. Device validation and server-side APNs/FCM push remain unchecked in tasks.md. Local notifications only run while the frontend is active; server-side scanning is unaffected by phone suspension.

## Source layout verification

After moving the native application and config tooling to `src/tauri/`, `task mobile:configure`, all 16 mobile tests, repository frontend lint/format checks, Cargo metadata, and Tauri CLI project discovery passed. Native compilation still requires the platform toolchains noted above.
