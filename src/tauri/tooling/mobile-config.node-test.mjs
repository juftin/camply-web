import test from "node:test";
import assert from "node:assert/strict";
import { mobileConfig } from "./mobile-config.mjs";

test("requires an explicit trusted HTTPS origin", () => {
  for (const value of [
    undefined,
    "",
    "http://example.com",
    "https://*.example.com",
    "https://user:pass@example.com",
    "https://example.com/app",
    "https://example.com/?secret=1",
    "https://example.com/#x",
    "file:///etc/passwd",
    "garbage",
  ]) {
    assert.throws(() => mobileConfig(value));
  }
});

test("pins the WebView and minimum native permissions to the same origin", () => {
  const config = mobileConfig("https://camply.example:8443/");
  assert.equal(config.build.frontendDist, "https://camply.example:8443");
  assert.equal(config.app.windows[0].url, config.build.frontendDist);
  const capability = config.app.security.capabilities[0];
  assert.deepEqual(capability.remote.urls, ["https://camply.example:8443/*"]);
  assert.equal(capability.local, false);
  assert.deepEqual(capability.permissions, [
    "notification:allow-is-permission-granted",
    "notification:allow-request-permission",
    "notification:allow-notify",
  ]);
});
