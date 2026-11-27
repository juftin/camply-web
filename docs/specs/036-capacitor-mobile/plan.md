# Implementation plan

Build the React app with Vite into `build/mobile`, with a fixed HTTPS API URL and a link to the documentation on the same deployment. Use Capacitor 8 with conventional Android Gradle and iOS Swift Package Manager projects. Commit editable native sources and ignore synced web assets. Keep the Python server and the existing web build independent of the native toolchains.

Use Auth0 React's existing Authorization Code with PKCE flow with a separate public native client ID, the Capacitor Browser plugin, and a verified callback route in the app. Keep tokens in memory and let the SDK validate OAuth state. Configure the Camply API and Auth0 to allow the exact WebView origins. Session deployments keep their same-site cookie protection and remain available in the browser.

The constitution permits this as a frontend target with no server contract changes. Test deployment URL handling, callback routing, and mobile-specific auth behavior, then verify the web suite and native project sync. Check the signed login and alert path on physical Android and iOS devices before release. Send future push from the existing server notification pipeline.
