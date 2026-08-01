import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { RiskDashboardPage } from "@/components/risk/risk-dashboard-page";
import { apiBaseUrl } from "@/lib/api/client";
import type { Repository, RepositoryRiskResponse } from "@/lib/api/types";
import { renderWithProviders } from "@/test/render";
import { server } from "@/test/server";

const repository: Repository = {
  clone_url: "https://github.com/mahdi-behnam/repolens.git",
  created_at: "2026-06-21T10:00:00Z",
  current_ref: "main",
  default_branch: "main",
  id: "77777777-7777-7777-7777-777777777777",
  indexed_at: "2026-06-21T10:30:00Z",
  last_indexed_commit: "abc123",
  local_path: null,
  name: "repolens",
  repo_metadata: null,
  status: "indexed",
  updated_at: "2026-06-21T10:30:00Z",
};

const riskResponse: RepositoryRiskResponse = {
  files: [
    {
      components: {
        churn: 0.72,
        complexity: 0.58,
        dependency: 0.9,
      },
      path: "backend/app/services/indexing_service.py",
      reasons: [
        "High dependency fan-in.",
        "Recent changes touched this file repeatedly.",
      ],
      risk_score: 0.87,
    },
    {
      components: {
        churn: 0.31,
        dependency: 0.44,
      },
      path: "backend/app/api/v1/endpoints/indexing.py",
      reasons: ["Endpoint depends on high-risk service code."],
      risk_score: 0.53,
    },
  ],
  metadata: {
    generated_at: "2026-06-22T09:00:00Z",
  },
  repository_id: "77777777-7777-7777-7777-777777777777",
};

function useRepositoryHandler() {
  server.use(
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777`, () => HttpResponse.json(repository)),
  );
}

describe("RiskDashboardPage", () => {
  it("renders risk summary, chart, table, and component details", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/risk/repositories/77777777-7777-7777-7777-777777777777/files`, () =>
        HttpResponse.json(riskResponse),
      ),
    );

    renderWithProviders(<RiskDashboardPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    expect(await screen.findByText("Risk summary")).toBeInTheDocument();
    expect(screen.getByText("Risk distribution")).toBeInTheDocument();
    expect(screen.getByText("Ranked files")).toBeInTheDocument();
    expect(
      screen.getByText("backend/app/services/indexing_service.py"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("87.0%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("dependency").length).toBeGreaterThan(0);
    expect(screen.getByText(/High dependency fan-in\./)).toBeInTheDocument();
    expect(screen.getByText("Heuristic score")).toBeInTheDocument();
  });

  it("applies filter parameters to the risk request", async () => {
    const requests: string[] = [];
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/risk/repositories/77777777-7777-7777-7777-777777777777/files`, ({ request }) => {
        requests.push(request.url);
        return HttpResponse.json(riskResponse);
      }),
    );

    renderWithProviders(<RiskDashboardPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    await waitFor(() => expect(requests.length).toBeGreaterThan(0));
    fireEvent.change(screen.getByLabelText("Top files"), {
      target: { value: "12" },
    });
    fireEvent.change(screen.getByLabelText("Language filter"), {
      target: { value: "python" },
    });
    fireEvent.click(screen.getByLabelText("Include tests"));
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    await waitFor(() => expect(requests.length).toBeGreaterThan(1));
    const lastRequest = new URL(requests.at(-1) ?? "");
    expect(lastRequest.searchParams.get("top_k")).toBe("12");
    expect(lastRequest.searchParams.get("language")).toBe("python");
    expect(lastRequest.searchParams.get("include_tests")).toBe("true");
  });

  it("renders an empty risk response", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/risk/repositories/77777777-7777-7777-7777-777777777777/files`, () =>
        HttpResponse.json({ ...riskResponse, files: [] }),
      ),
    );

    renderWithProviders(<RiskDashboardPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    expect(await screen.findByText("No risk results")).toBeInTheDocument();
  });
});
