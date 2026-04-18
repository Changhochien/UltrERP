import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EditProductForm } from "../../domain/inventory/components/EditProductForm";
import { updateProduct } from "../../lib/api/inventory";
import type { ProductDetail, ProductResponse } from "../../domain/inventory/types";

vi.mock("../../lib/api/inventory", () => ({
  updateProduct: vi.fn(),
}));

const product: ProductDetail = {
  id: "product-1",
  code: "SKU-1",
  name: "Widget",
  category: "Hardware",
  description: "Original description",
  unit: "pcs",
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
  status: "active",
  created_at: "2026-04-01T00:00:00Z",
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("EditProductForm", () => {
  it("prefills the form from the current product record", () => {
    render(<EditProductForm product={product} onSuccess={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByDisplayValue("SKU-1")).toBeTruthy();
    expect(screen.getByDisplayValue("Widget")).toBeTruthy();
    expect(screen.getByDisplayValue("Hardware")).toBeTruthy();
    expect(screen.getByDisplayValue("Original description")).toBeTruthy();
    expect(screen.getByDisplayValue("pcs")).toBeTruthy();
  });

  it("submits the full editable payload and calls onSuccess", async () => {
    const onSuccess = vi.fn();
    (updateProduct as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, data: updatedProduct });

    render(<EditProductForm product={product} onSuccess={onSuccess} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(/Code/i), { target: { value: "SKU-2" } });
    fireEvent.change(screen.getByLabelText(/Name/i), { target: { value: "Widget Pro" } });
    fireEvent.change(screen.getByLabelText(/Description/i), { target: { value: "Updated description" } });
    fireEvent.change(screen.getByLabelText(/Unit/i), { target: { value: "box" } });
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    await waitFor(() => {
      expect(updateProduct).toHaveBeenCalledWith("product-1", {
        code: "SKU-2",
        name: "Widget Pro",
        category: "Hardware",
        description: "Updated description",
        unit: "box",
      });
    });
    expect(onSuccess).toHaveBeenCalledWith(updatedProduct);
  });

  it("shows inline duplicate-code feedback", async () => {
    (updateProduct as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      errors: [{ field: "code", message: "Product code already exists" }],
    });

    render(<EditProductForm product={product} onSuccess={vi.fn()} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    expect(await screen.findByText("Product code already exists")).toBeTruthy();
  });
});