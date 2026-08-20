import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { ApiKeysCard } from "@/components/mcp/api-keys-card";
import { ToastProvider } from "@/components/ui/toast";
import { apiBaseUrl } from "@/lib/api/client";
import { renderWithProviders } from "@/test/render";
import { server } from "@/test/server";

describe("ApiKeysCard", () => {
  it("renders active API keys from the server", async () => {
    renderWithProviders(
      <ToastProvider>
        <ApiKeysCard />
      </ToastProvider>,
    );

    expect(await screen.findByText("Personal API Keys")).toBeInTheDocument();
    expect(await screen.findByText("Cursor IDE")).toBeInTheDocument();
    expect(screen.getByText(/gv_live_abc12345/)).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create new key/i })).toBeInTheDocument();
  });

  it("handles empty API key list", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api-keys`, () => HttpResponse.json([])),
    );

    renderWithProviders(
      <ToastProvider>
        <ApiKeysCard />
      </ToastProvider>,
    );

    expect(await screen.findByText("No API Keys Generated")).toBeInTheDocument();
    expect(
      screen.getByText(/No API keys found\. Create a personal API key/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /create first key/i }),
    ).toBeInTheDocument();
  });

  it("opens create modal, submits, and displays raw secret key modal", async () => {
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
        <ApiKeysCard />
      </ToastProvider>,
    );

    const createBtn = await screen.findByRole("button", {
      name: /create new key/i,
    });
    fireEvent.click(createBtn);

    // Dialog title
    expect(
      screen.getByRole("heading", { name: "Create New Personal API Key" }),
    ).toBeInTheDocument();

    const nameInput = screen.getByLabelText(/key name \/ description/i);
    fireEvent.change(nameInput, { target: { value: "Antigravity Dev Agent" } });

    const submitBtn = screen.getByRole("button", { name: /generate key/i });
    fireEvent.click(submitBtn);

    // Should open "Save Your Personal API Key" dialog
    expect(
      await screen.findByRole("heading", {
        name: "Save Your Personal API Key",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("gv_live_xyz9876543210abcdef"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Store this secret key securely/i),
    ).toBeInTheDocument();

    const copyBtn = screen.getByRole("button", { name: /copy/i });
    fireEvent.click(copyBtn);

    expect(writeTextMock).toHaveBeenCalledWith("gv_live_xyz9876543210abcdef");
    expect(await screen.findByText("Copied!")).toBeInTheDocument();

    // Close modal
    const closeBtn = screen.getByRole("button", {
      name: /i have copied my key/i,
    });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(
        screen.queryByRole("heading", { name: "Save Your Personal API Key" }),
      ).not.toBeInTheDocument();
    });
  });

  it("opens revoke confirmation dialog and revokes a key", async () => {
    let revokedId = "";

    server.use(
      http.delete(`${apiBaseUrl}/api-keys/:id`, ({ params }) => {
        revokedId = params.id as string;
        return HttpResponse.json(null);
      }),
    );

    renderWithProviders(
      <ToastProvider>
        <ApiKeysCard />
      </ToastProvider>,
    );

    const revokeBtn = await screen.findByRole("button", {
      name: /revoke key cursor ide/i,
    });
    fireEvent.click(revokeBtn);

    expect(
      await screen.findByRole("heading", { name: "Revoke Personal API Key" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Are you sure you want to revoke "Cursor IDE"\?/),
    ).toBeInTheDocument();

    const confirmRevokeBtn = screen.getByRole("button", { name: /^revoke key$/i });
    fireEvent.click(confirmRevokeBtn);

    await waitFor(() => {
      expect(revokedId).toBe("key-123");
    });
  });

  it("renders error state when fetch fails", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api-keys`, () =>
        new HttpResponse(null, { status: 500 }),
      ),
    );

    renderWithProviders(
      <ToastProvider>
        <ApiKeysCard />
      </ToastProvider>,
    );

    expect(await screen.findByText(/Failed to load API keys/)).toBeInTheDocument();
  });
});
