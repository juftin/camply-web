import { useSyncExternalStore } from "react";

const compactViewport = "(max-width: 767.98px)";

function subscribe(onChange: () => void) {
  const media = window.matchMedia?.(compactViewport);
  media?.addEventListener("change", onChange);
  return () => media?.removeEventListener("change", onChange);
}

function isCompact() {
  return window.matchMedia?.(compactViewport)?.matches ?? false;
}

export function useCompactAdminList() {
  return useSyncExternalStore(subscribe, isCompact);
}
