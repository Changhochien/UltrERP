import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const useProductDetailMock = vi.fn();
const fetchProductLookupMock = vi.fn();
const searchProductsMock = vi.fn();
const submitMock = vi.fn();

vi.mock("@/domain/inventory/components/ProductCombobox", () => ({
  ProductCombobox: ({
    value,
    onChange,
    placeholder,
  }: {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
  }) => (
    <button type="button" role="combobox" aria-label={placeholder ?? "Product"} onClick={() => onChange("product-2")}>
      {value || placeholder || "Product"}
    </button>
  ),
}));

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
    submit: submitMock,
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
  submitMock.mockReset();
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

    fireEvent.click(screen.getByRole("combobox", { name: "Search product…" }));

    await waitFor(() => {
      expect(useProductDetailMock).toHaveBeenLastCalledWith("product-2");
      expect(screen.getByText("Rotor")).toBeTruthy();
    });
  });

  it("uses the reason label in confirmation copy and can skip the nested confirmation dialog", async () => {
    const { StockAdjustmentForm } = await import("./StockAdjustmentForm");

    useProductDetailMock.mockImplementation((productId: string | null) => {
      if (productId === "product-1") {
        return { product: { name: "Widget" } };
      }
      return { product: null };
    });

    submitMock.mockResolvedValue({ updated_stock: 9 });

    const { unmount } = render(<StockAdjustmentForm defaultProductId="product-1" />);

    fireEvent.change(screen.getByLabelText("Warehouse"), { target: { value: "warehouse-1" } });
    fireEvent.change(screen.getByLabelText(/Quantity change/i), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText(/Reason code/i), { target: { value: "count" } });

    fireEvent.click(screen.getByRole("button", { name: "Record Adjustment" }));

    const confirmDialog = await screen.findByRole("dialog", { name: "Confirm adjustment" });
    expect(within(confirmDialog).getByText(/\+3/)).toBeTruthy();
    expect(within(confirmDialog).getByText(/Count adjustment/)).toBeTruthy();

    unmount();

    render(<StockAdjustmentForm defaultProductId="product-1" confirmBeforeSubmit={false} />);

    fireEvent.change(screen.getByLabelText("Warehouse"), { target: { value: "warehouse-1" } });
    fireEvent.change(screen.getByLabelText(/Quantity change/i), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText(/Reason code/i), { target: { value: "count" } });

    fireEvent.click(screen.getByRole("button", { name: "Record Adjustment" }));

    await waitFor(() => {
      expect(submitMock).toHaveBeenCalledWith(expect.objectContaining({
        product_id: "product-1",
        warehouse_id: "warehouse-1",
        quantity_change: 2,
        reason_code: "count",
      }));
    });
    expect(screen.queryByText("Confirm adjustment")).toBeNull();
  });
});