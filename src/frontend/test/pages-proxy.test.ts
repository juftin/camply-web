// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { onRequest } from "../functions/api/[[path]]";

const origin = "https://camply.example.test";
const env = {
  CAMPLY_API_ORIGIN: "https://api.example.test",
  CAMPLY_API_PROXY_SECRET: "synthetic-proxy-secret-for-unit-tests",
};
const edgeHeaders = { "CF-Connecting-IP": "203.0.113.20" };

afterEach(() => vi.unstubAllGlobals());

describe("Cloudflare Pages API proxy", () => {
  it("relays both strict cookies from login without changing their attributes", async () => {
    const headers = new Headers({ "Content-Type": "application/json" });
    const cookies = [
      "camply_session=synthetic-session; Path=/; HttpOnly; Secure; SameSite=Strict",
      "camply_csrf=synthetic-csrf; Path=/; Secure; SameSite=Strict",
    ];
    cookies.forEach((cookie) => headers.append("Set-Cookie", cookie));
    const upstream = new Response('{"id":"synthetic-user"}', { headers });
    const fetchMock = vi.fn().mockResolvedValue(upstream);
    vi.stubGlobal("fetch", fetchMock);

    const response = await onRequest({
      env,
      request: new Request(`${origin}/api/login`, {
        method: "POST",
        headers: {
          ...edgeHeaders,
          "Content-Type": "application/json",
          Origin: origin,
          "Sec-Fetch-Site": "same-origin",
        },
        body: JSON.stringify({ username: "synthetic", password: "synthetic" }),
      }),
    });

    const forwarded = fetchMock.mock.calls[0][0] as Request;
    expect(forwarded.url).toBe(`${env.CAMPLY_API_ORIGIN}/api/login`);
    expect(forwarded.method).toBe("POST");
    expect(forwarded.headers.get("Origin")).toBe(origin);
    expect(await forwarded.json()).toEqual({
      username: "synthetic",
      password: "synthetic",
    });
    expect(response.headers.getSetCookie()).toEqual(cookies);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(await response.json()).toEqual({ id: "synthetic-user" });
  });

  it("forwards session, CSRF, bearer headers, query strings, and mutation bodies", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await onRequest({
      env,
      request: new Request(`${origin}/api/scans/synthetic?notify=false`, {
        method: "PATCH",
        headers: {
          ...edgeHeaders,
          Cookie:
            "camply_session=synthetic-session; camply_csrf=synthetic-csrf",
          "X-CSRF-Token": "synthetic-csrf",
          Authorization: "Bearer synthetic-token",
          Host: "camply.example.test",
        },
        body: '{"is_active":false}',
      }),
    });

    const forwarded = fetchMock.mock.calls[0][0] as Request;
    expect(forwarded.url).toBe(
      `${env.CAMPLY_API_ORIGIN}/api/scans/synthetic?notify=false`,
    );
    expect(forwarded.method).toBe("PATCH");
    expect(forwarded.headers.get("Cookie")).toContain(
      "camply_session=synthetic-session",
    );
    expect(forwarded.headers.get("X-CSRF-Token")).toBe("synthetic-csrf");
    expect(forwarded.headers.get("Authorization")).toBe(
      "Bearer synthetic-token",
    );
    expect(forwarded.headers.has("Host")).toBe(false);
    expect(await forwarded.json()).toEqual({ is_active: false });
    expect(fetchMock.mock.calls[0][1]).toEqual({
      redirect: "manual",
      cache: "no-store",
    });
    expect(response.status).toBe(204);
  });

  it("keeps backend redirects on the frontend host and preserves denied responses", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(null, {
          status: 307,
          headers: { Location: `${env.CAMPLY_API_ORIGIN}/api/scans?limit=5` },
        }),
      )
      .mockResolvedValueOnce(
        new Response('{"detail":"Sign in required"}', { status: 401 }),
      );
    vi.stubGlobal("fetch", fetchMock);
    const request = new Request(`${origin}/api/scans/`, {
      headers: edgeHeaders,
    });
    const redirect = await onRequest({ env, request });
    expect(redirect.status).toBe(307);
    expect(redirect.headers.get("Location")).toBe(
      `${origin}/api/scans?limit=5`,
    );

    const denied = await onRequest({ env, request });
    expect(denied.status).toBe(401);
    expect(await denied.json()).toEqual({ detail: "Sign in required" });
  });

  it("keeps the frontend scheme and port in rewritten redirects", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(null, {
          status: 307,
          headers: { Location: "/api/scans" },
        }),
      ),
    );
    const frontend = "http://localhost:8788";
    const response = await onRequest({
      env: { ...env, CAMPLY_API_ORIGIN: "https://api.example.test:9443" },
      request: new Request(`${frontend}/api/scans/`, { headers: edgeHeaders }),
    });
    expect(response.headers.get("Location")).toBe(`${frontend}/api/scans`);
  });

  it.each([
    undefined,
    "invalid",
    "http://api.example.test",
    `${origin}`,
    `${env.CAMPLY_API_ORIGIN}/api`,
  ])(
    "fails closed for an invalid backend origin (%s)",
    async (CAMPLY_API_ORIGIN) => {
      const fetchMock = vi.fn();
      vi.stubGlobal("fetch", fetchMock);
      const response = await onRequest({
        env: { ...env, CAMPLY_API_ORIGIN },
        request: new Request(`${origin}/api/me`, { headers: edgeHeaders }),
      });
      expect(response.status).toBe(503);
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it("sets private trust headers from runtime bindings and the Cloudflare edge", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json(
        { detail: "Too many requests" },
        {
          status: 429,
          headers: {
            "Retry-After": "42",
            "X-Camply-Proxy-Secret": env.CAMPLY_API_PROXY_SECRET,
            "X-Camply-Client-IP": edgeHeaders["CF-Connecting-IP"],
          },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const response = await onRequest({
      env,
      request: new Request(`${origin}/api/search`, {
        headers: {
          ...edgeHeaders,
          "X-Camply-Proxy-Secret": "browser-supplied-secret",
          "X-Camply-Client-IP": "198.51.100.1",
          Forwarded: "for=198.51.100.2",
          "X-Forwarded-For": "198.51.100.3",
          "X-Real-IP": "198.51.100.4",
        },
      }),
    });
    const { headers } = fetchMock.mock.calls[0][0] as Request;
    expect(headers.get("X-Camply-Proxy-Secret")).toBe(
      env.CAMPLY_API_PROXY_SECRET,
    );
    expect(headers.get("X-Camply-Client-IP")).toBe(
      edgeHeaders["CF-Connecting-IP"],
    );
    expect(headers.has("Forwarded")).toBe(false);
    expect(headers.has("X-Forwarded-For")).toBe(false);
    expect(headers.has("X-Real-IP")).toBe(false);
    expect(response.status).toBe(429);
    expect(response.headers.get("Retry-After")).toBe("42");
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(response.headers.has("X-Camply-Proxy-Secret")).toBe(false);
    expect(response.headers.has("X-Camply-Client-IP")).toBe(false);
  });

  it.each([undefined, "", "short", `${env.CAMPLY_API_PROXY_SECRET}\n`])(
    "fails closed without a valid gateway secret (%s)",
    async (CAMPLY_API_PROXY_SECRET) => {
      const fetchMock = vi.fn();
      vi.stubGlobal("fetch", fetchMock);
      const response = await onRequest({
        env: { ...env, CAMPLY_API_PROXY_SECRET },
        request: new Request(`${origin}/api/me`, { headers: edgeHeaders }),
      });
      expect(response.status).toBe(503);
      expect(response.headers.get("Cache-Control")).toBe("no-store");
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it("does not use caller-supplied client IP headers as a fallback", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const response = await onRequest({
      env,
      request: new Request(`${origin}/api/me`, {
        headers: {
          "X-Camply-Client-IP": "203.0.113.20",
          "X-Forwarded-For": "203.0.113.21",
        },
      }),
    });
    expect(response.status).toBe(503);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each(["/api/health", "/api/health/?ready=true", "/api/%68ealth"])(
    "keeps database readiness on the backend (%s)",
    async (path) => {
      const fetchMock = vi.fn();
      vi.stubGlobal("fetch", fetchMock);
      const response = await onRequest({
        env,
        request: new Request(`${origin}${path}`, { headers: edgeHeaders }),
      });
      expect(response.status).toBe(404);
      expect(response.headers.get("Cache-Control")).toBe("no-store");
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it("continues to proxy the lightweight liveness endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await onRequest({
      env,
      request: new Request(`${origin}/api/ping`, {
        headers: {
          ...edgeHeaders,
          "X-Camply-Proxy-Secret": "browser-supplied-secret",
          "X-Camply-Client-IP": "198.51.100.1",
        },
      }),
    });
    expect(response.status).toBe(200);
    const forwarded = fetchMock.mock.calls[0][0] as Request;
    expect(forwarded.url).toBe(`${env.CAMPLY_API_ORIGIN}/api/ping`);
    expect(forwarded.headers.has("X-Camply-Proxy-Secret")).toBe(false);
    expect(forwarded.headers.has("X-Camply-Client-IP")).toBe(false);
  });

  it.each([
    ["Origin", "https://other.example.test"],
    ["Origin", "null"],
    ["Sec-Fetch-Site", "cross-site"],
    ["Sec-Fetch-Site", "same-site"],
  ])("rejects cross-origin browser context (%s %s)", async (header, value) => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const response = await onRequest({
      env,
      request: new Request(`${origin}/api/search`, {
        headers: { ...edgeHeaders, [header]: value },
      }),
    });
    expect(response.status).toBe(403);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns a gateway error without exposing upstream connection details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("private upstream details")),
    );
    const response = await onRequest({
      env,
      request: new Request(`${origin}/api/me`, { headers: edgeHeaders }),
    });
    expect(response.status).toBe(502);
    expect(await response.text()).not.toContain("private upstream details");
  });
});
