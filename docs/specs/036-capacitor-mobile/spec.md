# Capacitor mobile client

Campers can install a native Android or iOS build of the existing Camply web app. The mobile build bundles the same React UI and uses a configured HTTPS Camply API. The web build remains the primary product and ships through its existing workflows.

## Acceptance criteria

- Generate the mobile web bundle and sync it into versioned Android and iOS projects using repository tasks. Keep the ordinary browser output independent of mobile build settings.
- Reject missing or invalid mobile deployment URLs at build time. Support HTTPS deployments hosted at the domain root or below a path prefix.
- Auth0 users sign in and out through the system browser and can return to the app through its registered callback. The bundled client can also use an automatic-login deployment. Show an explanation for cookie-session deployments, which require a separate native authentication design.
- Keep the app usable around device safe areas and permit links to booking sites to open in the browser.
- Track server-sent push and signed physical-device validation as release work. Existing server notifications remain available while the app is closed.
