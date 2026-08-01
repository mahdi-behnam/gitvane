import { expect, type Page, test } from "@playwright/test";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

async function mockOverviewApis(page: Page) {
  await page.route(`${apiBaseUrl}/health`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { database: "connected", status: "healthy" },
    });
  });

  await page.route(`${apiBaseUrl}/repositories*`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        items: [
          {
            clone_url: "https://github.com/mahdi-behnam/repolens.git",
            created_at: "2026-06-21T10:00:00Z",
            current_ref: "main",
            default_branch: "main",
            id: 7,
            indexed_at: "2026-06-21T10:30:00Z",
            last_indexed_commit: "abc123",
            local_path: null,
            name: "repolens",
            repo_metadata: null,
            status: "indexed",
            updated_at: "2026-06-21T10:30:00Z",
          },
        ],
        limit: 100,
        skip: 0,
        total: 1,
      },
    });
  });

  await page.route(`${apiBaseUrl}/repositories/7/index/status`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        chunk_count: 30,
        commit_count: 5,
        current_ref: "main",
        dependency_edge_count: 12,
        file_count: 18,
        indexed_at: "2026-06-21T10:30:00Z",
        last_indexed_commit: "abc123",
        repository_id: 7,
        status: "indexed",
        symbol_count: 44,
      },
    });
  });

  await page.route(`${apiBaseUrl}/risk/repositories/7/files*`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        files: [
          {
            components: { dependency: 0.8 },
            path: "backend/app/services/indexing_service.py",
            reasons: ["High dependency fan-in."],
            risk_score: 0.82,
          },
        ],
        metadata: {},
        repository_id: 7,
      },
    });
  });
}

test.describe("overview smoke", () => {
  test("renders the dashboard with mocked backend data", async ({ page }) => {
    await mockOverviewApis(page);
    await page.goto("/");

    await expect(
      page.getByRole("heading", { name: "RepoLens dashboard" }),
    ).toBeVisible();
    await expect(page.getByText("Recent repositories")).toBeVisible();
    await expect(page.getByText("Risk summary")).toBeVisible();
    await expect(page.getByText("Evaluation summary")).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Run semantic search/i }),
    ).toBeVisible();
  });

  test("supports keyboard focus and reduced motion", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await mockOverviewApis(page);
    await page.goto("/");

    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Overview" }).first()).toBeFocused();

    const transitionDuration = await page
      .getByRole("link", { exact: true, name: "Add repository" })
      .evaluate((element) => getComputedStyle(element).transitionDuration);
    const transitionSeconds = transitionDuration.endsWith("ms")
      ? Number(transitionDuration.replace("ms", "")) / 1000
      : Number(transitionDuration.replace("s", ""));
    expect(transitionSeconds).toBeLessThanOrEqual(0.00001);
  });

  test("opens mobile navigation", async ({ page }) => {
    await page.setViewportSize({ height: 844, width: 390 });
    await mockOverviewApis(page);
    await page.goto("/");

    await page.getByRole("button", { name: "Open navigation" }).click();
    const dialog = page.getByRole("dialog", { name: "RepoLens" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("link", { name: "Repositories" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });
});
