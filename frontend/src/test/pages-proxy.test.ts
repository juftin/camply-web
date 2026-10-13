// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { onRequest } from "../../functions/api/[[path]]";

const origin = "https://camply.example.test";
const env = { CAMPLY_API_ORIGIN: "https://api.example.test" };

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
        headers: { "Content-Type": "application/json", Origin: origin },
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
    const request = new Request(`${origin}/api/scans/`);
    const redirect = await onRequest({ env, request });
    expect(redirect.status).toBe(307);
    expect(redirect.headers.get("Location")).toBe(
      `${origin}/api/scans?limit=5`,
    );

    const denied = await onRequest({ env, request });
    expect(denied.status).toBe(401);
    expect(await denied.json()).toEqual({ detail: "Sign in required" });
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
        env: { CAMPLY_API_ORIGIN },
        request: new Request(`${origin}/api/me`),
      });
      expect(response.status).toBe(503);
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it("returns a gateway error without exposing upstream connection details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("private upstream details")),
    );
    const response = await onRequest({
      env,
      request: new Request(`${origin}/api/me`),
    });
    expect(response.status).toBe(502);
    expect(await response.text()).not.toContain("private upstream details");
  });
});
