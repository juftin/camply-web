interface ProxyContext {
  request: Request;
  env: { CAMPLY_API_ORIGIN?: string; CAMPLY_API_PROXY_SECRET?: string };
}

const proxySecretHeader = "X-Camply-Proxy-Secret";
const clientIpHeader = "X-Camply-Client-IP";

function apiError(status: number, detail: string): Response {
  return Response.json(
    { detail },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

function decodePath(path: string): string {
  try {
    return decodeURIComponent(path);
  } catch {
    return path;
  }
}

/** Keep API traffic and host-only session cookies on the Pages frontend origin. */
export async function onRequest({
  request,
  env,
}: ProxyContext): Promise<Response> {
  const frontend = new URL(request.url);
  const path = decodePath(frontend.pathname);
  if (/^\/+api\/+health\/*$/.test(path)) {
    return apiError(404, "Not found.");
  }
  const origin = request.headers.get("Origin");
  const fetchSite = request.headers.get("Sec-Fetch-Site");
  if (
    (origin !== null && origin !== frontend.origin) ||
    (fetchSite !== null && fetchSite !== "same-origin" && fetchSite !== "none")
  ) {
    return apiError(403, "Cross-origin API request denied.");
  }

  let upstream: URL;
  try {
    upstream = new URL(env.CAMPLY_API_ORIGIN ?? "");
    if (
      upstream.protocol !== "https:" ||
      upstream.origin === frontend.origin ||
      upstream.pathname !== "/" ||
      upstream.search ||
      upstream.hash ||
      upstream.username ||
      upstream.password
    ) {
      throw new Error("Invalid backend origin");
    }
  } catch {
    return apiError(
      503,
      "Configure CAMPLY_API_ORIGIN with the HTTPS backend origin.",
    );
  }

  const secret = env.CAMPLY_API_PROXY_SECRET;
  if (!secret || secret.length < 32 || /[^!-~]/.test(secret)) {
    return apiError(
      503,
      "Configure CAMPLY_API_PROXY_SECRET in the Pages runtime.",
    );
  }

  // Cloudflare supplies this on ingress and may rewrite it on the subrequest.
  const clientIp = request.headers.get("CF-Connecting-IP");
  if (!clientIp) {
    return apiError(
      503,
      "The API gateway could not identify the client network.",
    );
  }

  upstream.pathname = frontend.pathname;
  upstream.search = frontend.search;
  const forwarded = new Request(upstream, request);
  for (const header of [
    "Host",
    "Forwarded",
    "X-Forwarded-For",
    "X-Forwarded-Host",
    "X-Forwarded-Port",
    "X-Forwarded-Proto",
    "X-Real-IP",
    proxySecretHeader,
    clientIpHeader,
  ]) {
    forwarded.headers.delete(header);
  }
  if (path !== "/api/ping" || !["GET", "HEAD"].includes(request.method)) {
    forwarded.headers.set(proxySecretHeader, secret);
    forwarded.headers.set(clientIpHeader, clientIp);
  }

  try {
    const result = await fetch(forwarded, {
      redirect: "manual",
      cache: "no-store",
    });
    const response = new Response(result.body, result);
    response.headers.set("Cache-Control", "no-store");
    response.headers.delete(proxySecretHeader);
    response.headers.delete(clientIpHeader);
    const location = response.headers.get("Location");
    if (location) {
      const redirect = new URL(location, upstream);
      if (redirect.origin === upstream.origin) {
        redirect.protocol = frontend.protocol;
        redirect.hostname = frontend.hostname;
        redirect.port = frontend.port;
        response.headers.set("Location", redirect.toString());
      }
    }
    return response;
  } catch {
    return apiError(502, "The backend API is unavailable.");
  }
}
