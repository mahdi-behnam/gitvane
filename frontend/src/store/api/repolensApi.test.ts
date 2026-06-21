import { describe, expect, it } from "vitest";
import { repolensApi } from "@/store/api/repolensApi";
import { makeStore } from "@/store/store";

describe("repolensApi", () => {
  it("registers repository and health endpoints", () => {
    const endpointNames = Object.keys(repolensApi.endpoints);

    expect(endpointNames).toEqual(
      expect.arrayContaining([
        "createRepository",
        "deleteRepository",
        "getHealth",
        "getIndexStatus",
        "getRepository",
        "indexRepository",
        "listRepositories",
      ]),
    );
  });

  it("mounts the RTK Query reducer in the store", () => {
    const store = makeStore();

    expect(store.getState()).toHaveProperty(repolensApi.reducerPath);
  });
});
