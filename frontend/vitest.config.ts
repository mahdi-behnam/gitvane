import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": new URL("./src", import.meta.url).pathname,
    },
  },
  test: {
    environment: "happy-dom",
    exclude: ["**/node_modules/**", "**/tests/e2e/**"],
    globals: true,
    maxWorkers: 4,
    pool: "forks",
    setupFiles: ["./src/test/setup.ts"],
    testTimeout: 10000,
  },
});
