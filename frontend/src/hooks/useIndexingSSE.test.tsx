import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ToastProvider } from "@/components/ui/toast";
import { useIndexingSSE } from "./useIndexingSSE";

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  withCredentials?: boolean;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  listeners: Record<string, ((event: MessageEvent) => void)[]> = {};
  closed = false;

  constructor(url: string, options?: { withCredentials?: boolean }) {
    this.url = url;
    this.withCredentials = options?.withCredentials;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type].push(listener);
  }

  removeEventListener(type: string, listener: (event: MessageEvent) => void) {
    if (this.listeners[type]) {
      this.listeners[type] = this.listeners[type].filter((l) => l !== listener);
    }
  }

  emit(type: string, data: unknown) {
    const event = new MessageEvent(type, { data: JSON.stringify(data) });
    if (type === "message" && this.onmessage) {
      this.onmessage(event);
    }
    if (this.listeners[type]) {
      this.listeners[type].forEach((l) => l(event));
    }
  }

  emitOpen() {
    if (this.onopen) this.onopen();
  }

  emitError() {
    if (this.onerror) this.onerror();
  }

  close() {
    this.closed = true;
  }
}

global.EventSource = MockEventSource as unknown as typeof EventSource;

describe("useIndexingSSE hook & Toast integration", () => {
  it("subscribes to SSE stream and returns progress", async () => {
    const { result } = renderHook(
      () =>
        useIndexingSSE({
          enabled: true,
          repositoryId: "repo-123",
        }),
      { wrapper: ToastProvider }
    );

    expect(MockEventSource.instances.length).toBeGreaterThan(0);
    const es = MockEventSource.instances[MockEventSource.instances.length - 1];
    expect(es.url).toContain("/repositories/repo-123/index/events");

    act(() => {
      es.emitOpen();
    });

    expect(result.current.connectionState).toBe("connected");

    act(() => {
      es.emit("progress", {
        repository_id: "repo-123",
        status: "indexing",
        progress_percentage: 45.0,
        files_processed: 9,
        files_total: 20,
        chunks_processed: 45,
        chunks_total: 100,
        phase: "indexing",
        phase_name: "Phase 2/4: Chunking & Indexing",
        error: null,
      });
    });

    expect(result.current.progress?.progress_percentage).toBe(45.0);
    expect(result.current.progress?.files_processed).toBe(9);
  });

  it("triggers success toast and calls onComplete when indexing succeeds", async () => {
    const onComplete = vi.fn();

    function TestComponent() {
      const { progress, connectionState } = useIndexingSSE({
        enabled: true,
        repositoryId: "repo-456",
        onComplete,
      });

      return (
        <div>
          <span data-testid="status">{connectionState}</span>
          <span data-testid="progress">{progress?.progress_percentage}</span>
        </div>
      );
    }

    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    const es = MockEventSource.instances[MockEventSource.instances.length - 1];

    act(() => {
      es.emitOpen();
    });

    act(() => {
      es.emit("progress", {
        repository_id: "repo-456",
        status: "indexed",
        progress_percentage: 100.0,
        files_processed: 20,
        files_total: 20,
        chunks_processed: 100,
        chunks_total: 100,
        phase: "completed",
        phase_name: "Phase 4/4: Complete",
        error: null,
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("completed");
    });

    expect(onComplete).toHaveBeenCalled();
    expect(await screen.findByText("Indexing Complete")).toBeDefined();
    expect(await screen.findByText("Repository indexing completed successfully.")).toBeDefined();
  });

  it("triggers destructive toast and calls onError when indexing fails", async () => {
    const onError = vi.fn();

    function TestComponent() {
      const { connectionState, error } = useIndexingSSE({
        enabled: true,
        repositoryId: "repo-789",
        onError,
      });

      return (
        <div>
          <span data-testid="status">{connectionState}</span>
          <span data-testid="error">{error}</span>
        </div>
      );
    }

    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    const es = MockEventSource.instances[MockEventSource.instances.length - 1];

    act(() => {
      es.emitOpen();
    });

    act(() => {
      es.emit("progress", {
        repository_id: "repo-789",
        status: "index_failed",
        progress_percentage: 30.0,
        files_processed: 5,
        files_total: 20,
        chunks_processed: 20,
        chunks_total: 100,
        phase: "failed",
        phase_name: "Phase 2/4: Chunking & Indexing",
        error: "Syntax error in file main.py",
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("error");
    });

    expect(onError).toHaveBeenCalledWith("Syntax error in file main.py");
    expect(await screen.findByText("Indexing Failed")).toBeDefined();
    const matchingElements = await screen.findAllByText("Syntax error in file main.py");
    expect(matchingElements.length).toBeGreaterThanOrEqual(1);
  });
});
