import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { ImpactAnalysisPage } from "@/components/impact/impact-analysis-page";
import { apiBaseUrl } from "@/lib/api/client";
import type {
  ImpactAnalyzeResponse,
  ImpactRunResponse,
  Repository,
} from "@/lib/api/types";
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

const impactResponse: ImpactAnalyzeResponse = {
  analysis_run_id: 91,
  base_ref: null,
  changed_files: [
    {
      change_type: "modified",
      changed_lines: [],
      old_path: null,
      path: "backend/app/services/indexing_service.py",
    },
  ],
  changed_symbols: [
    {
      end_line: 30,
      path: "backend/app/services/indexing_service.py",
      qualified_name: "IndexingService.index_repository",
      start_line: 10,
      symbol_type: "function",
    },
  ],
  head_ref: null,
  impacted_files: [
    {
      component_scores: {
        dependency: 0.8,
        semantic: 0.6,
      },
      path: "backend/app/api/v1/endpoints/indexing.py",
      rank: 1,
      reasons: [
        {
          confidence: 0.8,
          evidence: { edge_type: "imports" },
          message: "Endpoint depends on indexing service.",
          type: "dependency",
        },
      ],
      recommended_tests: [
        {
          linked_files: ["backend/app/api/v1/endpoints/indexing.py"],
          path: "backend/tests/test_indexing.py",
          reason: "Covers indexing endpoint behavior.",
          score: 0.71,
        },
      ],
      score: 0.82,
    },
  ],
  llm_explanation: "Evidence suggests indexing endpoint behavior may change.",
  recommended_tests: [
    {
      linked_files: ["backend/app/services/indexing_service.py"],
      path: "backend/tests/test_indexing.py",
      reason: "Covers indexing workflow.",
      score: 0.71,
    },
  ],
  repository_id: "77777777-7777-7777-7777-777777777777",
  risk_summary: {
    highest_risk_files: [{ path: "backend/app/services/indexing_service.py" }],
  },
};

function useRepositoryHandler() {
  server.use(
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777`, () => HttpResponse.json(repository)),
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777/files/search`, () =>
      HttpResponse.json([
        { is_test: false, language: "python", loc: 120, path: "backend/app/services/indexing_service.py" },
      ]),
    ),
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777/refs`, () =>
      HttpResponse.json([
        { name: "main", ref_type: "branch", commit_sha: "abc1234", commit_message: "init", commit_date: "2026-06-21T10:00:00Z" },
        { name: "development", ref_type: "branch", commit_sha: "def5678", commit_message: "dev branch", commit_date: "2026-06-21T11:00:00Z" },
      ]),
    ),
    http.get(`${apiBaseUrl}/impact/repository/77777777-7777-7777-7777-777777777777/runs`, () => HttpResponse.json([])),
  );
}


describe("ImpactAnalysisPage", () => {
  it("submits changed files and renders impact evidence", async () => {
    const bodies: unknown[] = [];
    useRepositoryHandler();
    server.use(
      http.post(`${apiBaseUrl}/impact/analyze`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(impactResponse);
      }),
    );

    renderWithProviders(<ImpactAnalysisPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    fireEvent.click(screen.getByLabelText("Changed files"));
    const option = await screen.findByRole("button", { name: /indexing_service\.py/ });
    fireEvent.click(option);
    fireEvent.click(screen.getByRole("button", { name: "Analyze impact" }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      changed_files: [{ path: "backend/app/services/indexing_service.py" }],
      include_changed_files_in_predictions: false,
      include_explanation: true,
      repository_id: "77777777-7777-7777-7777-777777777777",
      top_k: 20,
    });
    expect(await screen.findByText("Likely impacted files")).toBeInTheDocument();
    expect(
      screen.getAllByText(/backend\/app\/api\/v1\/endpoints\/indexing.py/).length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText(/dependency/i).length).toBeGreaterThan(0);
    expect(
      screen.getAllByText("backend/tests/test_indexing.py").length,
    ).toBeGreaterThan(0);
    expect(screen.getByText(/LLM explanations summarize/)).toBeInTheDocument();
  });

  it("submits raw diff mode", async () => {
    const bodies: unknown[] = [];
    useRepositoryHandler();
    server.use(
      http.post(`${apiBaseUrl}/impact/analyze`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ ...impactResponse, llm_explanation: null });
      }),
    );

    renderWithProviders(<ImpactAnalysisPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    fireEvent.click(screen.getByRole("button", { name: "Raw diff" }));
    fireEvent.change(screen.getByLabelText("Raw diff", { selector: "textarea" }), {
      target: { value: "diff --git a/a.py b/a.py" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Analyze impact" }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      changed_files: null,
      raw_diff: "diff --git a/a.py b/a.py",
    });
  });

  it("submits ref mode and refreshes a stored run", async () => {
    const bodies: unknown[] = [];
    const runResponse: ImpactRunResponse = {
      analysis_run_id: 91,
      changed_files: [{ path: "backend/app/services/indexing_service.py" }],
      changed_symbols: [],
      input_mode: "git_diff",
      predictions: impactResponse.impacted_files,
      repository_id: "77777777-7777-7777-7777-777777777777",
      status: "completed",
    };

    useRepositoryHandler();
    server.use(
      http.post(`${apiBaseUrl}/impact/analyze`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(impactResponse);
      }),
      http.get(`${apiBaseUrl}/impact/runs/91`, () => HttpResponse.json(runResponse)),
    );

    renderWithProviders(<ImpactAnalysisPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    fireEvent.click(screen.getByRole("button", { name: "Refs" }));
    fireEvent.click(screen.getByRole("combobox", { name: "Base ref" }));
    const mainOption = await screen.findByRole("button", { name: /main/ });
    fireEvent.click(mainOption);

    fireEvent.click(screen.getByRole("combobox", { name: "Head ref" }));
    const devOption = await screen.findByRole("button", { name: /development/ });
    fireEvent.click(devOption);

    fireEvent.click(screen.getByRole("button", { name: "Analyze impact" }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      base_ref: "main",
      head_ref: "development",
      raw_diff: null,
    });

    fireEvent.click(screen.getByRole("combobox", { name: "Analysis run ID" }));
    fireEvent.change(screen.getByPlaceholderText("Search run ID or status..."), {
      target: { value: "91" },
    });
    const useRunBtn = await screen.findByRole("button", { name: /Use / });
    fireEvent.click(useRunBtn);
    fireEvent.click(screen.getByRole("button", { name: "Load run" }));

    expect(await screen.findByText("Stored run")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });
});
