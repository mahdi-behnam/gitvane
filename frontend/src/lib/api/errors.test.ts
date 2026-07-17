import { describe, expect, it } from "vitest";
import { normalizeApiError } from "@/lib/api/errors";

describe("normalizeApiError", () => {
  it("classifies backend offline errors", () => {
    expect(
      normalizeApiError({ error: "TypeError: Failed to fetch", status: "FETCH_ERROR" }),
    ).toMatchObject({
      kind: "offline",
      message: "The service is offline or unreachable.",
    });
  });

  it("classifies validation errors", () => {
    expect(
      normalizeApiError({
        data: { detail: "Field required" },
        status: 422,
      }),
    ).toMatchObject({
      kind: "validation",
      message: "Field required",
    });
  });
});
