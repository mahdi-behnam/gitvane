import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { EvaluationDashboardPage } from "@/components/evaluation/evaluation-dashboard-page";
import { apiBaseUrl } from "@/lib/api/client";
import type {
  EvaluationRunResponse,
  EvaluationStatusResponse,
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

const runResponse: EvaluationRunResponse = {
  evaluation_run_id: 42,
  status: "queued",
  summary: {},
};

const statusResponse: EvaluationStatusResponse = {
  commit_limit: 50,
  error_message: null,
  evaluation_run_id: 42,
  methods: ["hybrid", "dependency_only"],
  name: "Nightly quality check",
  repository_id: "77777777-7777-7777-7777-777777777777",
  status: "completed",
  summary: {
    hybrid: {
      map: 0.62,
      precision_at_k: {
        "5": 0.74,
      },
    },
  },
};

const markdownReport = `# Evaluation Report

Hybrid performed best against the available baseline.

- Review low recall cases
`;

function useRepositoryHandler() {
  server.use(
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777`, () => HttpResponse.json(repository)),
    http.get(`${apiBaseUrl}/evaluation/repository/77777777-7777-7777-7777-777777777777/runs`, () => HttpResponse.json([])),
  );
}

describe("EvaluationDashboardPage", () => {
  it("starts an evaluation and renders returned status", async () => {
    const bodies: unknown[] = [];
    useRepositoryHandler();
    server.use(
      http.post(`${apiBaseUrl}/evaluation/run`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(runResponse);
      }),
      http.get(`${apiBaseUrl}/evaluation/42`, () => HttpResponse.json(statusResponse)),
      http.get(`${apiBaseUrl}/evaluation/42/report.md`, () =>
        HttpResponse.text(markdownReport),
      ),
    );

    renderWithProviders(<EvaluationDashboardPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    fireEvent.change(screen.getByRole("textbox", { name: "Name" }), {
      target: { value: "Nightly quality check" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: /Commit limit/ }), {
      target: { value: "50" },
    });
    const methodsTrigger = document.getElementById("evaluation-methods");
    expect(methodsTrigger).not.toBeNull();
    fireEvent.click(methodsTrigger!);
    const depOption = await screen.findByRole("button", { name: /Dependency Only/ });
    fireEvent.click(depOption);
    fireEvent.click(screen.getByRole("button", { name: "Run evaluation" }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      commit_limit: 50,
      k_values: [5, 10, 20],
      methods: ["hybrid", "dependency_only"],
      name: "Nightly quality check",
      repository_id: "77777777-7777-7777-7777-777777777777",
    });
    expect(await screen.findByText("Nightly quality check")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("Run 42")).toBeInTheDocument();
    expect(screen.getByText("Metrics summary")).toBeInTheDocument();
    expect(screen.getByText("Baseline comparison")).toBeInTheDocument();
    expect(await screen.findByText("Evaluation Report")).toBeInTheDocument();
    expect(screen.getByText(/Hybrid performed best/)).toBeInTheDocument();
  });

  it("loads an existing evaluation run manually", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/evaluation/42`, () => HttpResponse.json(statusResponse)),
      http.get(`${apiBaseUrl}/evaluation/42/report.md`, () =>
        HttpResponse.text(markdownReport),
      ),
    );

    renderWithProviders(<EvaluationDashboardPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    fireEvent.click(screen.getByLabelText("Evaluation run ID"));
    fireEvent.change(screen.getByPlaceholderText("Search run name or ID..."), {
      target: { value: "42" },
    });
    const useBtn = await screen.findByRole("button", { name: /Use / });
    fireEvent.click(useBtn);

    fireEvent.click(screen.getByRole("button", { name: "Load status" }));

    expect(await screen.findByText("Nightly quality check")).toBeInTheDocument();
  });

  it("validates methods and lookup IDs", async () => {
    useRepositoryHandler();
    renderWithProviders(<EvaluationDashboardPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    const methodsTrigger = document.getElementById("evaluation-methods");
    expect(methodsTrigger).not.toBeNull();
    fireEvent.click(methodsTrigger!);
    const hybridOption = await screen.findByRole("button", { name: /hybrid/i });
    fireEvent.click(hybridOption);

    fireEvent.click(screen.getByRole("button", { name: "Run evaluation" }));
    expect(
      screen.getByText("Select at least one evaluation method."),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Evaluation run ID"));
    fireEvent.change(screen.getByPlaceholderText("Search run name or ID..."), {
      target: { value: "abc" },
    });
    const useBtn = await screen.findByRole("button", { name: /Use / });
    fireEvent.click(useBtn);

    fireEvent.click(screen.getByRole("button", { name: "Load status" }));
    expect(screen.getByText("Enter a valid numeric evaluation run ID.")).toBeInTheDocument();
  });
});
