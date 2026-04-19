import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ProductSuppliersPanel } from "./ProductSuppliersPanel";

const createProductSupplierMock = vi.fn();
const deleteProductSupplierMock = vi.fn();
const listProductSuppliersMock = vi.fn();
const updateProductSupplierMock = vi.fn();

vi.mock("@/lib/api/inventory", () => ({
  createProductSupplier: (...args: unknown[]) => createProductSupplierMock(...args),
  deleteProductSupplier: (...args: unknown[]) => deleteProductSupplierMock(...args),
  listProductSuppliers: (...args: unknown[]) => listProductSuppliersMock(...args),
  updateProductSupplier: (...args: unknown[]) => updateProductSupplierMock(...args),
}));

vi.mock("../hooks/useSuppliers", () => ({
  useSuppliers: () => ({
    suppliers: [
      { id: "sup-1", name: "Acme Supply" },
      { id: "sup-2", name: "Beta Supply" },
    ],
    loading: false,
  }),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ProductSuppliersPanel", () => {
  it("adds a supplier association with optional planning fields", async () => {
    listProductSuppliersMock.mockResolvedValue({ ok: true, data: { items: [], total: 0 } });
    createProductSupplierMock.mockResolvedValue({
      ok: true,
      data: {
        id: "assoc-1",
        product_id: "prod-1",
        supplier_id: "sup-2",
        supplier_name: "Beta Supply",
        unit_cost: 9.5,
        lead_time_days: 6,
        is_default: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    });

    render(<ProductSuppliersPanel productId="prod-1" />);

    await waitFor(() => {
      expect(listProductSuppliersMock).toHaveBeenCalledWith("prod-1");
    });

    fireEvent.change(screen.getByLabelText("Supplier"), { target: { value: "sup-2" } });
    fireEvent.change(screen.getByLabelText("Unit Cost"), { target: { value: "9.5" } });
    fireEvent.change(screen.getByLabelText("Lead Time (days)"), { target: { value: "6" } });
    fireEvent.click(screen.getByLabelText("Default supplier"));
    fireEvent.click(screen.getByRole("button", { name: "Add Supplier" }));

    await waitFor(() => {
      expect(createProductSupplierMock).toHaveBeenCalledWith("prod-1", {
        supplier_id: "sup-2",
        unit_cost: 9.5,
        lead_time_days: 6,
        is_default: true,
      });
    });
  });

  it("supports default and remove actions for existing associations", async () => {
    listProductSuppliersMock.mockResolvedValue({
      ok: true,
      data: {
        items: [
          {
            id: "assoc-1",
            product_id: "prod-1",
            supplier_id: "sup-1",
            supplier_name: "Acme Supply",
            unit_cost: 12.5,
            lead_time_days: 7,
            is_default: false,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
    });
    updateProductSupplierMock.mockResolvedValue({ ok: true, data: {} });
    deleteProductSupplierMock.mockResolvedValue({ ok: true });

    render(<ProductSuppliersPanel productId="prod-1" />);

    expect(await screen.findByRole("button", { name: "Set Default" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Set Default" }));

    await waitFor(() => {
      expect(updateProductSupplierMock).toHaveBeenCalledWith("prod-1", "sup-1", { is_default: true });
    });

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    await waitFor(() => {
      expect(deleteProductSupplierMock).toHaveBeenCalledWith("prod-1", "sup-1");
    });
  });
});