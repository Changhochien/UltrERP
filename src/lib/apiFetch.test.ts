import { afterEach, describe, expect, it, vi } from "vitest";

const authStorageMocks = vi.hoisted(() => ({
  clearStoredToken: vi.fn(),
  getStoredToken: vi.fn<() => string | null>(() => null),
}));

vi.mock("./authStorage", () => ({
  clearStoredToken: authStorageMocks.clearStoredToken,
  getStoredToken: authStorageMocks.getStoredToken,
}));

afterEach(() => {
  vi.restoreAllMocks();
  authStorageMocks.clearStoredToken.mockReset();
  authStorageMocks.getStoredToken.mockReset();
  authStorageMocks.getStoredToken.mockReturnValue(null);
});

describe("apiFetch", () => {
  it("adds application/json when the caller sends a string body without a content type", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 200 }),
    );

    const { apiFetch } = await import("./apiFetch");
    await apiFetch("/api/v1/inventory/reorder-points/compute", {
      method: "POST",
      body: JSON.stringify({ safety_factor: 0.5 }),
    });

    const [, init] = fetchMock.mock.calls[0] ?? [];
    const headers = new Headers((init as RequestInit | undefined)?.headers);
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("preserves a caller-provided content type", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 200 }),
    );

    const { apiFetch } = await import("./apiFetch");
    await apiFetch("/api/v1/test", {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: "raw-text",
    });

    const [, init] = fetchMock.mock.calls[0] ?? [];
    const headers = new Headers((init as RequestInit | undefined)?.headers);
    expect(headers.get("Content-Type")).toBe("text/plain");
  });
});