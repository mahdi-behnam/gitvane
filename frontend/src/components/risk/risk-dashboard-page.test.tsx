import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { RiskDashboardPage } from "@/components/risk/risk-dashboard-page";
import { apiBaseUrl } from "@/lib/api/client";
import type { Repository, RepositoryRiskResponse } from "@/lib/api/types";
import { renderWithProviders } from "@/test/render";
import { server } from "@/test/server";

const repository: Repository = {
  clone_url: "https://github.com/mahdi-behnam/gitvane.git",
  created_at: "2026-06-21T10:00:00Z",
  current_ref: "main",
  default_branch: "main",
  id: "77777777-7777-7777-7777-777777777777",
  indexed_at: "2026-06-21T10:30:00Z",
  last_indexed_commit: "abc123",
  local_path: null,
  name: "gitvane",
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
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777/languages`, () => HttpResponse.json(["python"])),
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777/files/search`, () => HttpResponse.json([])),
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
    expect(screen.getAllByText("Dependency").length).toBeGreaterThan(0);
    expect(screen.getByText("High Dependency Fan-In")).toBeInTheDocument();
    expect(screen.getByText("Deterministic Heuristic Scoring")).toBeInTheDocument();
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
    fireEvent.change(screen.getByLabelText("Top files", { selector: "input" }), {
      target: { value: "12" },
    });
    fireEvent.click(screen.getByLabelText("Language filter"));
    const pythonOption = await screen.findByRole("button", { name: "python" });
    fireEvent.click(pythonOption);
    fireEvent.click(screen.getByLabelText("Include tests", { selector: "input" }));
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

  it("supports single-file inspection mode", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/risk/repositories/77777777-7777-7777-7777-777777777777/files`, () =>
        HttpResponse.json({
          ...riskResponse,
          metadata: {
            ...riskResponse.metadata,
            mean_risk_score: 0.45,
          },
        }),
      ),
    );

    renderWithProviders(
      <RiskDashboardPage
        initialPath="backend/app/services/indexing_service.py"
        repositoryId="77777777-7777-7777-7777-777777777777"
      />,
    );

    expect(await screen.findByText("File risk summary")).toBeInTheDocument();
    expect(screen.getByText("File signal breakdown")).toBeInTheDocument();
    expect(screen.getByText("Inspected file")).toBeInTheDocument();
    expect(screen.getByLabelText("Copy file path")).toBeInTheDocument();
    const topFilesInput = screen.getByLabelText("Top files", { selector: "input" });
    expect(topFilesInput).toBeDisabled();
    expect(topFilesInput).toHaveAttribute(
      "title",
      "Bypassed/disabled during single-file inspection mode",
    );
    expect(screen.getByText("+42.0% above avg")).toBeInTheDocument();
  });

  it("shows active filter pills and resets filters on reset click", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/risk/repositories/77777777-7777-7777-7777-777777777777/files`, () =>
        HttpResponse.json(riskResponse),
      ),
    );

    renderWithProviders(<RiskDashboardPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    await screen.findByText("Risk summary");

    fireEvent.change(screen.getByLabelText("Top files", { selector: "input" }), {
      target: { value: "15" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(await screen.findByText("Active filters:")).toBeInTheDocument();
    expect(screen.getByText("Top Files: 15")).toBeInTheDocument();

    const resetButton = screen.getByRole("button", { name: "Reset filters" });
    expect(resetButton).toHaveClass("border-danger/40");
    fireEvent.click(resetButton);

    await waitFor(() => {
      expect(screen.queryByText("Active filters:")).not.toBeInTheDocument();
    });
    expect((screen.getByLabelText("Top files", { selector: "input" }) as HTMLInputElement).value).toBe("20");
  });

  it("renders new component descriptions and title-cased fallbacks", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/risk/repositories/77777777-7777-7777-7777-777777777777/files`, () =>
        HttpResponse.json({
          ...riskResponse,
          files: [
            {
              components: {
                bugfix_frequency: 0.65,
                custom_unknown_metric: 0.35,
                file_size: 0.8,
                test_coverage_proxy: 0.5,
              },
              path: "backend/app/services/indexing_service.py",
              reasons: [],
              risk_score: 0.7,
            },
          ],
        }),
      ),
    );

    renderWithProviders(<RiskDashboardPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    expect((await screen.findAllByText("File Size")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("Bugfix Frequency")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("Test Coverage Proxy")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("Custom Unknown Metric")).length).toBeGreaterThan(0);
  });

  it("renders clear filters button in empty state when filters are active", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/risk/repositories/77777777-7777-7777-7777-777777777777/files`, () =>
        HttpResponse.json({ ...riskResponse, files: [] }),
      ),
    );

    renderWithProviders(
      <RiskDashboardPage
        initialPath="nonexistent_file.py"
        repositoryId="77777777-7777-7777-7777-777777777777"
      />,
    );

    expect(await screen.findByText("No risk results")).toBeInTheDocument();
    const clearButton = screen.getByRole("button", { name: "Clear filters & search" });
    expect(clearButton).toBeInTheDocument();

    fireEvent.click(clearButton);

    await waitFor(() => {
      expect(screen.queryByText("Active filters:")).not.toBeInTheDocument();
    });
  });
});
