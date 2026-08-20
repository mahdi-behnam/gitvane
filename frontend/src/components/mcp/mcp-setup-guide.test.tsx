import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { McpSetupGuide } from "@/components/mcp/mcp-setup-guide";
import { ToastProvider } from "@/components/ui/toast";
import { renderWithProviders } from "@/test/render";

describe("McpSetupGuide", () => {
  it("renders client tabs and exposed tools overview", () => {
    renderWithProviders(
      <ToastProvider>
        <McpSetupGuide />
      </ToastProvider>,
    );

    expect(
      screen.getByRole("heading", { name: "AI Agent & MCP Setup Guide" }),
    ).toBeInTheDocument();

    // Check tabs
    expect(screen.getByRole("tab", { name: "Antigravity" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "OpenAI Codex" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Claude Desktop" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Cursor IDE" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Claude Code" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Windsurf / Generic" })).toBeInTheDocument();

    // Check tools section
    expect(
      screen.getByRole("heading", {
        name: "Exposed MCP Tools & Agent Intelligence",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("gitvane_analyze_impact")).toBeInTheDocument();
    expect(screen.getByText("gitvane_recommend_tests")).toBeInTheDocument();
    expect(screen.getByText("gitvane_get_file_risk")).toBeInTheDocument();
  });

  it("switches tabs and displays client-specific configuration", () => {
    renderWithProviders(
      <ToastProvider>
        <McpSetupGuide />
      </ToastProvider>,
    );

    // Click Claude Code tab
    const claudeCodeTab = screen.getByRole("tab", { name: "Claude Code" });
    fireEvent.pointerDown(claudeCodeTab);
    fireEvent.click(claudeCodeTab);

    expect(
      screen.getByRole("heading", { name: "Claude Code Integration" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/claude mcp add gitvane -- uvx gitvane-mcp/),
    ).toBeInTheDocument();

    // Click Cursor tab
    const cursorTab = screen.getByRole("tab", { name: "Cursor IDE" });
    fireEvent.pointerDown(cursorTab);
    fireEvent.click(cursorTab);

    expect(
      screen.getByRole("heading", { name: "Cursor IDE Integration" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/File location:/)).toBeInTheDocument();
    expect(screen.getByText(/\.cursor\/mcp\.json/)).toBeInTheDocument();
  });

  it("updates snippets when custom server URL and API key are entered", () => {
    renderWithProviders(
      <ToastProvider>
        <McpSetupGuide />
      </ToastProvider>,
    );

    const urlInput = screen.getByLabelText(/gitvane server url/i);
    fireEvent.change(urlInput, {
      target: { value: "https://api.gitvane.corp.internal" },
    });

    const keyInput = screen.getByLabelText(/personal api key/i);
    fireEvent.change(keyInput, {
      target: { value: "gv_live_custom_token_123" },
    });

    // Check snippet updates
    expect(
      screen.getByText(/https:\/\/api\.gitvane\.corp\.internal/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/gv_live_custom_token_123/),
    ).toBeInTheDocument();
  });

  it("copies snippet to clipboard when copy button is clicked", async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: writeTextMock,
      },
      writable: true,
      configurable: true,
    });

    renderWithProviders(
      <ToastProvider>
        <McpSetupGuide />
      </ToastProvider>,
    );

    const copyBtn = screen.getByRole("button", {
      name: /copy configuration/i,
    });
    fireEvent.click(copyBtn);

    expect(writeTextMock).toHaveBeenCalled();
    expect(await screen.findByText("Copied!")).toBeInTheDocument();
  });
});
