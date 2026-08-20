import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GitVaneLoader } from "@/components/ui/gitvane-loader";

describe("GitVaneLoader", () => {
  it("renders with default 'Please Wait...' text and accessibility role", () => {
    render(<GitVaneLoader />);

    const loader = screen.getByRole("status");
    expect(loader).toBeInTheDocument();
    expect(screen.getByText("Please Wait")).toBeInTheDocument();
  });

  it("renders with custom text and subtext", () => {
    render(
      <GitVaneLoader
        text="Indexing Workspace..."
        subtext="Analyzing dependency graph"
        size="lg"
      />
    );

    expect(screen.getByText("Indexing Workspace")).toBeInTheDocument();
    expect(screen.getByText("Analyzing dependency graph")).toBeInTheDocument();
  });

  it("supports hiding text when text is false", () => {
    render(<GitVaneLoader text={false} />);

    expect(screen.queryByText("Please Wait")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders in fullScreen container when fullScreen is true", () => {
    const { container } = render(<GitVaneLoader fullScreen />);

    expect(container.firstChild).toHaveClass("min-h-screen");
  });
});
