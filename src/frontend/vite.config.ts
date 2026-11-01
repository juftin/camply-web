import { defineConfig, type Plugin } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";
import fs from "fs";
import tailwindcss from "tailwindcss";
import autoprefixer from "autoprefixer";
import { spawnSync } from "node:child_process";

function syncRootBuild(): Plugin {
  let output = "";
  let isDistBuild = false;
  return {
    name: "sync-root-build",
    apply: "build",
    configResolved(config) {
      output = path.resolve(config.root, config.build.outDir);
      isDistBuild =
        config.build.outDir === path.resolve(import.meta.dirname, "dist");
    },
    closeBundle() {
      const root = path.resolve(import.meta.dirname, "../..");
      const python = process.env.CAMPLY_BUILD_PYTHON;
      const result = spawnSync(
        python || "uv",
        [
          ...(python
            ? ["-m", "zensical"]
            : [
                "run",
                "--locked",
                "--isolated",
                "--only-group",
                "docs",
                "--",
                "zensical",
              ]),
          "build",
          "--strict",
        ],
        { cwd: root, stdio: "inherit" },
      );
      if (result.error || result.status !== 0) {
        throw new Error(
          "Documentation build failed; the app bundle is incomplete.",
          {
            cause: result.error,
          },
        );
      }
      fs.cpSync(path.join(root, "build/docs"), path.join(output, "docs"), {
        recursive: true,
      });
      if (!isDistBuild) return;
      const dist = path.resolve(import.meta.dirname, "dist");
      if (fs.existsSync(dist)) {
        const out = path.resolve(import.meta.dirname, "../../build/frontend");
        fs.rmSync(out, { recursive: true, force: true });
        fs.mkdirSync(out, { recursive: true });
        fs.cpSync(dist, out, { recursive: true });
      }
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), syncRootBuild()],
  css: {
    postcss: {
      plugins: [
        tailwindcss({
          config: path.resolve(import.meta.dirname, "tailwind.config.js"),
        }),
        autoprefixer(),
      ],
    },
  },
  root: import.meta.dirname,
  base:
    process.env.CAMPLY_STANDALONE_BUILD === "1"
      ? "/"
      : process.env.GITHUB_REPOSITORY
        ? `/${process.env.GITHUB_REPOSITORY.split("/")[1]}/`
        : "/",
  publicDir: "public",
  envDir: process.env.CAMPLY_STANDALONE_BUILD === "1" ? false : undefined,
  build: {
    outDir: path.resolve(import.meta.dirname, "dist"),
    emptyOutDir: true,
    // Preserve Vite 6's browser support when upgrading the bundler.
    target: ["es2020", "edge88", "firefox78", "chrome87", "safari14"],
  },
  resolve: {
    alias: {
      "@": import.meta.dirname,
    },
  },
  server: {
    host: "0.0.0.0",
    allowedHosts: true,
    proxy: {
      "/api": {
        target: process.env.CAMPLY_API_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    allowedHosts: true,
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: [path.resolve(import.meta.dirname, "test/setup.ts")],
  },
});
