import { describe, expect, it } from "vitest";
import { repolensApi } from "@/store/api/repolensApi";
import { makeStore } from "@/store/store";

describe("repolensApi MSW integration", () => {
  it("reads health through the configured API base URL", async () => {
    const store = makeStore();

    const result = await store.dispatch(repolensApi.endpoints.getHealth.initiate());

    expect(result.data).toMatchObject({
      database: "connected",
      status: "healthy",
    });
  });

  it("reads the empty repository list fixture", async () => {
    const store = makeStore();

    const result = await store.dispatch(
      repolensApi.endpoints.listRepositories.initiate(),
    );

    expect(result.data).toMatchObject({
      items: [],
      total: 0,
    });
  });

  it("reads default fixtures for core repository workflows", async () => {
    const store = makeStore();

    const repository = await store.dispatch(
      repolensApi.endpoints.getRepository.initiate(7),
    );
    const risk = await store.dispatch(
      repolensApi.endpoints.getRepositoryRisk.initiate({
        repositoryId: 7,
        top_k: 3,
      }),
    );
    const graph = await store.dispatch(
      repolensApi.endpoints.getRepositorySubgraph.initiate({
        repositoryId: 7,
      }),
    );
    const evaluation = await store.dispatch(
      repolensApi.endpoints.getEvaluationStatus.initiate(42),
    );

    expect(repository.data).toMatchObject({ id: 7, name: "repolens" });
    expect(risk.data?.files[0]).toMatchObject({
      path: "backend/app/services/indexing_service.py",
    });
    expect(graph.data?.nodes.length).toBeGreaterThan(0);
    expect(evaluation.data).toMatchObject({
      evaluation_run_id: 42,
      status: "completed",
    });
  });
});
