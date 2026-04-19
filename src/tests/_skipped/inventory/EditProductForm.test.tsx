import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EditProductForm } from "../../domain/inventory/components/EditProductForm";
import { listCategories, listUnits, updateProduct } from "../../lib/api/inventory";
import type { ProductDetail, ProductResponse } from "../../domain/inventory/types";

vi.mock("../../lib/api/inventory", () => ({
  listCategories: vi.fn(),
  listUnits: vi.fn(),
  updateProduct: vi.fn(),
}));

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const product: ProductDetail = {
  id: "product-1",
  code: "SKU-1",
  name: "Widget",
  category: "Hardware",
  description: "Original description",
  unit: "pcs",
  standard_cost: "5.2500",
  status: "active",
  total_stock: 12,
  warehouses: [],
  adjustment_history: [],
};

const updatedProduct: ProductResponse = {
  id: "product-1",
  code: "SKU-2",
  name: "Widget Pro",
  category: "Hardware",
  description: "Updated description",
  unit: "box",
  standard_cost: "7.1250",
  status: "active",
  created_at: "2026-04-01T00:00:00Z",
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe("EditProductForm", () => {
  it("prefills the form from the current product record", () => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    (listCategories as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [], total: 0 });
    render(<EditProductForm product={product} onSuccess={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByDisplayValue("SKU-1")).toBeTruthy();
    expect(screen.getByDisplayValue("Widget")).toBeTruthy();
    expect(screen.getByRole("combobox", { name: /Category/i }).textContent).toContain("Hardware");
    expect(screen.getByDisplayValue("Original description")).toBeTruthy();
    expect(screen.getByRole("combobox", { name: /Unit/i }).textContent).toContain("pcs");
    expect(screen.getByDisplayValue("5.2500")).toBeTruthy();
  });

  it("submits the full editable payload and calls onSuccess", async () => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    (listCategories as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [], total: 0 });
    (listUnits as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: "unit-1",
          tenant_id: "tenant-1",
          code: "pcs",
          name: "Pieces",
          decimal_places: 0,
          is_active: true,
          created_at: "2026-04-01T00:00:00Z",
          updated_at: "2026-04-01T00:00:00Z",
        },
        {
          id: "unit-2",
          tenant_id: "tenant-1",
          code: "box",
          name: "Box",
          decimal_places: 0,
          is_active: true,
          created_at: "2026-04-01T00:00:00Z",
          updated_at: "2026-04-01T00:00:00Z",
        },
      ],
      total: 2,
    });
    const onSuccess = vi.fn();
    (updateProduct as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, data: updatedProduct });

    render(<EditProductForm product={product} onSuccess={onSuccess} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(/Code/i), { target: { value: "SKU-2" } });
    fireEvent.change(screen.getByLabelText(/Name/i), { target: { value: "Widget Pro" } });
    fireEvent.change(screen.getByLabelText(/Description/i), { target: { value: "Updated description" } });
    fireEvent.click(screen.getByRole("combobox", { name: /Unit/i }));
    fireEvent.click(await screen.findByText("Box"));
    fireEvent.change(screen.getByLabelText(/Standard Cost/i), { target: { value: "7.1250" } });
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    await waitFor(() => {
      expect(updateProduct).toHaveBeenCalledWith("product-1", {
        code: "SKU-2",
        name: "Widget Pro",
        category: "Hardware",
        description: "Updated description",
        unit: "box",
        standard_cost: "7.1250",
      });
    });
    expect(onSuccess).toHaveBeenCalledWith(updatedProduct);
  });

  it("shows inline duplicate-code feedback", async () => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    (listCategories as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [], total: 0 });
    (updateProduct as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      errors: [{ field: "code", message: "Product code already exists" }],
    });

    render(<EditProductForm product={product} onSuccess={vi.fn()} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    expect(await screen.findByText("Product code already exists")).toBeTruthy();
  });
});