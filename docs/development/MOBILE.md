# Android and iOS development

The Capacitor client bundles the existing Camply React app. It connects to `https://camply.rocks` by default and opens the selected server’s documentation in the browser. The backend and scanning workers continue to run on the server.

## Build and run

Use the repository's Node and pnpm setup. Android builds use Android Studio, a JDK 21, and Android SDK Platform 36. iOS builds use macOS, Xcode 26 or newer, and Swift Package Manager. See the [Capacitor environment setup](https://capacitorjs.com/docs/getting-started/environment-setup).

```sh
task mobile:sync -- android
task mobile:android:debug
task mobile:run -- android

# On macOS
task mobile:sync -- ios
task mobile:open -- ios
```

`task mobile:bundle` writes the mobile assets to `build/mobile/`. `task mobile:sync` copies those assets into the native projects and updates plugin references. Use Android Studio or Xcode to configure the signing identity and produce release builds. The Android debug APK builds at `src/mobile/android/app/build/outputs/apk/debug/app-debug.apk`.

## Choose a server

Open **Server settings** in the app and enter the Camply web URL, including any path prefix. The app resolves `/api` beneath that URL. Select **Connect** to save the choice in native device preferences and start a fresh app session. Settings are available from the navigation menu and on connection or sign-in errors. To restore the default, select **Use camply.rocks**, then **Connect**.

## Deployment settings

Deploy the updated Camply backend to enable native password sign-in. The API permits the exact WebView origins `https://localhost` (Android) and `capacitor://localhost` (iOS) alongside configured web origins. If a reverse proxy handles CORS, allow both origins and forward the login request and response headers. Older password-session deployments offer browser sign-in. Do not expose an automatic-login backend publicly to enable mobile access.

Password sessions use an in-memory bearer in the app. Sign in again after restarting the app or switching servers. Password changes rotate the app credential, and logout or session revocation invalidates it on the server. See the [API contract](../architecture/DESIGN_API.md#authentication-modes).

For Auth0, create a public **Native** application on the same tenant as the deployment's SPA. Set its token endpoint authentication method to **None** and set both Allowed Callback URLs and Allowed Logout URLs to `com.camply.mobile://auth/callback`. Add the two WebView origins under Allowed Origins (CORS), then enable refresh token rotation for the native client and offline access for the API audience. In **Server settings**, open **Auth0 options** and enter that public client ID. A build can also supply `VITE_MOBILE_AUTH0_CLIENT_ID` for the default `camply.rocks` deployment. Tokens stay in memory, so reopening the app after the operating system terminates it requires sign-in again. See the [Auth0 Capacitor guide](https://auth0.com/docs/quickstart/native/ionic-react).

Before store distribution, verify sign-in, sign-out, scan browsing, booking links, and safe areas in signed builds on physical Android and iOS devices. Server-sent APNs/FCM alerts and opening the matching scan from an alert are tracked in the [mobile specification](../specs/036-capacitor-mobile/tasks.md). Existing server notification channels can deliver alerts while the app is closed.
