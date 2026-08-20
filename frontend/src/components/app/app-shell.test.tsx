import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AppShell, parseJwtExp } from "@/components/app/app-shell";
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

describe("parseJwtExp", () => {
  it("parses valid JWT expiration", () => {
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
    const payload = btoa(JSON.stringify({ sub: "123", exp: 1735689600 }));
    const token = `${header}.${payload}.signature`;

    expect(parseJwtExp(token)).toBe(1735689600);
  });

  it("returns null for malformed token or missing exp claim", () => {
    expect(parseJwtExp("invalid.token")).toBeNull();
    const payloadNoExp = btoa(JSON.stringify({ sub: "123" }));
    expect(parseJwtExp(`header.${payloadNoExp}.sig`)).toBeNull();
  });
});

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

    expect(await screen.findByText("Git")).toBeInTheDocument();
    expect(screen.getByText("Vane")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /overview/i }).length).toBeGreaterThan(
      0,
    );
    const mcpLinks = screen.getAllByRole("link", { name: /mcp & agents/i });
    expect(mcpLinks.length).toBeGreaterThan(0);
    expect(mcpLinks[0]).toHaveAttribute("href", "/mcp");
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

