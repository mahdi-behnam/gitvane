import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AppShell } from "@/components/app/app-shell";
import { ThemeProvider } from "@/components/theme/theme-provider";
import { ToastProvider } from "@/components/ui/toast";
import { renderWithProviders } from "@/test/render";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

describe("AppShell", () => {
  it("renders navigation and theme controls", async () => {
    renderWithProviders(
      <ThemeProvider>
        <ToastProvider>
          <AppShell>
            <div>Dashboard content</div>
          </AppShell>
        </ToastProvider>
      </ThemeProvider>,
    );

    expect(await screen.findByText("Repo")).toBeInTheDocument();
    expect(screen.getByText("Lens")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /overview/i }).length).toBeGreaterThan(
      0,
    );
    expect(
      screen.getByRole("navigation", { name: "Primary shortcuts" }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { current: "page", name: /overview/i }).length,
    ).toBeGreaterThan(0);
    expect(screen.getByLabelText("Toggle theme")).toBeInTheDocument();
    expect(screen.getByText("Dashboard content")).toBeInTheDocument();
  });
});
