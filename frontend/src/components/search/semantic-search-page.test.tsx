import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { SemanticSearchPage } from "@/components/search/semantic-search-page";
import { apiBaseUrl } from "@/lib/api/client";
import type { Repository, SemanticSearchResponse } from "@/lib/api/types";
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

function useRepositoryHandler() {
  server.use(
    http.get(`${apiBaseUrl}/repositories/7`, () => HttpResponse.json(repository)),
  );
}

describe("SemanticSearchPage", () => {
  it("submits a semantic query and renders scored results", async () => {
    const bodies: unknown[] = [];
    const response: SemanticSearchResponse = {
      results: [
        {
          end_line: 24,
          path: "backend/app/services/indexing_service.py",
          score: 0.873,
          snippet: "async def index_repository(...):\n    return result",
          start_line: 12,
          symbol: "IndexingService.index_repository",
        },
      ],
    };

    useRepositoryHandler();
    server.use(
      http.post(`${apiBaseUrl}/search/semantic`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(response);
      }),
    );

    renderWithProviders(<SemanticSearchPage repositoryId={7} />);

    fireEvent.change(screen.getByLabelText("Search query"), {
      target: { value: "where is repository indexing triggered" },
    });
    fireEvent.change(screen.getByLabelText("Top results"), {
      target: { value: "5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toEqual({
      query: "where is repository indexing triggered",
      repository_id: 7,
      top_k: 5,
    });
    expect(
      await screen.findByText("backend/app/services/indexing_service.py"),
    ).toBeInTheDocument();
    expect(screen.getByText("0.873")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open graph/i })).toHaveAttribute(
      "href",
      "/repositories/7/graph",
    );
  });

  it("renders empty results", async () => {
    useRepositoryHandler();
    server.use(
      http.post(`${apiBaseUrl}/search/semantic`, () =>
        HttpResponse.json({ results: [] }),
      ),
    );

    renderWithProviders(<SemanticSearchPage repositoryId={7} />);

    fireEvent.change(screen.getByLabelText("Search query"), {
      target: { value: "nonexistent parser" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("No matching snippets")).toBeInTheDocument();
  });

  it("renders validation and API errors", async () => {
    useRepositoryHandler();
    renderWithProviders(<SemanticSearchPage repositoryId={7} />);

    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(
      await screen.findByText("Enter a semantic search query."),
    ).toBeInTheDocument();

    server.use(
      http.post(`${apiBaseUrl}/search/semantic`, () =>
        HttpResponse.json({ detail: "Repository not found" }, { status: 404 }),
      ),
    );

    fireEvent.change(screen.getByLabelText("Search query"), {
      target: { value: "entry point" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("Repository not found")).toBeInTheDocument();
  });
});
