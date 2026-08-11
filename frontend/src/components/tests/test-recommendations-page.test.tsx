import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { TestRecommendationsPage } from "@/components/tests/test-recommendations-page";
import { apiBaseUrl } from "@/lib/api/client";
import type { Repository, TestRecommendationResponse } from "@/lib/api/types";
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

const recommendationResponse: TestRecommendationResponse = {
  changed_files: [{ path: "backend/app/services/indexing_service.py" }],
  recommended_tests: [
    {
      linked_files: [
        "backend/app/services/indexing_service.py",
        "backend/app/api/v1/endpoints/indexing.py",
      ],
      path: "backend/tests/test_indexing.py",
      reason: "Covers indexing workflow and endpoint behavior.",
      score: 0.83,
    },
  ],
  repository_id: "77777777-7777-7777-7777-777777777777",
};

function useRepositoryHandler() {
  server.use(
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777`, () => HttpResponse.json(repository)),
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777/files/search`, () =>
      HttpResponse.json([
        { id: 1, is_test: false, language: "python", loc: 100, path: "backend/app/services/indexing_service.py" },
        { id: 2, is_test: false, language: "python", loc: 50, path: "backend/app/api/v1/endpoints/indexing.py" },
      ]),
    ),
  );
}


describe("TestRecommendationsPage", () => {
  it("submits changed files and renders recommendations", async () => {
    const bodies: unknown[] = [];
    useRepositoryHandler();
    server.use(
      http.post(`${apiBaseUrl}/tests/recommend`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(recommendationResponse);
      }),
    );

    renderWithProviders(
      <TestRecommendationsPage
        initialPath="backend/app/services/indexing_service.py"
        repositoryId="77777777-7777-7777-7777-777777777777"
      />,
    );

    fireEvent.change(screen.getByLabelText("Top results"), {
      target: { value: "12" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Recommend tests" }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      changed_files: [{ path: "backend/app/services/indexing_service.py" }],
      repository_id: "77777777-7777-7777-7777-777777777777",
      top_k: 12,
    });
    expect(await screen.findByText("Recommended tests")).toBeInTheDocument();
    expect(screen.getByText("backend/tests/test_indexing.py")).toBeInTheDocument();
    expect(screen.getByText("83.0%")).toBeInTheDocument();
    expect(screen.getByText(/Covers indexing workflow/)).toBeInTheDocument();
    expect(screen.getByText(/does not execute tests/i)).toBeInTheDocument();
  });

  it("includes optional impacted files when provided", async () => {
    const bodies: unknown[] = [];
    useRepositoryHandler();
    server.use(
      http.post(`${apiBaseUrl}/tests/recommend`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(recommendationResponse);
      }),
    );

    renderWithProviders(
      <TestRecommendationsPage
        initialPath="backend/app/services/indexing_service.py"
        repositoryId="77777777-7777-7777-7777-777777777777"
      />,
    );

    fireEvent.click(screen.getByLabelText("Impacted files"));
    const option2 = await screen.findByRole("button", { name: /endpoints\/indexing\.py/ });
    fireEvent.click(option2);
    fireEvent.click(screen.getByRole("button", { name: "Recommend tests" }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      impacted_files: ["backend/app/api/v1/endpoints/indexing.py"],
    });
  });

  it("renders an empty recommendation response", async () => {
    useRepositoryHandler();
    server.use(
      http.post(`${apiBaseUrl}/tests/recommend`, () =>
        HttpResponse.json({
          ...recommendationResponse,
          recommended_tests: [],
        }),
      ),
    );

    renderWithProviders(
      <TestRecommendationsPage
        initialPath="backend/app/services/indexing_service.py"
        repositoryId="77777777-7777-7777-7777-777777777777"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Recommend tests" }));

    expect(await screen.findByText("No recommendations")).toBeInTheDocument();
  });







  it("requires at least one changed file", () => {
    useRepositoryHandler();
    renderWithProviders(<TestRecommendationsPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    fireEvent.click(screen.getByRole("button", { name: "Recommend tests" }));

    expect(
      screen.getByText("Enter at least one changed file path."),
    ).toBeInTheDocument();
  });

});
