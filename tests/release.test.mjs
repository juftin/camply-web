import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  cpSync,
  globSync,
  mkdtempSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const root = fileURLToPath(new URL("../", import.meta.url));

function fixture(t, { sources = false } = {}) {
  const directory = mkdtempSync(join(tmpdir(), "camply-release-"));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const files = [
    "Taskfile.yaml",
    "tasks/python.yaml",
    "tasks/frontend.yaml",
    "pyproject.toml",
    "uv.lock",
    "package.json",
    "docker-compose.yaml",
    "deploy/docker-bake.release.hcl",
    ".python-version",
    "README.md",
    "LICENSE",
  ];
  for (const file of files) {
    mkdirSync(dirname(join(directory, file)), { recursive: true });
    cpSync(join(root, file), join(directory, file));
  }
  if (sources) {
    for (const file of ["src", "pnpm-lock.yaml", "pnpm-workspace.yaml"]) {
      cpSync(join(root, file), join(directory, file), { recursive: true });
    }
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
      UV_OFFLINE: "0",
      UV_PYTHON: "3.14",
      ...env,
    },
  });
}

test("release preparation stamps both applications and keeps the lock usable", (t) => {
  const directory = fixture(t);
  const result = task(directory, ["release:prepare"], {
    RELEASE_VERSION: "2.3.4",
    UV_CACHE_DIR: join(directory, "uv-cache"),
  });
  assert.equal(result.status, 0, result.stderr);
  assert.match(
    readFileSync(join(directory, "pyproject.toml"), "utf8"),
    /version = "2\.3\.4"/,
  );
  const lock = readFileSync(join(directory, "uv.lock"), "utf8");
  assert.ok(lock.includes('name = "camply"\nversion = "2.3.4"'));
  for (const name of [
    "camply-backend",
    "backend",
    "db",
    "providers",
    "worker",
  ]) {
    assert.ok(!lock.includes(`name = "${name}"\nversion = "2.3.4"`));
  }
  const frontend = JSON.parse(
    readFileSync(join(directory, "package.json"), "utf8"),
  );
  assert.equal(frontend.version, "2.3.4");
  const check = spawnSync("uv", ["lock", "--check", "--offline"], {
    cwd: directory,
    encoding: "utf8",
    env: {
      ...process.env,
      UV_CACHE_DIR: join(directory, "uv-cache"),
      UV_PYTHON: "3.14",
    },
  });
  assert.equal(check.status, 0, check.stderr);
});

