import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const useProductDetailMock = vi.fn();
const fetchProductLookupMock = vi.fn();
const searchProductsMock = vi.fn();

vi.mock("../hooks/useProductDetail", () => ({
  useProductDetail: (...args: Parameters<typeof useProductDetailMock>) => useProductDetailMock(...args),
}));

vi.mock("../hooks/useWarehouses", () => ({
  useWarehouses: () => ({
    warehouses: [{ id: "warehouse-1", name: "Main Warehouse" }],
    loading: false,
    error: null,
  }),
}));

vi.mock("../hooks/useStockAdjustment", () => ({
  useReasonCodes: () => ({
    codes: [{ value: "count", label: "Count adjustment" }],
    loading: false,
  }),
  useStockAdjustment: () => ({
    submit: vi.fn(),
    submitting: false,
    result: null,
    error: null,
    clearError: vi.fn(),
  }),
}));

vi.mock("../../../lib/api/inventory", () => ({
  fetchProductDetail: (...args: Parameters<typeof fetchProductLookupMock>) =>
    fetchProductLookupMock(...args),
  searchProducts: (...args: Parameters<typeof searchProductsMock>) =>
    searchProductsMock(...args),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.resetModules();
});

describe("StockAdjustmentForm", () => {
  it("reads product detail from the currently selected product", async () => {
    const { StockAdjustmentForm } = await import("./StockAdjustmentForm");

    fetchProductLookupMock.mockImplementation(async (productId: string) => ({
      ok: true,
      data: {
        id: productId,
        code: productId === "product-1" ? "SKU-1" : "SKU-2",
        name: productId === "product-1" ? "Widget" : "Rotor",
        category: "Hardware",
        description: null,
        unit: "pcs",
        standard_cost: null,
        status: "active",
        total_stock: productId === "product-1" ? 4 : 8,
        warehouses: [],
        adjustment_history: [],
      },
    }));
    searchProductsMock.mockResolvedValue({
      items: [
        {
          id: "product-2",
          code: "SKU-2",
          name: "Rotor",
          category: "Hardware",
          status: "active",
          current_stock: 8,
          relevance: 1,
        },
      ],
      total: 1,
    });

    useProductDetailMock.mockImplementation((productId: string | null) => {
      if (productId === "product-2") {
        return { product: { name: "Rotor" } };
      }
      if (productId === "product-1") {
        return { product: { name: "Widget" } };
      }
      return { product: null };
    });

    render(<StockAdjustmentForm defaultProductId="product-1" />);

    expect(screen.getByText("Widget")).toBeTruthy();

  const productField = screen.getByText("Product").closest("label");
  expect(productField).toBeTruthy();

  fireEvent.click(within(productField!).getByRole("combobox"));

    await waitFor(() => {
      expect(screen.getByText("Rotor")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Rotor"));

    await waitFor(() => {
      expect(useProductDetailMock).toHaveBeenLastCalledWith("product-2");
      expect(screen.getByText("Rotor")).toBeTruthy();
    });
  });
});