interface ProxyContext {
  request: Request;
  env: { CAMPLY_API_ORIGIN?: string };
}

/** Keep API traffic and host-only session cookies on the Pages frontend origin. */
export async function onRequest({
  request,
  env,
}: ProxyContext): Promise<Response> {
  const frontend = new URL(request.url);
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
    return Response.json(
      { detail: "Configure CAMPLY_API_ORIGIN with the HTTPS backend origin." },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }

  upstream.pathname = frontend.pathname;
  upstream.search = frontend.search;
  const forwarded = new Request(upstream, request);
  forwarded.headers.delete("Host");

  try {
    const result = await fetch(forwarded, {
      redirect: "manual",
      cache: "no-store",
    });
    const response = new Response(result.body, result);
    response.headers.set("Cache-Control", "no-store");
    const location = response.headers.get("Location");
    if (location) {
      const redirect = new URL(location, upstream);
      if (redirect.origin === upstream.origin) {
        redirect.host = frontend.host;
        response.headers.set("Location", redirect.toString());
      }
    }
    return response;
  } catch {
    return Response.json(
      { detail: "The backend API is unavailable." },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}
