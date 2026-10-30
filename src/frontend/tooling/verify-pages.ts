/** Bundle and serve a secret-free copy of the Pages project using real Wrangler. */
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { createServer } from "node:net";
import path from "node:path";
import ts from "typescript";
import { once } from "node:events";

const root = path.resolve(import.meta.dirname, "../../..");
const output = path.join(root, "tmp/pages-functions");
mkdirSync(output, { recursive: true });
const fixture = mkdtempSync(path.join(output, "fixture-"));
const frontend = path.join(fixture, "src/frontend");
mkdirSync(frontend, { recursive: true });
const executable = path.join(root, "node_modules/wrangler/bin/wrangler.js");

/** Exclude developer environment and auth settings from the Wrangler fixture. */
const environment = {
  PATH: process.env.PATH,
  HOME: path.join(fixture, "home"),
  XDG_CONFIG_HOME: path.join(fixture, "home/.config"),
  CI: "true",
  WRANGLER_SEND_METRICS: "false",
  WRANGLER_LOG_PATH: path.join(output, "wrangler.log"),
};

/** Reserve an ephemeral local port before starting Wrangler's local server. */
async function availablePort(): Promise<number> {
  const server = createServer();
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  assert(address && typeof address !== "string");
  await new Promise<void>((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
  return address.port;
}

/** Verify relative config, nested Functions and real HTTP routes without publishing. */
async function main(): Promise<void> {
  let server: ReturnType<typeof spawn> | undefined;
  let logs = "";
  try {
    cpSync(
      path.join(root, "src/frontend/wrangler.jsonc"),
      path.join(frontend, "wrangler.jsonc"),
    );
    cpSync(
      path.join(root, "src/frontend/functions"),
      path.join(frontend, "functions"),
      { recursive: true },
    );
    cpSync(
      path.join(root, "build/frontend"),
      path.join(fixture, "build/frontend"),
      { recursive: true },
    );
    const { config, error } = ts.parseConfigFileTextToJson(
      "wrangler.jsonc",
      readFileSync(path.join(frontend, "wrangler.jsonc"), "utf8"),
    );
    assert.equal(error, undefined);
    assert.equal(
      path.resolve(frontend, config.pages_build_output_dir),
      path.join(fixture, "build/frontend"),
    );
    const routes = JSON.parse(
      readFileSync(path.join(fixture, "build/frontend/_routes.json"), "utf8"),
    );
    assert(
      routes.include.includes("/api") && routes.include.includes("/api/*"),
    );
    const bundle = spawnSync(
      process.execPath,
      [
        executable,
        "--cwd",
        frontend,
        "pages",
        "functions",
        "build",
        "--outdir",
        path.join(output, "worker"),
      ],
      { cwd: fixture, env: environment, encoding: "utf8" },
    );
    assert.equal(bundle.status, 0, `${bundle.stdout}\n${bundle.stderr}`);
    assert.match(
      readFileSync(path.join(output, "worker/index.js"), "utf8"),
      /Configure CAMPLY_API_ORIGIN/,
    );
    const port = await availablePort();
    server = spawn(
      process.execPath,
      [
        executable,
        "--cwd",
        frontend,
        "pages",
        "dev",
        "--ip",
        "127.0.0.1",
        "--port",
        String(port),
      ],
      { cwd: fixture, env: environment, stdio: ["ignore", "pipe", "pipe"] },
    );
    server.stdout?.on("data", (chunk: Buffer) => {
      logs += chunk.toString();
    });
    server.stderr?.on("data", (chunk: Buffer) => {
      logs += chunk.toString();
    });
    const base = `http://127.0.0.1:${port}`;
    let ready = false;
    const deadline = Date.now() + 30000;
    while (Date.now() < deadline) {
      if (server.exitCode !== null)
        throw new Error(`Pages exited early: ${logs}`);
      try {
        const response = await fetch(base);
        if (response.ok) {
          ready = true;
          break;
        }
      } catch {
        /* The local runtime is still starting. */
      }
      await new Promise<void>((resolve) => setTimeout(resolve, 100));
    }
    assert(ready, `Pages did not become ready: ${logs}`);
    const home = await fetch(base);
    assert.match(await home.text(), /<div id="root">/);
    for (const route of ["/api", "/api/session?synthetic=true"]) {
      const response = await fetch(`${base}${route}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: '{"synthetic":true}',
      });
      assert.equal(
        response.status,
        503,
        `${route} did not reach the nested Function`,
      );
      assert.equal(response.headers.get("Cache-Control"), "no-store");
      assert.match(
        ((await response.json()) as { detail: string }).detail,
        /CAMPLY_API_ORIGIN/,
      );
    }
    console.log(
      "Pages config discovery, Function bundling, static HTTP and proxy HTTP checks passed.",
    );
  } finally {
    if (server && server.exitCode === null) {
      server.kill("SIGTERM");
      await once(server, "exit");
    }
    rmSync(fixture, { recursive: true, force: true });
  }
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
