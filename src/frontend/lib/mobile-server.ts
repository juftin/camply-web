import { Capacitor } from "@capacitor/core";

export const defaultMobileServerUrl = "https://camply.rocks/";
const storageKey = "camply-mobile-server";

export interface MobileServer {
  url: string;
  auth0ClientId: string;
}

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
  if (!Capacitor.isNativePlatform()) return null;

  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) ?? "null");
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
    // An unreadable preference should not prevent the app from starting.
  }
  return { url: defaultMobileServerUrl, auth0ClientId: "" };
}

export function saveMobileServer(
  url: string,
  auth0ClientId: string,
): MobileServer {
  const server = {
    url: normalizeServerUrl(url),
    auth0ClientId: auth0ClientId.trim(),
  };
  localStorage.setItem(storageKey, JSON.stringify(server));
  return server;
}
