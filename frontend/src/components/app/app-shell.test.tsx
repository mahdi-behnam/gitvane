import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AppShell } from "@/components/app/app-shell";
import { ThemeProvider } from "@/components/theme/theme-provider";
import { ToastProvider } from "@/components/ui/toast";
import { renderWithProviders } from "@/test/render";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("AppShell", () => {
  it("renders navigation and theme controls", () => {
    renderWithProviders(
      <ThemeProvider>
        <ToastProvider>
          <AppShell>
            <div>Dashboard content</div>
          </AppShell>
        </ToastProvider>
      </ThemeProvider>,
    );

    expect(screen.getAllByText("RepoLens").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /overview/i }).length).toBeGreaterThan(
      0,
    );
    expect(screen.getByLabelText("Toggle theme")).toBeInTheDocument();
    expect(screen.getByText("Dashboard content")).toBeInTheDocument();
  });
});
