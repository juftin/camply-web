import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, delimiter } from "node:path";
import { spawnSync } from "node:child_process";
import { androidEnvironment } from "./android-env.mjs";

function installation(t) {
  const root = mkdtempSync(join(tmpdir(), "camply-android-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const java = join(root, "Java Home");
  mkdirSync(java);
  writeFileSync(join(java, "release"), 'JAVA_VERSION="21.0.9"\n');
  const sdk = join(root, "Android SDK");
  mkdirSync(join(sdk, "ndk", "29.0.1"), { recursive: true });
  mkdirSync(join(sdk, "ndk", "30.0.16248370"));
  mkdirSync(join(sdk, "ndk", "31.0.1-beta"));
  return { root, java, sdk };
}

test("selects JDK 21 and latest stable NDK, preserving spaces and PATH", (t) => {
  const { java, sdk } = installation(t);
  const env = androidEnvironment({
    JAVA_HOME: java,
    ANDROID_HOME: sdk,
    PATH: "/existing",
  });
  assert.equal(env.JAVA_HOME, java);
  assert.equal(env.ANDROID_HOME, sdk);
  assert.equal(env.NDK_HOME, join(sdk, "ndk", "30.0.16248370"));
  assert.equal(
    env.PATH,
    [join(java, "bin"), join(sdk, "platform-tools"), "/existing"].join(
      delimiter,
    ),
  );
});

test("preserves an explicitly selected installed NDK", (t) => {
  const { java, sdk } = installation(t);
  const ndk = join(sdk, "ndk", "29.0.1");
  assert.equal(
    androidEnvironment({ JAVA_HOME: java, ANDROID_HOME: sdk, NDK_HOME: ndk })
      .NDK_HOME,
    ndk,
  );
  assert.throws(
    () =>
      androidEnvironment({
        JAVA_HOME: java,
        ANDROID_HOME: sdk,
        NDK_HOME: "/missing-ndk",
      }),
    /NDK_HOME/,
  );
});

test("reports missing SDK or NDK instead of launching Gradle", (t) => {
  const { java, sdk } = installation(t);
  assert.throws(
    () => androidEnvironment({ JAVA_HOME: java, ANDROID_HOME: "/missing-sdk" }),
    /ANDROID_HOME/,
  );
  rmSync(join(sdk, "ndk"), { recursive: true });
  assert.throws(
    () => androidEnvironment({ JAVA_HOME: java, ANDROID_HOME: sdk }),
    /NDK/,
  );
});

test("uses the standard macOS and Linux SDK paths", (t) => {
  const { root, java } = installation(t);
  for (const [platform, relative] of [
    ["darwin", "Library/Android/sdk"],
    ["linux", "Android/Sdk"],
  ]) {
    const sdk = join(root, relative);
    mkdirSync(join(sdk, "ndk", "30.0.1"), { recursive: true });
    assert.equal(
      androidEnvironment({ HOME: root, JAVA_HOME: java }, platform)
        .ANDROID_HOME,
      sdk,
    );
  }
});

test("Android tasks override inherited Java 27 and forward CLI arguments", (t) => {
  const { root, java, sdk } = installation(t);
  const bin = join(root, "bin");
  mkdirSync(bin);
  writeFileSync(
    join(bin, "pnpm"),
    "#!/bin/sh\nexec node -e 'console.log(JSON.stringify({args:process.argv.slice(1),java:process.env.JAVA_HOME,sdk:process.env.ANDROID_HOME,ndk:process.env.NDK_HOME,path:process.env.PATH}))' -- \"$@\"\n",
    { mode: 0o755 },
  );
  const toolchain = {
    JAVA_HOME: java,
    ANDROID_HOME: sdk,
    NDK_HOME: join(sdk, "ndk", "30.0.16248370"),
    PATH: `${bin}${delimiter}${process.env.PATH}`,
  };
  writeFileSync(
    join(bin, "node"),
    `#!${process.execPath}\nconst { spawnSync } = require("node:child_process");\nif (process.argv[2]?.endsWith("/android-env.mjs")) console.log(${JSON.stringify(JSON.stringify(toolchain))});\nelse { const child = spawnSync(${JSON.stringify(process.execPath)}, process.argv.slice(2), { stdio: "inherit" }); process.exit(child.status ?? 1); }\n`,
    { mode: 0o755 },
  );
  for (const action of ["init", "dev", "build"]) {
    const result = spawnSync(
      "task",
      [`mobile:android:${action}`, "--", "--verbose"],
      {
        cwd: resolve(import.meta.dirname, "../../.."),
        env: {
          ...process.env,
          JAVA_HOME: "/java27",
          PATH: toolchain.PATH,
          CAMPLY_MOBILE_URL: "https://camply.example.com",
        },
        encoding: "utf8",
      },
    );
    assert.equal(result.status, 0, result.stderr);
    const received = JSON.parse(result.stdout.trim());
    assert.equal(received.java, java);
    assert.equal(received.sdk, sdk);
    assert.equal(received.ndk, toolchain.NDK_HOME);
    assert.equal(received.path, toolchain.PATH);
    assert.deepEqual(received.args, [
      "exec",
      "tauri",
      "android",
      action,
      "--config",
      "build/mobile/tauri.remote.json",
      "--verbose",
    ]);
  }
});

test("Java 27 is never selected for Android builds", (t) => {
  const { java, sdk } = installation(t);
  writeFileSync(join(java, "release"), 'JAVA_VERSION="27"\n');
  let selected;
  try {
    selected = androidEnvironment({ JAVA_HOME: java, ANDROID_HOME: sdk });
  } catch (error) {
    assert.match(error.message, /require JDK 21/);
    return;
  }
  assert.notEqual(selected.JAVA_HOME, java);
});
