import { Browser } from "@capacitor/browser";
import { Capacitor } from "@capacitor/core";

export const mobileAuthCallback = "com.camply.mobile://auth/callback";

export function auth0BrowserOptions() {
  return Capacitor.isNativePlatform()
    ? { openUrl: (url: string) => Browser.open({ url }) }
    : {};
}
