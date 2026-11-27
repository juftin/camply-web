import { useEffect, useRef, useState } from "react";
import { useAuth0, type AppState } from "@auth0/auth0-react";
import { App as NativeApp } from "@capacitor/app";
import { Browser } from "@capacitor/browser";

interface MobileAuthCallbackProps {
  redirectUri: string;
  onRedirect: (appState?: AppState) => void;
}

export function MobileAuthCallback({
  redirectUri,
  onRedirect,
}: MobileAuthCallbackProps) {
  const { handleRedirectCallback } = useAuth0();
  const [error, setError] = useState<string>();
  const handled = useRef<string>();

  useEffect(() => {
    let active = true;
    const handleUrl = async ({ url }: { url: string }) => {
      if (!active || url === handled.current) return;
      if (url.split(/[?#]/, 1)[0] !== redirectUri || url.includes("#")) return;
      const callback = new URL(url);
      handled.current = url;
      setError(undefined);

      try {
        if (
          callback.searchParams.has("code") ||
          callback.searchParams.has("error")
        ) {
          const result = await handleRedirectCallback(url);
          if (active)
            onRedirect("appState" in result ? result.appState : undefined);
        }
      } catch {
        if (active) setError("Could not finish signing in. Please try again.");
      } finally {
        await Browser.close().catch(() => {});
      }
    };

    const listener = NativeApp.addListener("appUrlOpen", handleUrl);
    void listener
      .then(() => NativeApp.getLaunchUrl())
      .then((launch) => launch && handleUrl(launch))
      .catch(() => {
        if (active)
          setError(
            "Could not listen for the sign-in callback. Please reopen Camply.",
          );
      });
    return () => {
      active = false;
      void listener.then((handle) => handle.remove()).catch(() => {});
    };
  }, [handleRedirectCallback, onRedirect, redirectUri]);

  return error ? (
    <p role="alert" className="p-4 text-center text-destructive">
      {error}
    </p>
  ) : null;
}
