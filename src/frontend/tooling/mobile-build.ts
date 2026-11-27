export function mobileApiUrl(deployment: string | undefined): string {
  const url =
    deployment && /^https:\/\//i.test(deployment)
      ? URL.parse(deployment)
      : null;
  if (
    !url ||
    url.hostname.includes("*") ||
    url.username ||
    url.password ||
    url.href.includes("?") ||
    url.href.includes("#")
  ) {
    throw new Error(
      "Set CAMPLY_MOBILE_URL to the Camply HTTPS app URL without credentials, a query, or a fragment.",
    );
  }

  url.pathname = `${url.pathname.replace(/\/+$/, "")}/api`;
  return url.href;
}
