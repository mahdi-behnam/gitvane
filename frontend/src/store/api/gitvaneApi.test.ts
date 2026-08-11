import { describe, expect, it } from "vitest";
import { gitvaneApi } from "@/store/api/gitvaneApi";
import { makeStore } from "@/store/store";

describe("gitvaneApi", () => {
  it("registers backend endpoint hooks", () => {
    const endpointNames = Object.keys(gitvaneApi.endpoints);

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

    expect(store.getState()).toHaveProperty(gitvaneApi.reducerPath);
  });
});
