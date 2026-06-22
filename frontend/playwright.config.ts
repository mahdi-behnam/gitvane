import { defineConfig, devices } from "@playwright/test";

const port = 3100;
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  expect: {
    timeout: 10_000,
  },
  fullyParallel: true,
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  reporter: [["list"]],
  testDir: "./tests/e2e",
  use: {
    baseURL,
    trace: "retain-on-failure",
  },
  webServer: {
    command: `npm run dev -- --hostname 127.0.0.1 --port ${port}`,
    env: {
      NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000/api/v1",
    },
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    url: baseURL,
  },
});
