import { describe, expect, it } from "vitest";
import { repolensApi } from "@/store/api/repolensApi";
import { makeStore } from "@/store/store";

describe("repolensApi", () => {
  it("registers backend endpoint hooks", () => {
    const endpointNames = Object.keys(repolensApi.endpoints);

    expect(endpointNames).toEqual(
      expect.arrayContaining([
        "createRepository",
        "deleteRepository",
        "getEvaluationReport",
        "getEvaluationReportMarkdown",
        "getEvaluationStatus",
        "getFileNeighbors",
        "getHealth",
        "getImpactRun",
        "getIndexStatus",
        "getRepository",
        "getRepositoryRisk",
        "getRepositorySubgraph",
        "indexRepository",
        "listRepositories",
        "recommendTests",
        "runEvaluation",
        "runImpactAnalysis",
        "semanticSearch",
        "forgotPassword",
        "resetPassword",
        "updateMe",
      ]),
    );
  });

  it("mounts the RTK Query reducer in the store", () => {
    const store = makeStore();

    expect(store.getState()).toHaveProperty(repolensApi.reducerPath);
  });
});
