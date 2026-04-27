import "../helpers/i18n";

import type { ReactNode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProductCombobox } from "@/domain/inventory/components/ProductCombobox";
import { createProduct, fetchProductDetail, searchProducts } from "../../lib/api/inventory";
import { ToastProvider } from "../../providers/ToastProvider";

vi.mock("../../lib/api/inventory", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api/inventory")>("../../lib/api/inventory");
  return {
    ...actual,
    createProduct: vi.fn(),
    fetchProductDetail: vi.fn(),
    searchProducts: vi.fn(),
  };
});

vi.mock("../../domain/inventory/components/ProductForm", () => ({
  ProductForm: ({ onCancel, onSubmit, onSuccess, submitLabel }: {
    onCancel?: () => void;
    onSubmit: (values: {
      code: string;
      name: string;
      category_id: string | null;
      description: string;
      unit: string;
      standard_cost: string | null;
    }) => Promise<{ ok: boolean; product?: { id: string; code: string; name: string; category_id: string | null; category: string | null; status: string } }>;
    onSuccess: (product: { id: string; code: string; name: string; category_id: string | null; category: string | null; status: string }) => void;
    submitLabel: string;
  }) => (
    <div>
      <button
        type="button"
        onClick={async () => {
          const result = await onSubmit({
            code: "NEW-1",
            name: "New Product",
            category_id: null,
            description: "",
            unit: "pcs",
            standard_cost: null,
          });
          if (result.ok && result.product) {
            onSuccess(result.product);
          }
        }}
      >
        {submitLabel}
      </button>
      {onCancel ? (
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      ) : null}
    </div>
  ),
}));

function renderWithToastProvider(component: ReactNode) {
  return render(<ToastProvider>{component}</ToastProvider>);
}

describe("ProductCombobox", () => {
  beforeEach(() => {
    vi.mocked(searchProducts).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(fetchProductDetail).mockResolvedValue({ ok: false, error: "not found" } as never);
    vi.mocked(createProduct).mockResolvedValue({
      id: "prod-1",
      code: "NEW-1",
      name: "New Product",
      category_id: null,
      category: null,
      description: null,
      unit: "pcs",
      standard_cost: null,
      status: "active",
      created_at: "2026-04-21T00:00:00Z",
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("creates and selects a product through the shared quick-entry dialog", async () => {
    const onChange = vi.fn();
    const onProductSelected = vi.fn();

    renderWithToastProvider(
      <ProductCombobox value="" onChange={onChange} onProductSelected={onProductSelected} />,
    );

    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.change(screen.getByPlaceholderText("Search product by name or code…"), {
      target: { value: "New Product" },
    });

    await waitFor(() => {
      expect(screen.getByText("Create new product")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Create new product"));

    expect(screen.getByRole("dialog", { name: "Create new product" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Create Product" }));

    await waitFor(() => {
      expect(createProduct).toHaveBeenCalledWith({
        code: "NEW-1",
        name: "New Product",
        category_id: null,
        description: "",
        unit: "pcs",
        standard_cost: null,
      });
    });

    expect(onChange).toHaveBeenCalledWith("prod-1");
    expect(onProductSelected).toHaveBeenCalledWith({
      id: "prod-1",
      code: "NEW-1",
      name: "New Product",
      category_id: null,
      category: null,
      status: "active",
      current_stock: 0,
      relevance: 0,
    });
  });

  it("keeps the dialog open and surfaces toast feedback when creation fails", async () => {
    const onChange = vi.fn();
    vi.mocked(createProduct).mockRejectedValue(new Error("Product code already exists"));

    renderWithToastProvider(<ProductCombobox value="" onChange={onChange} />);

    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.change(screen.getByPlaceholderText("Search product by name or code…"), {
      target: { value: "New Product" },
    });

    await waitFor(() => {
      expect(screen.getByText("Create new product")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Create new product"));
    fireEvent.click(screen.getByRole("button", { name: "Create Product" }));

    expect(await screen.findByText("Product code already exists")).toBeTruthy();
    expect(screen.getByRole("dialog", { name: "Create new product" })).toBeTruthy();
    expect(onChange).not.toHaveBeenCalled();
  });
});