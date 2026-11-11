# Tauri mobile client

Android and iOS users open the existing Camply frontend against their remote server and opt in to native campsite notifications. Python, database, workers, and scanning remain remote.

The app loads a deployment URL fixed at build time. Hosting the UI and API on the same origin preserves session cookies, CSRF, and existing Auth0 redirects. Only that trusted origin receives native notification permissions; arbitrary pages receive no native access. The deployed frontend must include this feature.

Local notifications report newly observed campsite/date results while the app is running. Mobile suspension prevents reliable background polling; terminated-app delivery requires a separate APNs/FCM integration. Existing server notification channels remain available for background alerts.

Acceptance: HTTPS origin validation, Android/iOS commands, permission granted/denied/error handling, no notifications in normal browsers, initial-result suppression, new-result detection and duplicate suppression, and unchanged web authentication.

Android builds must select JDK 21 rather than inheriting an unsupported shell Java version, export JAVA_HOME/ANDROID_HOME/NDK_HOME and put the selected Java and platform-tools on PATH. Existing SDK/NDK overrides are preserved. Missing toolchains must fail with actionable setup guidance. iOS and non-Android tasks must not require an Android installation.
