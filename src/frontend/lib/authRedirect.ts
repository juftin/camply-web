/** Accept only same-origin app paths for post-login navigation. */
export function authReturnTo(value: string | null): string {
  if (!value?.startsWith("/")) return "/dashboard";
  try {
    const destination = new URL(value, window.location.origin);
    return destination.origin === window.location.origin
      ? destination.pathname + destination.search + destination.hash
      : "/dashboard";
  } catch {
    return "/dashboard";
  }
}
