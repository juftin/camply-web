# Android and iOS development

Build the Camply mobile client from the repository root. Capacitor packages the React app and connects to `https://camply.rocks` by default. You can build against the hosted service or select another HTTPS Camply deployment when the app runs.

## Shared prerequisites

Install Git, [go-task](https://taskfile.dev/installation/), and [Node.js](https://nodejs.org/en/download) 24 or newer. Use the pnpm version pinned in the root `package.json`. Enable the pnpm shim if you use Corepack, or install the pinned version directly. Then install the locked frontend dependencies from the repository root. [pnpm installation guide](https://pnpm.io/installation)

```sh
corepack enable pnpm
node --version
pnpm --version
task frontend:install
```

The Android and iOS projects are checked in. `task mobile:bundle` compiles the React app to `build/mobile/`. `task mobile:sync -- android` or `task mobile:sync -- ios` builds that bundle, copies it into the selected project, and updates native plugin references. Run sync again after changing React code or Capacitor plugins. Mobile builds use the frontend dependencies and the selected platform SDK. [Capacitor environment setup](https://capacitorjs.com/docs/getting-started/environment-setup)

## Build Android

Install Android Studio 2025.2.1 or newer for emulator and IDE workflows. The terminal build uses JDK 21, Android SDK Platform 36, Android SDK Build-Tools 35.0.0, and Android SDK Platform-Tools. Install these packages in Android Studio’s **Tools → SDK Manager**. For a headless build, install JDK 21 and Android SDK Command-Line Tools, then use `sdkmanager`. The repository Gradle wrapper downloads Gradle and resolves the native dependencies. [Android SDK command-line tools](https://developer.android.com/tools/sdkmanager)

Set `JAVA_HOME` to your JDK 21 directory and `ANDROID_HOME` to the Android SDK directory shown in SDK Manager. The usual SDK paths are `$HOME/Android/Sdk` on Linux and `$HOME/Library/Android/sdk` on macOS. These commands show the headless setup on Linux.

```sh
export JAVA_HOME=/path/to/jdk-21
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
java -version
sdkmanager --licenses
sdkmanager 'platform-tools' 'platforms;android-36' 'build-tools;35.0.0'
```

Build the debug APK from the repository root.

```sh
task mobile:android:debug
```

The APK is written to `src/mobile/android/app/build/outputs/apk/debug/app-debug.apk`. To run it, start an emulator in Android Studio’s **Device Manager**, or connect an Android device with USB debugging enabled. Android 7.0 (API 24) is the project’s minimum device version.

```sh
adb devices
task mobile:run -- android
```

You can install an existing debug APK with `adb install -r src/mobile/android/app/build/outputs/apk/debug/app-debug.apk`. For the IDE workflow, run `task mobile:sync -- android` followed by `task mobile:open -- android`. On Windows, run the wrapper from PowerShell after sync.

```powershell
.\src\mobile\android\gradlew.bat -p src/mobile/android :app:assembleDebug
```

### Sign an Android release

Set `versionCode` and `versionName` in `src/mobile/android/app/build.gradle` for the release. Run `task mobile:sync -- android` and `task mobile:open -- android`. In Android Studio, select **Build → Generate Signed Bundle / APK**, choose **Android App Bundle** for Google Play or **APK** for direct distribution, select your signing key and the `release` variant, then build to the output directory shown by the wizard. Store the keystore and its credentials outside the repository. [Android signing guide](https://developer.android.com/studio/publish/app-signing)

## Build iOS

Use macOS with Xcode 26 or newer. Install Xcode’s command-line tools and an iOS Simulator runtime. Open Xcode once to complete its setup, then check that `xcode-select -p` points to the full Xcode installation and `xcodebuild -version` reports Xcode 26 or newer. The project uses Xcode’s Swift Package Manager and targets iOS 15 or newer. [Xcode component and simulator setup](https://developer.apple.com/documentation/xcode/downloading-and-installing-additional-xcode-components)

Build and run on a simulator from the repository root.

```sh
task mobile:run -- ios
```

To compile a simulator `.app` without launching it, sync and build the `App` scheme.

```sh
task mobile:sync -- ios
xcodebuild -project src/mobile/ios/App/App.xcodeproj \
  -scheme App -configuration Debug -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath build/mobile-ios CODE_SIGNING_ALLOWED=NO build
```

The simulator app is written to `build/mobile-ios/Build/Products/Debug-iphonesimulator/App.app`. Use `task mobile:open -- ios` to open the synced project in Xcode. To run on a physical iPhone, enable Developer Mode on the device, select it as the destination, and choose your Apple development team under the `App` target’s **Signing & Capabilities**.

### Archive and sign an iOS release

Use an Apple Developer Program team with access to the app’s bundle ID. Sync the bundle and open the project.

```sh
task mobile:sync -- ios
task mobile:open -- ios
```

Set the app’s Version and Build in the `App` target’s **General** tab and choose the team under **Signing & Capabilities**. Select a generic iOS device destination and choose **Product → Archive**. In Organizer, select **Distribute App** to upload to App Store Connect or export an `.ipa` with the appropriate distribution profile. [Apple’s distribution guide](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases)

## Choose a server

Open **Server settings** in the app and enter the Camply web URL, including any path prefix. The app resolves `/api` beneath that URL. Select **Connect** to save the choice in native device preferences and start a fresh app session. Settings are available from the navigation menu and on connection or sign-in errors. After a connection failure, select **Try again** to reconnect to the current server. To restore the default, select **Use camply.rocks**, then **Connect**.

## Deployment settings

Deploy the updated Camply backend to enable native password sign-in. The API permits the exact WebView origins `https://localhost` (Android) and `capacitor://localhost` (iOS) alongside configured web origins. If a reverse proxy handles CORS, allow both origins and forward the login request and response headers. Older password-session deployments offer browser sign-in. Do not expose an automatic-login backend publicly to enable mobile access.

Password sessions use an in-memory bearer in the app. Sign in again after restarting the app or switching servers. Password changes rotate the app credential, and logout or session revocation invalidates it on the server. See the [API contract](../architecture/DESIGN_API.md#authentication-modes).

For Auth0, create a public **Native** application on the same tenant as the deployment's SPA. Set its token endpoint authentication method to **None** and set both Allowed Callback URLs and Allowed Logout URLs to `com.camply.mobile://auth/callback`. Add the two WebView origins under Allowed Origins (CORS), then enable refresh token rotation for the native client and offline access for the API audience. In **Server settings**, open **Auth0 options** and enter that public client ID. A build can also supply `VITE_MOBILE_AUTH0_CLIENT_ID` for the default `camply.rocks` deployment. Tokens stay in memory, so reopening the app after the operating system terminates it requires sign-in again. See the [Auth0 Capacitor guide](https://auth0.com/docs/quickstart/native/ionic-react).

Before store distribution, verify sign-in, sign-out, scan browsing, booking links, and safe areas in signed builds on physical Android and iOS devices. Server-sent APNs/FCM alerts and opening the matching scan from an alert are tracked in the [mobile specification](../specs/036-capacitor-mobile/tasks.md). Existing server notification channels can deliver alerts while the app is closed.
