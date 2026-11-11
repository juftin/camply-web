import { existsSync, readFileSync, readdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { homedir } from "node:os";
import { join, delimiter, resolve } from "node:path";
import { fileURLToPath } from "node:url";

function isJdk21(directory) {
  if (!directory) return false;
  try {
    return /^JAVA_VERSION="21(?:[.\-+" ])/m.test(
      readFileSync(join(directory, "release"), "utf8"),
    );
  } catch {
    return false;
  }
}

export function androidEnvironment(
  env = process.env,
  platform = process.platform,
) {
  const home = env.HOME || homedir();
  const studioJava =
    platform === "darwin"
      ? "/Applications/Android Studio.app/Contents/jbr/Contents/Home"
      : "/opt/android-studio/jbr";
  let java = [env.JAVA_HOME, studioJava].find(isJdk21);
  if (!java && platform === "darwin") {
    try {
      const installed = execFileSync("/usr/libexec/java_home", ["-v", "21"], {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
      }).trim();
      if (isJdk21(installed)) java = installed;
    } catch {
      /* Report the required JDK below. */
    }
  }
  if (!java)
    throw new Error(
      "Android builds require JDK 21. Install JDK 21 or Android Studio with its JDK 21 JBR, and set JAVA_HOME to that JDK (Java 27 is unsupported).",
    );
  const sdk =
    env.ANDROID_HOME ||
    join(home, platform === "darwin" ? "Library/Android/sdk" : "Android/Sdk");
  if (!existsSync(sdk))
    throw new Error(
      "Android SDK not found. Install it in Android Studio's SDK Manager or set ANDROID_HOME.",
    );
  let ndk = env.NDK_HOME;
  if (!ndk) {
    const directory = join(sdk, "ndk");
    const versions = existsSync(directory)
      ? readdirSync(directory, { withFileTypes: true })
          .filter(
            (entry) =>
              entry.isDirectory() && /^\d+\.\d+\.\d+$/.test(entry.name),
          )
          .map((entry) => entry.name)
      : [];
    versions.sort((a, b) => a.localeCompare(b, "en", { numeric: true }));
    if (versions.length) ndk = join(directory, versions.at(-1));
  }
  if (!ndk || !existsSync(ndk))
    throw new Error(
      "Android NDK not found. Install NDK (Side by side) in Android Studio's SDK Manager or set NDK_HOME.",
    );
  return {
    JAVA_HOME: java,
    ANDROID_HOME: sdk,
    NDK_HOME: ndk,
    PATH: [join(java, "bin"), join(sdk, "platform-tools"), env.PATH || ""].join(
      delimiter,
    ),
  };
}

if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  try {
    console.log(JSON.stringify(androidEnvironment()));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
