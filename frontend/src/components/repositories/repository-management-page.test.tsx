import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse, delay } from "msw";
import { describe, expect, it } from "vitest";
import { RepositoryManagementPage } from "@/components/repositories/repository-management-page";
import { apiBaseUrl } from "@/lib/api/client";
import type { Repository, RepositoryList } from "@/lib/api/types";
import { renderWithProviders } from "@/test/render";
import { server } from "@/test/server";

const repository: Repository = {
  clone_url: "https://github.com/mahdi-behnam/gitvane.git",
  created_at: "2026-06-21T10:00:00Z",
  current_ref: "main",
  default_branch: "main",
  id: "7",
  indexed_at: "2026-06-21T10:30:00Z",
  last_indexed_commit: "abc123",
  local_path: null,
  name: "gitvane",
  repo_metadata: null,
  status: "indexed",
  updated_at: "2026-06-21T10:30:00Z",
};

function repositoryList(items: Repository[]): RepositoryList {
  return {
    items,
    limit: 100,
    skip: 0,
    total: items.length,
  };
}

describe("RepositoryManagementPage", () => {
  it("renders the loading state", async () => {
    server.use(
      http.get(`${apiBaseUrl}/repositories`, async () => {
        await delay(100);
        return HttpResponse.json(repositoryList([]));
      }),
    );

    renderWithProviders(<RepositoryManagementPage />);

    expect(screen.getByText("Loading repositories")).toBeInTheDocument();
  });

  it("renders the empty state", async () => {
    renderWithProviders(<RepositoryManagementPage />);

    expect(await screen.findByText("No repository records")).toBeInTheDocument();
  });

  it("renders repository records", async () => {
    server.use(
      http.get(`${apiBaseUrl}/repositories`, () =>
        HttpResponse.json(repositoryList([repository])),
      ),
    );

    renderWithProviders(<RepositoryManagementPage />);

    expect(await screen.findByText("gitvane")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View" })).toHaveAttribute(
      "href",
      "/repositories/7",
    );
  });

  it("runs list row index and delete actions", async () => {
    const indexBodies: unknown[] = [];
    let deleted = false;

    server.use(
      http.get(`${apiBaseUrl}/repositories`, () =>
        HttpResponse.json(repositoryList([repository])),
      ),
      http.post(`${apiBaseUrl}/repositories/7/index`, async ({ request }) => {
        indexBodies.push(await request.json());
        return HttpResponse.json({
          chunks_indexed: 1,
          commits_indexed: 1,
          current_ref: "main",
          dependency_edges_indexed: 1,
          embeddings_indexed: 1,
          files_indexed: 1,
          files_skipped: 0,
          indexed_at: "2026-06-21T10:30:00Z",
          parser_errors: [],
          repository_id: "7",
          status: "indexed",
          symbols_indexed: 1,
          warnings: [],
        });
      }),
      http.delete(`${apiBaseUrl}/repositories/7`, () => {
        deleted = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );

    renderWithProviders(<RepositoryManagementPage />);

    await screen.findByText("gitvane");
    fireEvent.click(screen.getByRole("button", { name: "Index" }));
    await waitFor(() => expect(indexBodies).toEqual([{}]));

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const confirmInput = screen.getByPlaceholderText("gitvane");
    fireEvent.change(confirmInput, { target: { value: "gitvane" } });
    fireEvent.click(
      within(screen.getByRole("dialog", { name: "Delete repository" })).getByRole(
        "button",
        { name: "Delete repository" },
      ),
    );

    await waitFor(() => expect(deleted).toBe(true));
  });

  it("renders API errors", async () => {
    server.use(
      http.get(`${apiBaseUrl}/repositories`, () =>
        HttpResponse.json({ detail: "Database unavailable" }, { status: 500 }),
      ),
    );

    renderWithProviders(<RepositoryManagementPage />);

    expect(
      await screen.findByText("Repositories could not be loaded"),
    ).toBeInTheDocument();
  });

  it("submits clone URL when adding repository", async () => {
    const bodies: unknown[] = [];

    server.use(
      http.post(`${apiBaseUrl}/repositories`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(repository, { status: 201 });
      }),
    );

    renderWithProviders(<RepositoryManagementPage />);

    fireEvent.click(screen.getByRole("button", { name: "Add repository" }));
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "gitvane" },
    });
    fireEvent.change(screen.getByLabelText("Clone URL"), {
      target: { value: "https://github.com/mahdi-behnam/gitvane.git" },
    });
    fireEvent.click(
      within(screen.getByRole("dialog", { name: "Add repository" })).getByRole(
        "button",
        { name: "Add repository" },
      ),
    );

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      branch: null,
      clone_url: "https://github.com/mahdi-behnam/gitvane.git",
      index_now: false,
      name: "gitvane",
    });
  });

  it("filters repositories by search query and updates stats", async () => {
    const repos: Repository[] = [
      { ...repository, id: "1", name: "gitvane-backend", status: "indexed" },
      { ...repository, id: "2", name: "frontend-app", status: "indexed" },
      { ...repository, id: "3", name: "analytics-service", status: "indexing" },
    ];

    server.use(
      http.get(`${apiBaseUrl}/repositories`, () =>
        HttpResponse.json(repositoryList(repos)),
      ),
    );

    renderWithProviders(<RepositoryManagementPage />);

    expect(await screen.findByText("gitvane-backend")).toBeInTheDocument();
    expect(screen.getByText("frontend-app")).toBeInTheDocument();
    expect(screen.getByText("analytics-service")).toBeInTheDocument();

    const searchInput = screen.getByLabelText("Search repositories");
    fireEvent.change(searchInput, { target: { value: "frontend" } });

    await waitFor(() => {
      expect(screen.getByText("Showing 1 of 3 repositories")).toBeInTheDocument();
    });
    expect(screen.queryByText("gitvane-backend")).not.toBeInTheDocument();
    expect(screen.getByText("frontend-app")).toBeInTheDocument();
    expect(screen.queryByText("analytics-service")).not.toBeInTheDocument();
  });

  it("filters repositories by status and resets filters", async () => {
    const repos: Repository[] = [
      { ...repository, id: "1", name: "repo-ready", status: "indexed" },
      { ...repository, id: "2", name: "repo-indexing", status: "indexing" },
      { ...repository, id: "3", name: "repo-failed", status: "failed" },
    ];

    server.use(
      http.get(`${apiBaseUrl}/repositories`, () =>
        HttpResponse.json(repositoryList(repos)),
      ),
    );

    renderWithProviders(<RepositoryManagementPage />);

    expect(await screen.findByText("repo-ready")).toBeInTheDocument();

    const statusSelect = screen.getByLabelText("Filter by status");
    fireEvent.change(statusSelect, { target: { value: "indexing" } });

    expect(screen.queryByText("repo-ready")).not.toBeInTheDocument();
    expect(screen.getByText("repo-indexing")).toBeInTheDocument();
    expect(screen.queryByText("repo-failed")).not.toBeInTheDocument();

    const resetButton = screen.getByRole("button", { name: "Reset filters" });
    fireEvent.click(resetButton);

    expect(screen.getByText("repo-ready")).toBeInTheDocument();
    expect(screen.getByText("repo-indexing")).toBeInTheDocument();
    expect(screen.getByText("repo-failed")).toBeInTheDocument();
  });

  it("renders empty state when search filters yield no results", async () => {
    server.use(
      http.get(`${apiBaseUrl}/repositories`, () =>
        HttpResponse.json(repositoryList([repository])),
      ),
    );

    renderWithProviders(<RepositoryManagementPage />);

    expect(await screen.findByText("gitvane")).toBeInTheDocument();

    const searchInput = screen.getByLabelText("Search repositories");
    fireEvent.change(searchInput, { target: { value: "nonexistent-query" } });

    expect(await screen.findByText("No matching repositories")).toBeInTheDocument();
    expect(
      screen.getByText("No repositories match your current search query or status filter."),
    ).toBeInTheDocument();
  });
});