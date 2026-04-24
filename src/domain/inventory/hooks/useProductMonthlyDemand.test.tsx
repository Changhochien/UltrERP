import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useProductMonthlyDemand } from "./useProductMonthlyDemand";

const apiFetchMock = vi.fn();

vi.mock("../../../lib/apiFetch", () => ({
  apiFetch: (...args: Parameters<typeof apiFetchMock>) => apiFetchMock(...args),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("useProductMonthlyDemand", () => {
  it("threads the selected month range into the API request", async () => {
    apiFetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [{ month: "2026-04", total_qty: 5 }],
        total: 5,
      }),
    });

    const { result } = renderHook(() =>
      useProductMonthlyDemand("product-1", {
        months: 48,
        includeCurrentMonth: false,
      }),
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/inventory/products/product-1/monthly-demand?months=48&include_current_month=false",
    );
    expect(result.current.items).toEqual([{ month: "2026-04", total_qty: 5 }]);
    expect(result.current.total).toBe(5);
  });
});