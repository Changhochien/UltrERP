import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { InventoryValuationResponse, ProductDetail } from "../types";
import { useInventoryValuation } from "./useInventoryValuation";
import { useProductDetail } from "./useProductDetail";

const fetchInventoryValuationMock = vi.fn();
const fetchProductDetailMock = vi.fn();

vi.mock("../../../lib/api/inventory", () => ({
  fetchInventoryValuation: (...args: Parameters<typeof fetchInventoryValuationMock>) =>
    fetchInventoryValuationMock(...args),
  fetchProductDetail: (...args: Parameters<typeof fetchProductDetailMock>) =>
    fetchProductDetailMock(...args),
}));

function createAbortError() {
  return Object.assign(new Error("The operation was aborted."), { name: "AbortError" });
}

function createDeferred<T>() {
  let resolvePromise!: (value: T | PromiseLike<T>) => void;
  let rejectPromise!: (reason?: unknown) => void;

  const promise = new Promise<T>((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
  });

  return {
    promise,
    resolve: resolvePromise,
    reject: rejectPromise,
  };
}

const productDetailFixture: ProductDetail = {
  id: "product-2",
  code: "SKU-2",
  name: "Rotor",
  category_id: null,
  category: "Hardware",
  description: "Updated product detail",
  unit: "pcs",
  standard_cost: "12.5000",
  status: "active",
  total_stock: 24,
  warehouses: [],
  adjustment_history: [],
};

const inventoryValuationFixture: InventoryValuationResponse = {
  items: [
    {
      product_id: "product-2",
      product_code: "SKU-2",
      product_name: "Rotor",
      category: "Hardware",
      warehouse_id: "warehouse-2",
      warehouse_name: "Overflow",
      quantity: 24,
      unit_cost: "12.5000",
      extended_value: "300.0000",
      cost_source: "standard_cost",
    },
  ],
  warehouse_totals: [
    {
      warehouse_id: "warehouse-2",
      warehouse_name: "Overflow",
      total_quantity: 24,
      total_value: "300.0000",
      row_count: 1,
    },
  ],
  grand_total_value: "300.0000",
  grand_total_quantity: 24,
  total_rows: 1,
};

afterEach(() => {
  vi.clearAllMocks();
});

describe("inventory hook abort handling", () => {
  it("clears product detail when the selected product is removed", async () => {
    fetchProductDetailMock.mockResolvedValueOnce({ ok: true, data: productDetailFixture });

    const { result, rerender } = renderHook(
      ({ productId }: { productId: string | null }) => useProductDetail(productId),
      { initialProps: { productId: "product-2" } as { productId: string | null } },
    );

    await waitFor(() => {
      expect(result.current.product).toEqual(productDetailFixture);
      expect(result.current.loading).toBe(false);
    });

    rerender({ productId: null });

    await waitFor(() => {
      expect(result.current.product).toBeNull();
      expect(result.current.error).toBeNull();
      expect(result.current.loading).toBe(false);
    });
  });

  it("keeps product detail loading owned by the latest request", async () => {
    const secondRequest = createDeferred<{ ok: true; data: ProductDetail }>();

    fetchProductDetailMock.mockImplementation(
      (productId: string, options?: { signal?: AbortSignal }) => {
        if (productId === "product-1") {
          return new Promise((_resolve, reject) => {
            options?.signal?.addEventListener("abort", () => reject(createAbortError()), {
              once: true,
            });
          });
        }

        return secondRequest.promise;
      },
    );

    const { result, rerender } = renderHook(
      ({ productId }: { productId: string | null }) => useProductDetail(productId),
      { initialProps: { productId: "product-1" } as { productId: string | null } },
    );

    await waitFor(() => {
      expect(fetchProductDetailMock).toHaveBeenCalledTimes(1);
      expect(result.current.loading).toBe(true);
    });

    rerender({ productId: "product-2" });

    await waitFor(() => {
      expect(fetchProductDetailMock).toHaveBeenCalledTimes(2);
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.error).toBeNull();

    secondRequest.resolve({ ok: true, data: productDetailFixture });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.product).toEqual(productDetailFixture);
    });
  });

  it("keeps inventory valuation loading owned by the latest request", async () => {
    const secondRequest = createDeferred<{ ok: true; data: InventoryValuationResponse }>();

    fetchInventoryValuationMock.mockImplementation(
      (
        options?: { warehouseId?: string },
        fetchOptions?: { signal?: AbortSignal },
      ) => {
        if (options?.warehouseId === "warehouse-1") {
          return new Promise((_resolve, reject) => {
            fetchOptions?.signal?.addEventListener("abort", () => reject(createAbortError()), {
              once: true,
            });
          });
        }

        return secondRequest.promise;
      },
    );

    const { result, rerender } = renderHook(
      ({ warehouseId }: { warehouseId?: string }) => useInventoryValuation({ warehouseId }),
      { initialProps: { warehouseId: "warehouse-1" } },
    );

    await waitFor(() => {
      expect(fetchInventoryValuationMock).toHaveBeenCalledTimes(1);
      expect(result.current.loading).toBe(true);
    });

    rerender({ warehouseId: "warehouse-2" });

    await waitFor(() => {
      expect(fetchInventoryValuationMock).toHaveBeenCalledTimes(2);
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.error).toBeNull();

    secondRequest.resolve({ ok: true, data: inventoryValuationFixture });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.items).toEqual(inventoryValuationFixture.items);
      expect(result.current.totalRows).toBe(1);
    });
  });
});
