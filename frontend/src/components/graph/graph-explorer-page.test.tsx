import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { GraphExplorerPage } from "@/components/graph/graph-explorer-page";
import { apiBaseUrl } from "@/lib/api/client";
import type { GraphResponse, Repository } from "@/lib/api/types";
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

const graphResponse: GraphResponse = {
  edges: [
    {
      confidence: 0.86,
      edge_type: "imports",
      evidence: { import: "IndexingService" },
      id: 31,
      source_file_id: 1,
      source_path: "backend/app/api/v1/endpoints/indexing.py",
      target_file_id: 2,
      target_path: "backend/app/services/indexing_service.py",
    },
  ],
  nodes: [
    {
      id: 1,
      is_generated: false,
      is_test: false,
      language: "python",
      loc: 80,
      path: "backend/app/api/v1/endpoints/indexing.py",
    },
    {
      id: 2,
      is_generated: false,
      is_test: false,
      language: "python",
      loc: 240,
      path: "backend/app/services/indexing_service.py",
    },
    {
      id: 3,
      is_generated: false,
      is_test: true,
      language: "python",
      loc: 120,
      path: "backend/tests/test_indexing.py",
    },
  ],
  repository_id: "77777777-7777-7777-7777-777777777777",
};

const neighborResponse: GraphResponse = {
  edges: graphResponse.edges,
  nodes: graphResponse.nodes.slice(0, 2),
  repository_id: "77777777-7777-7777-7777-777777777777",
};

function useRepositoryHandler() {
  server.use(
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777`, () => HttpResponse.json(repository)),
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777/languages`, () => HttpResponse.json(["python"])),
    http.get(`${apiBaseUrl}/repositories/77777777-7777-7777-7777-777777777777/files/search`, () => HttpResponse.json([])),
  );
}

describe("GraphExplorerPage", () => {
  it("renders repository subgraph nodes, edges, and controls", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/graph/repositories/77777777-7777-7777-7777-777777777777/subgraph`, () =>
        HttpResponse.json(graphResponse),
      ),
    );

    renderWithProviders(<GraphExplorerPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    expect(await screen.findByText("Repository subgraph")).toBeInTheDocument();
    expect(
      await screen.findByText("backend/app/services/indexing_service.py"),
    ).toBeInTheDocument();
    expect(screen.getByText("3 nodes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Apply" })).toBeInTheDocument();
  });

  it("applies graph filters to the subgraph request", async () => {
    const requests: string[] = [];
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/graph/repositories/77777777-7777-7777-7777-777777777777/subgraph`, ({ request }) => {
        requests.push(request.url);
        return HttpResponse.json(graphResponse);
      }),
    );

    renderWithProviders(<GraphExplorerPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    await waitFor(() => expect(requests.length).toBeGreaterThan(0));
    fireEvent.change(screen.getByRole("spinbutton", { name: /Max nodes/ }), {
      target: { value: "50" },
    });
    fireEvent.click(screen.getByLabelText("Language filter"));
    const pythonOption = await screen.findByRole("button", { name: "python" });
    fireEvent.click(pythonOption);
    fireEvent.click(screen.getByLabelText("Include tests"));
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    await waitFor(() => expect(requests.length).toBeGreaterThan(1));
    const lastRequest = new URL(requests.at(-1) ?? "");
    expect(lastRequest.searchParams.get("max_nodes")).toBe("50");
    expect(lastRequest.searchParams.get("language")).toBe("python");
    expect(lastRequest.searchParams.get("include_tests")).toBe("false");
  });

  it("selects a node and renders file neighbors", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/graph/repositories/77777777-7777-7777-7777-777777777777/subgraph`, () =>
        HttpResponse.json(graphResponse),
      ),
      http.get(`${apiBaseUrl}/graph/repositories/77777777-7777-7777-7777-777777777777/file/2/neighbors`, () =>
        HttpResponse.json(neighborResponse),
      ),
    );

    renderWithProviders(<GraphExplorerPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    const serviceNode = await screen.findByText(
      "backend/app/services/indexing_service.py",
    );
    fireEvent.click(serviceNode);

    const panel = await screen.findByText("File neighbors");
    expect(panel).toBeInTheDocument();
    expect(await screen.findByText("240")).toBeInTheDocument();
    expect(
      screen.getAllByText(/backend\/app\/api\/v1\/endpoints\/indexing.py/).length,
    ).toBeGreaterThan(0);
  });

  it("switches graph views via the view switcher buttons", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/graph/repositories/77777777-7777-7777-7777-777777777777/subgraph`, () =>
        HttpResponse.json(graphResponse),
      ),
    );

    renderWithProviders(<GraphExplorerPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    expect(await screen.findByText("Repository subgraph")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Dependency Tree View" }));
    expect(await screen.findByText("Hierarchical Module Directory Tree")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Risk/Impact Matrix View" }));
    expect(await screen.findByText("Risk & Impact Matrix View")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Hierarchy View" }));
    expect(await screen.findByText("Architecture Layer Hierarchy View")).toBeInTheDocument();
  });

  it("renders large graph and search empty states", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/graph/repositories/77777777-7777-7777-7777-777777777777/subgraph`, () =>
        HttpResponse.json({
          ...graphResponse,
          nodes: graphResponse.nodes.slice(0, 1),
        }),
      ),
    );

    renderWithProviders(<GraphExplorerPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    await screen.findByText("backend/app/api/v1/endpoints/indexing.py");
    fireEvent.change(screen.getByRole("spinbutton", { name: /Max nodes/ }), {
      target: { value: "1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(
      await screen.findByText(/current node limit reached/i),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Node search"));
    fireEvent.change(screen.getByPlaceholderText("Type file path..."), {
      target: { value: "does-not-match" },
    });
    const useButton = await screen.findByRole("button", { name: /Use / });
    fireEvent.click(useButton);
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(await screen.findByText("No matching nodes")).toBeInTheDocument();
  });

  it("renders an empty graph response", async () => {
    useRepositoryHandler();
    server.use(
      http.get(`${apiBaseUrl}/graph/repositories/77777777-7777-7777-7777-777777777777/subgraph`, () =>
        HttpResponse.json({ ...graphResponse, edges: [], nodes: [] }),
      ),
    );

    renderWithProviders(<GraphExplorerPage repositoryId="77777777-7777-7777-7777-777777777777" />);

    expect(await screen.findByText("No graph nodes")).toBeInTheDocument();
  });
});
