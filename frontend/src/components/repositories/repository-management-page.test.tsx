import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse, delay } from "msw";
import { describe, expect, it } from "vitest";
import { RepositoryManagementPage } from "@/components/repositories/repository-management-page";
import { apiBaseUrl } from "@/lib/api/client";
import type { Repository, RepositoryList } from "@/lib/api/types";
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

    expect(await screen.findByText("repolens")).toBeInTheDocument();
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
          repository_id: 7,
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

    await screen.findByText("repolens");
    fireEvent.click(screen.getByRole("button", { name: "Index" }));
    await waitFor(() => expect(indexBodies).toEqual([{}]));

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
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

  it("submits clone URL and local path variants", async () => {
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
      target: { value: "repolens" },
    });
    fireEvent.change(screen.getByLabelText("Clone URL"), {
      target: { value: "https://github.com/mahdi-behnam/repolens.git" },
    });
    fireEvent.click(
      within(screen.getByRole("dialog", { name: "Add repository" })).getByRole(
        "button",
        { name: "Add repository" },
      ),
    );

    await waitFor(() => expect(bodies).toHaveLength(1));

    fireEvent.click(screen.getByRole("button", { name: "Add repository" }));
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "local-repo" },
    });
    fireEvent.change(screen.getByLabelText("Local path"), {
      target: { value: "D:\\Dev\\Repos\\repolens" },
    });
    fireEvent.click(
      within(screen.getByRole("dialog", { name: "Add repository" })).getByRole(
        "button",
        { name: "Add repository" },
      ),
    );

    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies).toEqual([
      expect.objectContaining({
        clone_url: "https://github.com/mahdi-behnam/repolens.git",
        local_path: null,
      }),
      expect.objectContaining({
        clone_url: null,
        local_path: "D:\\Dev\\Repos\\repolens",
      }),
    ]);
  });
});
