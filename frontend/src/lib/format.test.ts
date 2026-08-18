import { describe, expect, it } from "vitest";
import {
  formatDateTime,
  formatPercent,
  formatSnakeCase,
  formatTitleCase,
  getRepositoryDisplayBranch,
} from "@/lib/format";

describe("getRepositoryDisplayBranch", () => {
  it("returns user-selected branch when current_ref is a branch name", () => {
    expect(
      getRepositoryDisplayBranch({
        current_ref: "feature/awesome-feature",
        default_branch: "main",
        last_indexed_commit: "59d3e6022e1b12b509ba098b1859bb3962d3a39e",
      }),
    ).toBe("feature/awesome-feature");
  });

  it("prefers default_branch when current_ref is a full 40-character SHA hash", () => {
    expect(
      getRepositoryDisplayBranch({
        current_ref: "59d3e6022e1b12b509ba098b1859bb3962d3a39e",
        default_branch: "main",
        last_indexed_commit: "59d3e6022e1b12b509ba098b1859bb3962d3a39e",
      }),
    ).toBe("main");
  });

  it("prefers default_branch when current_ref matches last_indexed_commit", () => {
    expect(
      getRepositoryDisplayBranch({
        current_ref: "abc1234",
        default_branch: "release-v1",
        last_indexed_commit: "abc1234",
      }),
    ).toBe("release-v1");
  });

  it("falls back to short SHA if only a SHA is available without a default branch", () => {
    expect(
      getRepositoryDisplayBranch({
        current_ref: "59d3e6022e1b12b509ba098b1859bb3962d3a39e",
        default_branch: null,
      }),
    ).toBe("59d3e60");
  });

  it("returns default_branch when current_ref is null", () => {
    expect(
      getRepositoryDisplayBranch({
        current_ref: null,
        default_branch: "main",
      }),
    ).toBe("main");
  });

  it("returns Unknown when no ref or branch is present", () => {
    expect(getRepositoryDisplayBranch(null)).toBe("Unknown");
    expect(
      getRepositoryDisplayBranch({
        current_ref: null,
        default_branch: null,
      }),
    ).toBe("Unknown");
  });
});

describe("format formatting utilities", () => {
  it("formats date times cleanly", () => {
    expect(formatDateTime(null)).toBe("Not indexed");
    expect(formatDateTime("2026-06-21T10:00:00Z")).toContain("2026");
  });

  it("formats snake case to title case words", () => {
    expect(formatSnakeCase("indexing_queued")).toBe("Indexing Queued");
    expect(formatSnakeCase(null)).toBe("");
  });

  it("formats percentages", () => {
    expect(formatPercent(0.854)).toBe("85.4%");
    expect(formatPercent(null)).toBe("0%");
  });

  it("formats title case strings", () => {
    expect(formatTitleCase("structural-dependencies")).toBe("Structural-Dependencies");
  });
});
