import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { SupplierOrderForm } from "./SupplierOrderForm";

// Top-level mock functions
const mockSearchProducts = vi.fn();
const mockFetchProductDetail = vi.fn();
const createSupplierOrderMock = vi.fn();

vi.mock("../hooks/useSupplierOrders", () => ({
  useSuppliers: () => ({
    suppliers: [{ id: "sup-1", name: "Acme Supply" }],
    loading: false,
  }),
  useCreateSupplierOrder: () => ({
    create: createSupplierOrderMock,
    submitting: false,
    error: null,
  }),
}));

vi.mock("../hooks/useWarehouses", () => ({
  useWarehouses: () => ({
    warehouses: [{ id: "wh-1", name: "Main Warehouse" }],
    loading: false,
  }),
}));

vi.mock("../../../lib/api/inventory", () => ({
  searchProducts: (...args: unknown[]) => mockSearchProducts(...args),
  fetchProductDetail: (...args: unknown[]) => mockFetchProductDetail(...args),
}));

const PRODUCT = {
  id: "prod-1",
  code: "P001",
  name: "Widget",
  category: "Hardware",
  status: "active" as const,
  current_stock: 10,
  relevance: 0,
};

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", ResizeObserverMock);
  mockSearchProducts.mockResolvedValue({
    items: [PRODUCT],
    total: 1,
  });
  mockFetchProductDetail.mockResolvedValue({
    ok: true,
    data: PRODUCT,
  });
  createSupplierOrderMock.mockReset();
  createSupplierOrderMock.mockResolvedValue({ id: "so-1" });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("SupplierOrderForm", () => {
  it("preserves an explicit zero unit price when submitting", async () => {
    render(<SupplierOrderForm onCreated={vi.fn()} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Supplier"), {
      target: { value: "sup-1" },
    });

    // Open product combobox, wait for list, then select product
    fireEvent.click(screen.getByRole("combobox", { name: "Line 1 product" }));
    await screen.findByText("Widget");
    fireEvent.click(screen.getByText("Widget"));

    fireEvent.change(screen.getByLabelText("Line 1 warehouse"), {
      target: { value: "wh-1" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 unit cost"), {
      target: { value: "0" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create Order" }));

    await waitFor(() => {
      expect(createSupplierOrderMock).toHaveBeenCalledTimes(1);
    });

    expect(createSupplierOrderMock).toHaveBeenCalledWith({
      supplier_id: "sup-1",
      order_date: expect.any(String),
      expected_arrival_date: undefined,
      lines: [
        {
          product_id: "prod-1",
          warehouse_id: "wh-1",
          quantity_ordered: 1,
          unit_price: 0,
        },
      ],
    });
  });
});
