import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { vi } from "vitest";
import { server } from "@/test/server";

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    addEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
    matches: false,
    media: query,
    onchange: null,
    removeEventListener: vi.fn(),
  })),
});

class ResizeObserverMock {
  disconnect = vi.fn();
  observe = vi.fn();
  unobserve = vi.fn();
}

Object.defineProperty(window, "ResizeObserver", {
  writable: true,
  value: ResizeObserverMock,
});

class EventSourceMock {
  close = vi.fn();
  addEventListener = vi.fn();
  removeEventListener = vi.fn();
  onopen: any = null;
  onmessage: any = null;
  onerror: any = null;
  constructor(public url: string, public options?: any) {}
}

Object.defineProperty(window, "EventSource", {
  writable: true,
  value: EventSourceMock,
});

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
