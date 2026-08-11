import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { apiBaseUrl } from "@/lib/api/client";
import { gitvaneApi } from "@/store/api/gitvaneApi";
import { makeStore } from "@/store/store";
import { setCredentials } from "@/store/slices/authSlice";

describe("gitvaneApi MSW integration", () => {
  it("fetches health status successfully", async () => {
    const store = makeStore();

    const result = await store.dispatch(gitvaneApi.endpoints.getHealth.initiate());

    expect(result.data).toMatchObject({
      database: "connected",
      status: "healthy",
    });
  });

  it("reads the empty repository list fixture", async () => {
    const store = makeStore();

    const result = await store.dispatch(
      gitvaneApi.endpoints.listRepositories.initiate(),
    );

    expect(result.data).toMatchObject({
      items: [],
      total: 0,
    });
  });

  it("reads default fixtures for core repository workflows", async () => {
    const store = makeStore();

    const repository = await store.dispatch(
      gitvaneApi.endpoints.getRepository.initiate("77777777-7777-7777-7777-777777777777"),
    );
    const risk = await store.dispatch(
      gitvaneApi.endpoints.getRepositoryRisk.initiate({
        repositoryId: "77777777-7777-7777-7777-777777777777",
        top_k: 3,
      }),
    );
    const graph = await store.dispatch(
      gitvaneApi.endpoints.getRepositorySubgraph.initiate({
        repositoryId: "77777777-7777-7777-7777-777777777777",
      }),
    );
    const evaluation = await store.dispatch(
      gitvaneApi.endpoints.getEvaluationStatus.initiate(42),
    );

    expect(repository.data).toMatchObject({ id: "77777777-7777-7777-7777-777777777777", name: "gitvane" });
    expect(risk.data?.files[0]).toMatchObject({
      path: "backend/app/services/indexing_service.py",
    });
    expect(graph.data?.nodes.length).toBeGreaterThan(0);
    expect(evaluation.data).toMatchObject({
      evaluation_run_id: 42,
      status: "completed",
    });
  });

  it("automatically refreshes access token and retries query when receiving 401", async () => {
    const store = makeStore();
    store.dispatch(setCredentials({ accessToken: "expired-token" }));

    let attempts = 0;
    server.use(
      http.get(`${apiBaseUrl}/repositories`, ({ request }) => {
        attempts++;
        const authHeader = request.headers.get("Authorization");
        if (authHeader === "Bearer expired-token") {
          return new HttpResponse(null, { status: 401 });
        }
        return HttpResponse.json({ items: [{ id: "1", name: "retried-repo" }], total: 1 });
      }),
      http.post(`${apiBaseUrl}/auth/refresh`, () => {
        return HttpResponse.json({
          access_token: "new-valid-token",
          token_type: "bearer",
        });
      }),
    );

    const result = await store.dispatch(
      gitvaneApi.endpoints.listRepositories.initiate(),
    );

    expect(attempts).toBe(2);
    expect(result.data).toMatchObject({ items: [{ id: "1", name: "retried-repo" }] });
    expect(store.getState().auth.accessToken).toBe("new-valid-token");
  });

  it("clears credentials when token refresh fails on 401", async () => {
    const store = makeStore();
    store.dispatch(setCredentials({ accessToken: "invalid-token" }));

    server.use(
      http.get(`${apiBaseUrl}/repositories`, () => {
        return new HttpResponse(null, { status: 401 });
      }),
      http.post(`${apiBaseUrl}/auth/refresh`, () => {
        return new HttpResponse(null, { status: 401 });
      }),
    );

    const result = await store.dispatch(
      gitvaneApi.endpoints.listRepositories.initiate(),
    );

    expect(result.error).toBeDefined();
    expect(store.getState().auth.accessToken).toBeNull();
  });
});

