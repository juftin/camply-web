# Implementation plan

Build the React app with Vite into `build/mobile`. Load the selected HTTPS deployment from Capacitor Preferences before the API client sends any requests. Migrate an existing WebView preference on first launch. Replace the WebView document on change, recreating the authentication state and React Query cache. Declare the Preferences API in the iOS privacy manifest. Use Capacitor 8 with Android Gradle and iOS Swift Package Manager projects.

Use Auth0 React's existing Authorization Code with PKCE flow with a separate public native client ID, the Capacitor Browser plugin, and a verified callback route. Surface browser launch errors and retain a retry for system-browser logout after the app session ends.

Reuse `/api/login`, `/api/change-password`, and server-side session records. An explicit native login header requests a bearer token from an exact WebView origin. Validate the bearer audience and keep tokens in memory. Retain cookie and CSRF enforcement for ordinary web requests and advertise support in `/api/auth-config`. The API allows the exact mobile origins in addition to configured web origins. There is no database migration. Test issuance, transport isolation, password rotation, revocation, and the unchanged web workflows. Check signed login and alert delivery on physical devices before release.
