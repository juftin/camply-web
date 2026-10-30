import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";
import tailwindcss from "tailwindcss";
import autoprefixer from "autoprefixer";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  css: {
    postcss: {
      plugins: [
        tailwindcss({
          config: path.resolve(
            import.meta.dirname,
            "src/frontend/tailwind.config.js",
          ),
        }),
        autoprefixer(),
      ],
    },
  },
  root: path.resolve(import.meta.dirname, "src/frontend"),
  base:
    process.env.CAMPLY_STANDALONE_BUILD === "1"
      ? "/"
      : process.env.GITHUB_REPOSITORY
        ? `/${process.env.GITHUB_REPOSITORY.split("/")[1]}/`
        : "/",
  publicDir: "public",
  envDir: process.env.CAMPLY_STANDALONE_BUILD === "1" ? false : undefined,
  build: {
    outDir: path.resolve(import.meta.dirname, "build/frontend"),
    emptyOutDir: true,
    // Preserve Vite 6's browser support when upgrading the bundler.
    target: ["es2020", "edge88", "firefox78", "chrome87", "safari14"],
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src/frontend"),
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
    setupFiles: [
      path.resolve(import.meta.dirname, "src/frontend/test/setup.ts"),
    ],
  },
});
