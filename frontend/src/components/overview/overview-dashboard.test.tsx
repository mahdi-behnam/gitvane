import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { OverviewDashboard } from "@/components/overview/overview-dashboard";
import { apiBaseUrl } from "@/lib/api/client";
import type { RepositoryList } from "@/lib/api/types";
import { renderWithProviders } from "@/test/render";
import { server } from "@/test/server";

describe("OverviewDashboard", () => {
  it("renders the repository empty state", async () => {
    renderWithProviders(<OverviewDashboard />);

    expect(await screen.findByText("No repositories registered")).toBeInTheDocument();
  });

  it("renders repository summary data", async () => {
    const response: RepositoryList = {
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
    };

    server.use(
      http.get(`${apiBaseUrl}/repositories`, () => HttpResponse.json(response)),
    );

    renderWithProviders(<OverviewDashboard />);

    expect(await screen.findByText("Recently indexed")).toBeInTheDocument();
    expect(screen.getByText("repolens")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });
});
