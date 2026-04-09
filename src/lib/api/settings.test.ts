import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();

vi.mock("../apiFetch", () => ({
  apiFetch: (...args: Parameters<typeof apiFetchMock>) => apiFetchMock(...args),
}));

afterEach(() => {
  vi.clearAllMocks();
  vi.resetModules();
});

describe("getSettings", () => {
  it("requests the settings collection with a trailing slash", async () => {
    apiFetchMock.mockResolvedValue(
      new Response("[]", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { getSettings } = await import("./settings");
    await getSettings();

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/settings/");
  });
});