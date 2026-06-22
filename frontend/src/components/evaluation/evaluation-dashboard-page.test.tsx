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
  id: 7,
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
  repository_id: 7,
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

function useRepositoryHandler() {
  server.use(
    http.get(`${apiBaseUrl}/repositories/7`, () => HttpResponse.json(repository)),
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
    );

    renderWithProviders(<EvaluationDashboardPage repositoryId={7} />);

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Nightly quality check" },
    });
    fireEvent.change(screen.getByLabelText("Commit limit"), {
      target: { value: "50" },
    });
    fireEvent.click(screen.getByLabelText("dependency_only"));
    fireEvent.click(screen.getByRole("button", { name: "Run evaluation" }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      commit_limit: 50,
      k_values: [5, 10, 20],
      methods: ["hybrid", "dependency_only"],
      name: "Nightly quality check",
      repository_id: 7,
    });
    expect(await screen.findByText("Nightly quality check")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("Run 42")).toBeInTheDocument();
  });

  it("loads an existing evaluation run manually", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/evaluation/42`, () => HttpResponse.json(statusResponse)),
    );

    renderWithProviders(<EvaluationDashboardPage repositoryId={7} />);

    fireEvent.change(screen.getByLabelText("Evaluation run ID"), {
      target: { value: "42" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load status" }));

    expect(await screen.findByText("Nightly quality check")).toBeInTheDocument();
  });

  it("validates methods and lookup IDs", () => {
    useRepositoryHandler();
    renderWithProviders(<EvaluationDashboardPage repositoryId={7} />);

    fireEvent.click(screen.getByLabelText("hybrid"));
    fireEvent.click(screen.getByRole("button", { name: "Run evaluation" }));
    expect(
      screen.getByText("Select at least one evaluation method."),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Evaluation run ID"), {
      target: { value: "abc" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load status" }));
    expect(screen.getByText("Enter a valid evaluation run ID.")).toBeInTheDocument();
  });
});