test("one wheel and sdist contain stamped metadata and support standalone rebuilding", (t) => {
  const directory = fixture(t, { sources: true });
  const prepared = task(directory, ["release:prepare"], {
    RELEASE_VERSION: "2.3.4",
  });
  assert.equal(prepared.status, 0, prepared.stderr);
  mkdirSync(join(directory, "dist"));
  writeFileSync(join(directory, "dist/stale-0.0.1.tar.gz"), "stale build");
  writeFileSync(
    join(directory, "dist/stale-0.0.1-py3-none-any.whl"),
    "stale wheel",
  );
  const built = task(directory, ["dist"]);
  assert.equal(built.status, 0, built.stderr);
  const artifacts = readdirSync(join(directory, "dist")).filter(
    (file) => file.endsWith(".tar.gz") || file.endsWith(".whl"),
  );
  assert.deepEqual(artifacts.sort(), [
    "camply-2.3.4-py3-none-any.whl",
    "camply-2.3.4.tar.gz",
  ]);
  const config = JSON.parse(
    readFileSync(join(root, "package.json"), "utf8"),
  ).release;
  const [, github] = config.plugins.find(
    (plugin) =>
      Array.isArray(plugin) && plugin[0] === "@semantic-release/github",
  );
  assert.deepEqual(
    globSync(github.assets, { cwd: directory }).sort(),
    artifacts.map((file) => `dist/${file}`).sort(),
  );
  const archive = join(directory, "dist/camply-2.3.4.tar.gz");
  const metadata = spawnSync(
    "tar",
    ["-xOf", archive, "camply-2.3.4/PKG-INFO"],
    {
      encoding: "utf8",
    },
  );
  assert.equal(metadata.status, 0, metadata.stderr);
  assert.match(metadata.stdout, /^Name: camply$/m);
  assert.match(metadata.stdout, /^Version: 2\.3\.4$/m);
  assert.match(metadata.stdout, /^Requires-Python: >=3\.11$/m);
  const extras = [...metadata.stdout.matchAll(/^Provides-Extra: (.+)$/gm)].map(
    (match) => match[1],
  );
  assert.deepEqual(extras.sort(), [
    "distributed",
    "postgres",
    "sentry",
    "server",
  ]);
  for (const [dependency, extra] of [
    ["fastapi", "server"],
    ["celery", "distributed"],
    ["psycopg", "postgres"],
    ["sentry-sdk", "sentry"],
  ]) {
    const requirement = metadata.stdout
      .split("\n")
      .find((line) => line.startsWith(`Requires-Dist: ${dependency}`));
    assert.ok(requirement?.includes(`extra == '${extra}'`), requirement);
  }
  const contents = spawnSync("tar", ["-tzf", archive], { encoding: "utf8" });
  assert.equal(contents.status, 0, contents.stderr);
  for (const file of [
    "LICENSE",
    "README.md",
    "src/camply/__init__.py",
    "src/camply/py.typed",
    "src/camply/db/migrations/env.py",
    "src/camply/db/migrations/script.py.mako",
    "src/camply/server/gunicorn.py",
    "src/camply/server/static/index.html",
    "src/frontend/index.html",
    "build/frontend-manifest.json",
  ]) {
    assert.ok(contents.stdout.includes(`camply-2.3.4/${file}`), file);
  }
  const rebuild = mkdtempSync(join(tmpdir(), "camply-sdist-rebuild-"));
  t.after(() => rmSync(rebuild, { recursive: true, force: true }));
  const standaloneArchive = join(rebuild, "camply-2.3.4.tar.gz");
  cpSync(archive, standaloneArchive);
  const rebuilt = spawnSync(
    "uv",
    [
      "build",
      "--wheel",
      standaloneArchive,
      "--out-dir",
      join(rebuild, "wheels"),
    ],
    {
      cwd: rebuild,
      encoding: "utf8",
      env: { ...process.env, UV_PYTHON: "3.14" },
    },
  );
  assert.equal(rebuilt.status, 0, rebuilt.stderr);
  assert.deepEqual(readdirSync(join(rebuild, "wheels")), [
    ".gitignore",
    "camply-2.3.4-py3-none-any.whl",
  ]);
  for (const wheel of [
    join(directory, "dist/camply-2.3.4-py3-none-any.whl"),
    join(rebuild, "wheels/camply-2.3.4-py3-none-any.whl"),
  ]) {
    const listed = spawnSync("unzip", ["-Z1", wheel], { encoding: "utf8" });
    assert.equal(listed.status, 0, listed.stderr);
    for (const file of [
      "camply/py.typed",
      "camply/db/migrations/env.py",
      "camply/db/migrations/script.py.mako",
      "camply/server/gunicorn.py",
      "camply/server/static/index.html",
    ])
      assert.ok(listed.stdout.split("\n").includes(file), file);
    assert.match(
      listed.stdout,
      /camply-2\.3\.4\.dist-info\/(?:licenses\/)?LICENSE/,
    );
  }
});

test("runtime defaults and compatibility checks preserve the Python support policy", () => {
  assert.equal(
    readFileSync(join(root, ".python-version"), "utf8").trim(),
    "3.14",
  );
  assert.match(
    readFileSync(join(root, "Dockerfile"), "utf8"),
    /ARG PYTHON_VERSION=3\.14/,
  );
  assert.match(
    readFileSync(
      join(root, ".github/actions/setup-backend/action.yaml"),
      "utf8",
    ),
    /default: "3\.14"/,
  );
  const ci = readFileSync(join(root, ".github/workflows/ci.yaml"), "utf8");
  assert.match(ci, /python-version: "3\.11"/);
  assert.match(ci, /task backend:packaging:test/);
});

