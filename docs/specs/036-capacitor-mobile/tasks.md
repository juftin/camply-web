# Tasks

- [x] Test and isolate the mobile build target, its deployment URL, and the web build output.
- [x] Check in Android and iOS projects and wire build, sync, and local run tasks.
- [x] Test callback validation, Auth0 browser handoff, and cold-start handling with synthetic platform events.
- [x] Document mobile setup and supported deployment settings, then sync both projects and run automated checks.
- [x] Default to camply.rocks, persist server settings, and verify app restart and recovery when switching deployments.
- [x] Persist server settings in Capacitor Preferences and verify hydration, migration, and the iOS privacy manifest.
- [x] Test native password sign-in, credential isolation, revocation, rotation, and mobile CORS alongside the web flow.
- [x] Surface and test failed system-browser launches for Auth0 sign-in and sign-out.

## Release follow-up

- [ ] Deploy the updated API to the hosted password-session instance and verify physical-device sign-in.
- [ ] Before release, integrate server-sent APNs/FCM through the scan notification pipeline and route taps to the corresponding scan.
- [ ] Before release, verify signed builds, authentication, and push delivery with the app closed on physical Android and iOS devices.
