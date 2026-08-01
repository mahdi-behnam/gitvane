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
    environment: "jsdom",
    exclude: ["**/node_modules/**", "**/tests/e2e/**"],
    globals: true,
    maxWorkers: 1,
    minWorkers: 1,
    setupFiles: ["./src/test/setup.ts"],
  },
});
