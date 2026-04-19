import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();

vi.mock("../apiFetch", () => ({
  apiFetch: (...args: Parameters<typeof apiFetchMock>) => apiFetchMock(...args),
}));

function createAbortError() {
  return Object.assign(new Error("The operation was aborted."), { name: "AbortError" });
}

afterEach(() => {
  vi.clearAllMocks();
  vi.resetModules();
});

describe("inventory api client", () => {
  it("rethrows aborted product detail requests", async () => {
    apiFetchMock.mockRejectedValueOnce(createAbortError());

    const { fetchProductDetail } = await import("./inventory");

    await expect(
      fetchProductDetail("product-1", { signal: new AbortController().signal }),
    ).rejects.toMatchObject({ name: "AbortError" });
  });

  it("rethrows aborted inventory valuation requests", async () => {
    apiFetchMock.mockRejectedValueOnce(createAbortError());

    const { fetchInventoryValuation } = await import("./inventory");

    await expect(
      fetchInventoryValuation(
        { warehouseId: "warehouse-1" },
        { signal: new AbortController().signal },
      ),
    ).rejects.toMatchObject({ name: "AbortError" });
  });

  it("rethrows inventory valuation requests canceled with a custom abort reason", async () => {
    const controller = new AbortController();
    controller.abort("useInventoryValuation: unmounting");
    apiFetchMock.mockRejectedValueOnce(controller.signal.reason);

    const { fetchInventoryValuation } = await import("./inventory");

    await expect(
      fetchInventoryValuation(
        { warehouseId: "warehouse-1" },
        { signal: controller.signal },
      ),
    ).rejects.toBe("useInventoryValuation: unmounting");
  });
});
