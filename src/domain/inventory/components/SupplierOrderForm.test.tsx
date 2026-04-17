import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { SupplierOrderForm } from "./SupplierOrderForm";

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

afterEach(() => {
  cleanup();
  createSupplierOrderMock.mockReset();
  vi.restoreAllMocks();
});

describe("SupplierOrderForm", () => {
  it("preserves an explicit zero unit price when submitting", async () => {
    createSupplierOrderMock.mockResolvedValue({ id: "so-1" });

    render(<SupplierOrderForm onCreated={vi.fn()} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Supplier"), {
      target: { value: "sup-1" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 product"), {
      target: { value: "prod-1" },
    });
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