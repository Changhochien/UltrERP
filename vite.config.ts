import { configDefaults, defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import os from "node:os";
import path from "path";

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";
const buildTarget =
  process.env.TAURI_PLATFORM === "windows"
    ? "chrome105"
    : process.env.TAURI_PLATFORM
      ? "safari13"
      : "esnext";

function parsePositiveInteger(value: string | undefined, fallback: number) {
  if (!value) {
    return fallback;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

const detectedParallelism = os.availableParallelism?.() ?? os.cpus().length;
const defaultVitestMaxWorkers = Math.max(1, Math.min(4, Math.ceil(detectedParallelism / 2)));
const vitestMaxWorkers = parsePositiveInteger(
  process.env.VITEST_MAX_WORKERS,
  defaultVitestMaxWorkers,
);
const vitestMinWorkers = Math.min(
  parsePositiveInteger(process.env.VITEST_MIN_WORKERS, 1),
  vitestMaxWorkers,
);

export default defineConfig({
  plugins: [tailwindcss(), react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  envPrefix: ["VITE_", "TAURI_"],
  build: {
    target: buildTarget,
    minify: process.env.TAURI_DEBUG ? false : "esbuild",
    sourcemap: Boolean(process.env.TAURI_DEBUG),
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/tests/setup.ts"],
    exclude: [...configDefaults.exclude, "src/tests/_skipped/**"],
    pool: "forks",
    maxWorkers: vitestMaxWorkers,
    minWorkers: vitestMinWorkers,
  },
});
