import { describe, expect, it } from "vitest";
import { normalizeApiError } from "@/lib/api/errors";

describe("normalizeApiError", () => {
  it("classifies backend offline errors", () => {
    expect(
      normalizeApiError({ error: "TypeError: Failed to fetch", status: "FETCH_ERROR" }),
    ).toMatchObject({
      kind: "offline",
      message: "Backend is offline or unreachable.",
    });
  });

  it("classifies validation errors", () => {
    expect(
      normalizeApiError({
        data: { detail: "Must provide either clone_url or local_path" },
        status: 422,
      }),
    ).toMatchObject({
      kind: "validation",
      message: "Must provide either clone_url or local_path",
    });
  });
});
