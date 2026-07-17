import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { useRouter } from "next/navigation";
import { describe, expect, it, vi } from "vitest";
import { RepositoryDetailPage } from "@/components/repositories/repository-detail-page";
import { apiBaseUrl } from "@/lib/api/client";
import type {
  IndexRepositoryResponse,
  IndexStatusResponse,
  Repository,
} from "@/lib/api/types";
import { renderWithProviders } from "@/test/render";
import { server } from "@/test/server";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

function mockRouter(push = vi.fn()) {
  vi.mocked(useRouter).mockReturnValue({
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
    push,
    refresh: vi.fn(),
    replace: vi.fn(),
  });
  return push;
}

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

const indexStatus: IndexStatusResponse = {
  chunk_count: 30,
  commit_count: 4,
  current_ref: "main",
  dependency_edge_count: 12,
  file_count: 10,
  indexed_at: "2026-06-21T10:30:00Z",
  last_indexed_commit: "abc123",
  repository_id: 7,
  status: "indexed",
  symbol_count: 20,
};

const indexResponse: IndexRepositoryResponse = {
  chunks_indexed: 30,
  commits_indexed: 4,
  current_ref: "main",
  dependency_edges_indexed: 12,
  embeddings_indexed: 30,
  files_indexed: 10,
  files_skipped: 1,
  indexed_at: "2026-06-21T10:40:00Z",
  parser_errors: [],
  repository_id: 7,
  status: "indexed",
  symbols_indexed: 20,
  warnings: [],
};

function useRepositoryHandlers() {
  server.use(
    http.get(`${apiBaseUrl}/repositories/7`, () => HttpResponse.json(repository)),
    http.get(`${apiBaseUrl}/repositories/7/index/status`, () =>
      HttpResponse.json(indexStatus),
    ),
  );
}

describe("RepositoryDetailPage", () => {
  it("renders repository identity and index status", async () => {
    mockRouter();
    useRepositoryHandlers();

    renderWithProviders(<RepositoryDetailPage repositoryId={7} />);

    expect(
      await screen.findByRole("heading", { name: "repolens" }),
    ).toBeInTheDocument();
    expect(screen.getByText("abc123")).toBeInTheDocument();
    expect(screen.getByText("Files")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
  });

  it("submits an index request", async () => {
    const bodies: unknown[] = [];
    mockRouter();
    useRepositoryHandlers();
    server.use(
      http.post(`${apiBaseUrl}/repositories/7/index`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(indexResponse);
      }),
    );

    renderWithProviders(<RepositoryDetailPage repositoryId={7} />);

    await screen.findByRole("heading", { name: "repolens" });
    fireEvent.change(screen.getByLabelText("Ref"), {
      target: { value: "development" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run index" }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toEqual({ ref: "development" });
    expect(await screen.findByText(/Indexed 10 files/)).toBeInTheDocument();
  });

  it("deletes a repository after confirmation", async () => {
    const push = mockRouter();
    useRepositoryHandlers();
    server.use(
      http.delete(
        `${apiBaseUrl}/repositories/7`,
        () => new HttpResponse(null, { status: 204 }),
      ),
    );

    renderWithProviders(<RepositoryDetailPage repositoryId={7} />);

    await screen.findByRole("heading", { name: "repolens" });
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    fireEvent.click(
      within(screen.getByRole("dialog", { name: "Delete repository" })).getByRole(
        "button",
        { name: "Delete repository" },
      ),
    );

    await waitFor(() => expect(push).toHaveBeenCalledWith("/repositories"));
  });
});
