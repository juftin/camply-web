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

## Android toolchain environment regression

`task fix`, `task lint`, `task check`, and `task test` passed after adding explicit Android environment selection. The full run included 8 tooling/configuration tests, 17 release tests, 876 backend tests (24 skipped), 69 packaging tests, 354 frontend tests, and 10 Pages tests plus Pages artifact verification. The 14 focused notification tests also passed through `task mobile:test`.

Synthetic toolchains verify JDK 21 selection, rejection of Java 27, SDK/NDK overrides, standard macOS/Linux SDK paths, latest stable NDK selection, missing-installation errors, and environment/argument forwarding through all three Android Taskfile entrypoints. The Taskfile regression starts with an incompatible exported JAVA_HOME and paths containing spaces. CI runs these tooling tests without an Android installation. Gradle/APK compilation still requires an Android-equipped host.
