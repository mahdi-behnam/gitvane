import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DeleteRepoModal } from "./delete-repo-modal";

describe("DeleteRepoModal", () => {
  it("disables deletion button until exact repo name is typed", () => {
    const onConfirm = vi.fn();
    const onOpenChange = vi.fn();

    render(
      <DeleteRepoModal
        onConfirm={onConfirm}
        onOpenChange={onOpenChange}
        open={true}
        repositoryName="my-awesome-repo"
      />,
    );

    const deleteBtn = screen.getByRole("button", { name: "Delete repository" });
    expect(deleteBtn).toBeDisabled();

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "wrong-name" } });
    expect(deleteBtn).toBeDisabled();

    fireEvent.change(input, { target: { value: "my-awesome-repo" } });
    expect(deleteBtn).not.toBeDisabled();

    fireEvent.click(deleteBtn);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("renders error message when error prop is provided", () => {
    render(
      <DeleteRepoModal
        error="Failed to delete repository"
        onConfirm={vi.fn()}
        onOpenChange={vi.fn()}
        open={true}
        repositoryName="repo-1"
      />,
    );

    expect(screen.getByText("Failed to delete repository")).toBeInTheDocument();
  });
});