for (const [version, major] of [
  ["1.2.3", "v1"],
  ["2.3.4", "v2"],
]) {
  test(`release ${version} publishes ${major}, v${version}, a seven-character SHA, and latest`, (t) => {
    const directory = fixture(t);
    const result = task(directory, ["publish", "--", "--print"], {
      CI: "true",
      RELEASE_VERSION: version,
      GITHUB_SHA: "0123456789abcdef",
    });
    assert.equal(result.status, 0, result.stderr);
    const plan = JSON.parse(result.stdout);
    assert.deepEqual(plan.group.default.targets, ["backend"]);
    const target = plan.target.backend;
    assert.deepEqual(target.tags, [
      `ghcr.io/juftin/camply:${major}`,
      `ghcr.io/juftin/camply:v${version}`,
      "ghcr.io/juftin/camply:0123456",
      `ghcr.io/juftin/camply:latest`,
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
    assert.equal(target.context, ".");
    assert.equal(target.target, "camply");
    assert.equal(target.dockerfile, "Dockerfile");
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
  const target = plan.target.backend;
  assert.deepEqual(target.tags, [`ghcr.io/juftin/camply:latest`]);
  assert.equal(
    target.labels["org.opencontainers.image.version"],
    "sha-0123456789abcdef",
  );
  assert.equal(
    target.labels["org.opencontainers.image.revision"],
    "0123456789abcdef",
  );
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

test("release publication requires a valid Git revision for its SHA tag", (t) => {
  const directory = fixture(t);
  for (const revision of [
    "",
    "123456",
    "not-a-git-sha",
    "0123456; touch unexpected-file",
  ]) {
    const result = task(directory, ["publish", "--", "--print"], {
      CI: "true",
      RELEASE_VERSION: "1.2.3",
      GITHUB_SHA: revision,
    });
    assert.notEqual(result.status, 0, revision);
    assert.match(result.stderr, /GITHUB_SHA/);
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
    const result = task(directory, ["publish", "--", "--print"], {
      GITHUB_SHA: "0123456789abcdef",
      ...env,
    });
    assert.notEqual(result.status, 0, JSON.stringify(env));
    assert.match(result.stderr, /CI|RELEASE_VERSION/);
  }
});

test("publisher selects the full release tag or exact main SHA and rejects other refs", () => {
  const workflow = readFileSync(
    join(root, ".github/workflows/publish.yaml"),
    "utf8",
  );
  const script = workflow
    .match(/script: \|\n((?: {12}.*\n)+)/)[1]
    .replace(/^ {12}/gm, "");
  const resolve = (context) => {
    const outputs = {};
    new Function("context", "core", script)(context, {
      setOutput: (name, value) => (outputs[name] = value),
    });
    return outputs;
  };
  for (const version of ["1.2.3", "2.0.0", "0.1.0"]) {
    assert.deepEqual(
      resolve({
        eventName: "release",
        sha: "unrelated-main-head",
        payload: { release: { tag_name: `v${version}` } },
      }),
      { ref: `refs/tags/v${version}`, version },
    );
  }
  assert.deepEqual(
    resolve({
      eventName: "push",
      ref: "refs/heads/main",
      sha: "0123456789abcdef",
    }),
    { ref: "0123456789abcdef", version: "" },
  );
  for (const tag of [
    "v1",
    "1.2.3",
    "v01.2.3",
    "v1.2.3-beta.1",
    "v1.2.3+build",
    "v1.2.3\n",
    "v1.2.3; touch unexpected-file",
  ]) {
    assert.throws(() =>
      resolve({
        eventName: "release",
        payload: { release: { tag_name: tag } },
      }),
    );
  }
  for (const context of [
    { eventName: "push", ref: "refs/heads/feature" },
    { eventName: "pull_request", ref: "refs/heads/main" },
  ]) {
    assert.throws(() => resolve(context));
  }
});

test("semantic release signals publication only after preparing source assets", (t) => {
  const directory = fixture(t);
  const config = JSON.parse(
    readFileSync(join(root, "package.json"), "utf8"),
  ).release;
  const [, exec] = config.plugins.find(
    (plugin) => Array.isArray(plugin) && plugin[0] === "@semantic-release/exec",
  );
  assert.equal(
    exec.prepareCmd,
    "task release:prepare RELEASE_VERSION=${nextRelease.version} && task dist",
  );
  const marker = () => readdirSync(directory).includes(".release-published");
  assert.equal(marker(), false);
  const result = spawnSync("sh", ["-c", exec.successCmd], {
    cwd: directory,
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(marker(), true);
});

test("one Python and Nginx image serves every application role", () => {
  const dockerfile = readFileSync(join(root, "Dockerfile"), "utf8");
  assert.match(dockerfile, /AS application-build/i);
  assert.equal((dockerfile.match(/RUN uv build/g) ?? []).length, 1);
  assert.match(dockerfile, /FROM python-base AS camply[\s\S]*USER camply/);
  assert.match(dockerfile, /apt-get install[^\n]*nginx/);
  assert.match(dockerfile, /CMD \["camply", "serve", "backend"\]/);
  assert.doesNotMatch(dockerfile, /envsubst|gettext-base|COPY deploy\/nginx/);
  assert.doesNotMatch(dockerfile, /FROM nginx|AS backend|AS frontend/);
  for (const file of [
    "backend/Dockerfile",
    "frontend/Dockerfile",
    "backend/docker-compose.yaml",
    "frontend/docker-compose.yaml",
  ]) {
    assert.equal(globSync(file, { cwd: root }).length, 0, file);
  }
});

test("required Docker checks share one build and reject unsuccessful build results", () => {
  const ci = readFileSync(join(root, ".github/workflows/ci.yaml"), "utf8");
  assert.match(ci, /backend-docker:\n    name: Backend Docker Build/);
  assert.equal((ci.match(/uses: docker\/bake-action@/g) ?? []).length, 1);
  const gate = ci.match(/  frontend-docker:\n([\s\S]*?)(?=\n  #|\n  [a-z])/)[1];
  assert.match(gate, /name: Frontend Docker Build/);
  assert.match(gate, /needs: \[backend-docker\]/);
  assert.match(gate, /if: \$\{\{ always\(\) \}\}/);
  assert.match(gate, /BUILD_RESULT: \$\{\{ needs\.backend-docker\.result \}\}/);
  const script = gate.match(/run: (.+)/)[1];
  for (const result of ["success", "failure", "cancelled", "skipped", ""]) {
    const checked = spawnSync("bash", ["-c", script], {
      encoding: "utf8",
      env: { ...process.env, BUILD_RESULT: result },
    });
    assert.equal(checked.status === 0, result === "success", result);
  }
});

test("distributed Compose retains services, persistent storage, and API relationships", () => {
  const rendered = spawnSync(
    "docker",
    ["compose", "--env-file", "/dev/null", "config", "--format", "json"],
    {
      cwd: root,
      encoding: "utf8",
      env: {
        PATH: process.env.PATH,
        HOME: process.env.HOME,
        COMPOSE_DISABLE_ENV_FILE: "1",
      },
    },
  );
  assert.equal(rendered.status, 0, rendered.stderr);
  const config = JSON.parse(rendered.stdout);
  assert.deepEqual(Object.keys(config.services).sort(), [
    "backend",
    "celery-beat",
    "celery-worker",
    "db",
    "frontend",
    "prometheus",
    "valkey",
  ]);
  assert.deepEqual(Object.keys(config.volumes).sort(), [
    "db_data",
    "prometheus_data",
    "valkey_data",
  ]);
  for (const name of ["backend", "celery-worker", "celery-beat"]) {
    const service = config.services[name];
    assert.equal(service.image, "ghcr.io/juftin/camply:local");
    assert.equal(service.build.context, root.replace(/\/$/, ""));
    assert.equal(service.build.target, "camply");
    assert.equal(service.environment.CAMPLY_DB_HOST, "db");
    assert.equal(
      service.environment.CAMPLY_VALKEY_URL,
      "redis://valkey:6379/0",
    );
    assert.equal(service.depends_on.db.condition, "service_healthy");
    assert.ok(
      service.volumes.some(
        (volume) =>
          volume.type === "bind" &&
          volume.source.endsWith("/.data/camply") &&
          volume.target === "/home/camply/.local/share/camply",
      ),
    );
  }
  for (const name of ["frontend", "celery-worker", "celery-beat"]) {
    assert.equal(config.services[name].image, config.services.backend.image);
    assert.deepEqual(
      config.services[name].build,
      config.services.backend.build,
    );
  }
  for (const name of ["backend", "frontend", "celery-worker", "celery-beat"]) {
    assert.equal(config.services[name].stop_grace_period, "1m0s");
  }
  assert.equal(config.services.frontend.stop_signal, "SIGQUIT");
  assert.equal(
    config.services.frontend.environment.CAMPLY_BACKEND_URL,
    "http://backend:8000",
  );
  for (const name of ["backend", "celery-worker", "celery-beat"]) {
    assert.equal(config.services[name].stop_signal, "SIGTERM");
  }
  assert.deepEqual(config.services.frontend.command, [
    "camply",
    "serve",
    "frontend",
  ]);
  assert.deepEqual(config.services["celery-worker"].command, [
    "camply",
    "serve",
    "worker",
  ]);
  assert.deepEqual(config.services["celery-beat"].command, [
    "camply",
    "serve",
    "beat",
    "--sync-providers",
  ]);
  for (const name of ["celery-worker", "celery-beat"]) {
    assert.equal(
      config.services[name].depends_on.backend.condition,
      "service_healthy",
    );
  }
  assert.equal(
    config.services.frontend.depends_on.backend.condition,
    "service_healthy",
  );
  for (const [name, role] of Object.entries({
    backend: "backend",
    frontend: "frontend",
    "celery-worker": "worker",
    "celery-beat": "beat",
  })) {
    assert.deepEqual(config.services[name].healthcheck.test, [
      "CMD",
      "camply",
      "serve",
      "healthcheck",
      role,
    ]);
  }
  assert.ok(
    config.services.prometheus.volumes.some(
      (volume) =>
        volume.source.endsWith(
          "/deploy/monitoring/prometheus/prometheus.yml",
        ) && volume.read_only,
    ),
  );
});

test("Compose passes a custom backend URL to the frontend", () => {
  const backend = "http://synthetic-api.internal:9000";
  const rendered = spawnSync(
    "docker",
    ["compose", "--env-file", "/dev/null", "config", "--format", "json"],
    {
      cwd: root,
      encoding: "utf8",
      env: {
        PATH: process.env.PATH,
        HOME: process.env.HOME,
        COMPOSE_DISABLE_ENV_FILE: "1",
        CAMPLY_BACKEND_URL: backend,
      },
    },
  );
  assert.equal(rendered.status, 0, rendered.stderr);
  assert.equal(
    JSON.parse(rendered.stdout).services.frontend.environment
      .CAMPLY_BACKEND_URL,
    backend,
  );
});
