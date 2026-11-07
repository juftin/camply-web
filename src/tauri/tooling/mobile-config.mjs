import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

export function mobileConfig(value) {
  if (!value)
    throw new Error("Set CAMPLY_MOBILE_URL to your Camply HTTPS origin.");
  const url = new URL(value);
  if (
    url.protocol !== "https:" ||
    url.hostname.includes("*") ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash
  )
    throw new Error(
      "CAMPLY_MOBILE_URL must be an HTTPS origin without credentials, path, query, or fragment.",
    );
  return {
    build: { frontendDist: url.origin, devUrl: url.origin },
    app: {
      windows: [{ label: "main", title: "Camply", url: url.origin }],
      security: {
        capabilities: [
          {
            identifier: "camply-notifications",
            description:
              "Native notifications for the trusted Camply deployment only",
            windows: ["main"],
            local: false,
            remote: { urls: [`${url.origin}/*`] },
            permissions: [
              "notification:allow-is-permission-granted",
              "notification:allow-request-permission",
              "notification:allow-notify",
            ],
          },
        ],
      },
    },
  };
}

if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const config = mobileConfig(process.env.CAMPLY_MOBILE_URL);
  mkdirSync("build/mobile", { recursive: true });
  writeFileSync(
    "build/mobile/tauri.remote.json",
    `${JSON.stringify(config, null, 2)}\n`,
  );
}
