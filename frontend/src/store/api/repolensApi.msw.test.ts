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
});
