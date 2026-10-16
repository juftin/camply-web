import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { cpSync, mkdtempSync, mkdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const root = fileURLToPath(new URL("../", import.meta.url));
const packages = ["backend", "db", "providers", "worker"];

function fixture(t) {
  const directory = mkdtempSync(join(tmpdir(), "camply-release-"));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const files = [
    "Taskfile.yaml",
    "backend/Taskfile.yaml",
    "frontend/Taskfile.yaml",
    "backend/pyproject.toml",
    "backend/uv.lock",
    "frontend/package.json",
    "docker-compose.yaml",
    "docker-bake.release.hcl",
    "backend/docker-compose.yaml",
    "frontend/docker-compose.yaml",
    ...packages.map((name) => `backend/packages/${name}/pyproject.toml`),
  ];
  for (const file of files) {
    mkdirSync(dirname(join(directory, file)), { recursive: true });
    cpSync(join(root, file), join(directory, file));
  }
  return directory;
}

function task(directory, args, env = {}) {
  return spawnSync("task", args, {
    cwd: directory,
    encoding: "utf8",
    env: {
      ...process.env,
      CI: "",
      RELEASE_VERSION: "",
      DOCKER_HOST: "unix:///camply-release-tests-no-daemon.sock",
      DOCKER_CONTEXT: "",
      BUILDX_BUILDER: "",
      UV_OFFLINE: "1",
      UV_PYTHON: "3.12",
      ...env,
    },
  });
}

test("release preparation stamps both applications and keeps the lock usable", (t) => {
  const directory = fixture(t);
  const result = task(directory, ["release:prepare"], {
    RELEASE_VERSION: "2.3.4",
  });
  assert.equal(result.status, 0, result.stderr);
  for (const file of [
    "backend/pyproject.toml",
    ...packages.map((name) => `backend/packages/${name}/pyproject.toml`),
  ]) {
    assert.match(
      readFileSync(join(directory, file), "utf8"),
      /version = "2\.3\.4"/,
    );
  }
  const lock = readFileSync(join(directory, "backend/uv.lock"), "utf8");
  for (const name of ["camply-backend", ...packages]) {
    assert.ok(lock.includes(`name = "${name}"\nversion = "2.3.4"`));
  }
  const frontend = JSON.parse(
    readFileSync(join(directory, "frontend/package.json"), "utf8"),
  );
  assert.equal(frontend.version, "2.3.4");
  const check = spawnSync("uv", ["lock", "--check", "--offline"], {
    cwd: join(directory, "backend"),
    encoding: "utf8",
  });
  assert.equal(check.status, 0, check.stderr);
});

for (const [version, major] of [
  ["1.2.3", "v1"],
  ["2.3.4", "v2"],
]) {
  test(`release ${version} publishes its version, ${major}, and latest with a same-origin API`, (t) => {
    const result = task(fixture(t), ["publish", "--", "--print"], {
      CI: "true",
      RELEASE_VERSION: version,
      GITHUB_SHA: "0123456789abcdef",
    });
    assert.equal(result.status, 0, result.stderr);
    const plan = JSON.parse(result.stdout);
    assert.deepEqual(plan.group.default.targets, ["backend", "frontend"]);
    for (const name of ["backend", "frontend"]) {
      const target = plan.target[name];
      assert.deepEqual(target.tags, [
        `ghcr.io/juftin/camply-${name}:${version}`,
        `ghcr.io/juftin/camply-${name}:${major}`,
        `ghcr.io/juftin/camply-${name}:latest`,
      ]);
      assert.equal(target.labels["org.opencontainers.image.version"], version);
      assert.equal(
        target.labels["org.opencontainers.image.revision"],
        "0123456789abcdef",
      );
      assert.equal(
        target.labels["org.opencontainers.image.source"],
        "https://github.com/juftin/camply-web",
      );
      assert.ok(target.context.endsWith(name));
    }
    assert.equal(plan.target.frontend.args.CAMPLY_API_URL, "");
  });
}

test("main builds publish latest without changing numbered release tags", (t) => {
  const result = task(fixture(t), ["publish:latest", "--", "--print"], {
    CI: "true",
    GITHUB_SHA: "0123456789abcdef",
    RELEASE_VERSION: "2.3.4",
  });
  assert.equal(result.status, 0, result.stderr);
  const plan = JSON.parse(result.stdout);
  for (const name of ["backend", "frontend"]) {
    const target = plan.target[name];
    assert.deepEqual(target.tags, [`ghcr.io/juftin/camply-${name}:latest`]);
    assert.equal(
      target.labels["org.opencontainers.image.version"],
      "sha-0123456789abcdef",
    );
    assert.equal(
      target.labels["org.opencontainers.image.revision"],
      "0123456789abcdef",
    );
  }
  assert.equal(plan.target.frontend.args.CAMPLY_API_URL, "");
});

test("main publication requires CI and a source revision", (t) => {
  const directory = fixture(t);
  for (const env of [
    { GITHUB_SHA: "0123456789abcdef" },
    { CI: "true", GITHUB_SHA: "" },
  ]) {
    const result = task(directory, ["publish:latest", "--", "--print"], env);
    assert.notEqual(result.status, 0, JSON.stringify(env));
    assert.match(result.stderr, /CI|GITHUB_SHA/);
  }
});

test("publication requires CI and a stable release version", (t) => {
  const directory = fixture(t);
  for (const env of [
    { RELEASE_VERSION: "2.3.4" },
    { CI: "false", RELEASE_VERSION: "2.3.4" },
    { CI: "true" },
    { CI: "true", RELEASE_VERSION: "latest" },
    { CI: "true", RELEASE_VERSION: "2.3.4-beta.1" },
  ]) {
    const result = task(directory, ["publish", "--", "--print"], env);
    assert.notEqual(result.status, 0, JSON.stringify(env));
    assert.match(result.stderr, /CI|RELEASE_VERSION/);
  }
});
