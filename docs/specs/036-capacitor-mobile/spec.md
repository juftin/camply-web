# Capacitor mobile client

Campers can install a native Android or iOS build of the existing Camply web app. The mobile client defaults to `https://camply.rocks` and lets campers choose a different HTTPS Camply deployment on the device. The web build remains the primary product and ships through its existing workflows.

## Acceptance criteria

- Generate the mobile web bundle and sync it into versioned Android and iOS projects using repository tasks. Keep the ordinary browser output independent of mobile build settings.
- Persist the HTTPS server URL on the device. Support deployments at the domain root or below a path prefix. Make server settings reachable when the current deployment cannot be reached, and let users restore the hosted default.
- Start a fresh app session after switching servers. Keep authentication credentials and cached account data from the previous server out of requests to the new server.
- Auth0 users sign in and out through the system browser and can retry a failed browser launch. The bundled client also supports automatic login and password sign-in on compatible servers. Older password-session deployments offer browser sign-in.
- Native password sessions support expiration, revocation, and password changes. Web password sessions keep their existing cookie and CSRF requirements.
- Keep the app usable around device safe areas and permit links to booking sites to open in the browser.
- Track server-sent push and signed physical-device validation as release work. Existing server notifications remain available while the app is closed.
