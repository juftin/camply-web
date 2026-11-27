import { Capacitor } from "@capacitor/core";
import { Preferences } from "@capacitor/preferences";

export const defaultMobileServerUrl = "https://camply.rocks/";
const storageKey = "camply-mobile-server";

export interface MobileServer {
  url: string;
  auth0ClientId: string;
}

let activeServer: MobileServer | null = null;

function normalizeServerUrl(value: string): string {
  const input = value.trim();
  const invalid =
    "Enter an HTTPS server URL without credentials, a query, or a fragment.";
  if (!/^https:\/\//i.test(input)) throw new Error(invalid);

  let url: URL;
  try {
    url = new URL(input);
  } catch {
    throw new Error(invalid);
  }
  if (
    url.hostname.includes("*") ||
    url.username ||
    url.password ||
    /[?#]/.test(url.href)
  ) {
    throw new Error(invalid);
  }

  url.pathname = `${url.pathname.replace(/\/+$/, "")}/`;
  return url.href;
}

export function getMobileServer(): MobileServer | null {
  return activeServer;
}

function readMobileServer(value: string | null): MobileServer | null {
  try {
    const saved = JSON.parse(value ?? "null");
    if (
      typeof saved?.url === "string" &&
      typeof saved.auth0ClientId === "string"
    ) {
      return {
        url: normalizeServerUrl(saved.url),
        auth0ClientId: saved.auth0ClientId.trim(),
      };
    }
  } catch {
    // Ignore invalid serialized preferences from previous builds.
  }
  return null;
}

export async function loadMobileServer(): Promise<MobileServer | null> {
  if (!Capacitor.isNativePlatform()) {
    activeServer = null;
    return null;
  }

  const { value } = await Preferences.get({ key: storageKey });
  let server = readMobileServer(value);
  if (value === null) {
    const legacy = readMobileServer(localStorage.getItem(storageKey));
    if (legacy) {
      server = await saveMobileServer(legacy.url, legacy.auth0ClientId);
      localStorage.removeItem(storageKey);
    }
  }
  activeServer = server ?? { url: defaultMobileServerUrl, auth0ClientId: "" };
  return activeServer;
}

export async function saveMobileServer(
  url: string,
  auth0ClientId: string,
): Promise<MobileServer> {
  const server = {
    url: normalizeServerUrl(url),
    auth0ClientId: auth0ClientId.trim(),
  };
  await Preferences.set({ key: storageKey, value: JSON.stringify(server) });
  return server;
}
