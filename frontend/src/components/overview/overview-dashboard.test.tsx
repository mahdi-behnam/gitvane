import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { OverviewDashboard } from "@/components/overview/overview-dashboard";
import { apiBaseUrl } from "@/lib/api/client";
import type {
  IndexStatusResponse,
  RepositoryList,
  RepositoryRiskResponse,
} from "@/lib/api/types";
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
    const indexStatus: IndexStatusResponse = {
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
    };
    const riskResponse: RepositoryRiskResponse = {
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
    };

    server.use(
      http.get(`${apiBaseUrl}/repositories`, () => HttpResponse.json(response)),
      http.get(`${apiBaseUrl}/repositories/7/index/status`, () =>
        HttpResponse.json(indexStatus),
      ),
      http.get(`${apiBaseUrl}/risk/repositories/7/files`, () =>
        HttpResponse.json(riskResponse),
      ),
    );

    renderWithProviders(<OverviewDashboard />);

    expect(await screen.findByText("Recent repositories")).toBeInTheDocument();
    expect(screen.getByText("repolens")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("18").length).toBeGreaterThan(0));
    expect(screen.getByText("Review risk")).toBeInTheDocument();
    expect(screen.getAllByText("Open evaluation").length).toBeGreaterThan(0);
    expect(await screen.findByText("Risk summary")).toBeInTheDocument();
    expect(
      screen.getAllByText("backend/app/services/indexing_service.py").length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("Evaluation summary")).toBeInTheDocument();
    expect(screen.getByText(/does not invent evaluation results/)).toBeInTheDocument();
  });
});
