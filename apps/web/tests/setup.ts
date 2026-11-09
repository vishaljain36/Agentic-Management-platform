import "@testing-library/jest-dom/vitest";
import { beforeAll, afterEach, afterAll } from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

// Global DOM Polyfills for jsdom & React Flow
if (typeof window !== "undefined") {
  if (!window.ResizeObserver) {
    window.ResizeObserver = class ResizeObserver {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  }

  if (!window.DOMMatrixReadOnly) {
    // @ts-expect-error minimal mock
    window.DOMMatrixReadOnly = class DOMMatrixReadOnly {
      m11 = 1;
      m22 = 1;
      m41 = 0;
      m42 = 0;
    };
  }

  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

// Default MSW Handlers
export const handlers = [
  http.get("/api/v1/auth/session", () => {
    return HttpResponse.json({
      user: { id: "usr_mock_1", email: "qa_admin@test.com", role: "ADMIN" },
      session: { token: "jwt_mock_valid_999", expires: "2099-01-01" },
    });
  }),
  http.post("http://localhost:8000/api/v1/workflow/resume/:runId", () => {
    return HttpResponse.json({ status: "RESUMED", success: true });
  }),
  http.post("/api/v1/runs/:runId/hitl-resume", () => {
    return HttpResponse.json({ status: "RESUMED", success: true });
  }),
  http.post("/api/v1/agents", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      { id: `agent_${Date.now()}`, ...body, status: "created" },
      { status: 201 }
    );
  }),
];

export const server = setupServer(...handlers);

beforeAll(() => (server.listen as any)({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
