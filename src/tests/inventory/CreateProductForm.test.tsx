import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CreateProductForm } from "../../domain/inventory/components/CreateProductForm";
import { createCategory, createProduct, listCategories } from "../../lib/api/inventory";
import type { ProductResponse } from "../../domain/inventory/types";

vi.mock("../../lib/api/inventory", () => ({
  createCategory: vi.fn(),
  createProduct: vi.fn(),
  listCategories: vi.fn(),
}));

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const CATEGORY = {
  id: "category-1",
  tenant_id: "tenant-1",
  name: "Hardware",
  is_active: true,
  created_at: "2026-04-01T00:00:00Z",
  updated_at: "2026-04-01T00:00:00Z",
};

const mockProduct: ProductResponse = {
  id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  code: "WIDGET-001",
  name: "Test Widget",
  category: null,
  description: null,
  unit: "pcs",
  standard_cost: null,
  status: "active",
  created_at: "2026-04-01T00:00:00Z",
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

function fillValidForm() {
  fireEvent.change(screen.getByLabelText(/Code/i), { target: { value: "WIDGET-001" } });
  fireEvent.change(screen.getByLabelText(/Name/i), { target: { value: "Test Widget" } });
}

describe("CreateProductForm", () => {
  it("submits the selected category as plain text", async () => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    (listCategories as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [CATEGORY],
      total: 1,
    });
    (createCategory as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      data: CATEGORY,
    });
    const onSuccess = vi.fn();
    (createProduct as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockProduct,
      category: "Hardware",
    });

    render(<CreateProductForm onSuccess={onSuccess} />);
    fillValidForm();
    fireEvent.click(screen.getByRole("combobox", { name: /Category/i }));
    fireEvent.click(await screen.findByText("Hardware"));
    fireEvent.click(screen.getByRole("button", { name: /Create Product/i }));

    await waitFor(() => {
      expect(createProduct).toHaveBeenCalledWith({
        code: "WIDGET-001",
        name: "Test Widget",
        category: "Hardware",
        description: "",
        unit: "pcs",
        standard_cost: null,
      });
    });
  });

  it("shows validation errors when submitting empty form", async () => {
    const onSuccess = vi.fn();
    render(<CreateProductForm onSuccess={onSuccess} />);

    fireEvent.click(screen.getByRole("button", { name: /Create Product/i }));

    const codeError = await screen.findByText("Code is required");
    const nameError = screen.getByText("Name is required");
    expect(codeError).toBeTruthy();
    expect(nameError).toBeTruthy();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("calls createProduct with correct data on submit", async () => {
    const onSuccess = vi.fn();
    (createProduct as ReturnType<typeof vi.fn>).mockResolvedValue(mockProduct);

    render(<CreateProductForm onSuccess={onSuccess} />);
    fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: /Create Product/i }));

    await waitFor(() => {
      expect(createProduct).toHaveBeenCalledWith({
        code: "WIDGET-001",
        name: "Test Widget",
        category: "",
        description: "",
        unit: "pcs",
        standard_cost: null,
      });
    });
    expect(onSuccess).toHaveBeenCalledWith(mockProduct);
  });

  it("submits standard cost when provided and blocks negative values", async () => {
    const onSuccess = vi.fn();
    (createProduct as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockProduct,
      standard_cost: "12.5000",
    });

    render(<CreateProductForm onSuccess={onSuccess} />);
    fillValidForm();
    fireEvent.change(screen.getByLabelText(/Standard Cost/i), { target: { value: "-1" } });
    fireEvent.click(screen.getByRole("button", { name: /Create Product/i }));

    expect(await screen.findByText("Standard cost must be greater than or equal to 0")).toBeTruthy();
    expect(createProduct).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText(/Standard Cost/i), { target: { value: "12.5000" } });
    fireEvent.click(screen.getByRole("button", { name: /Create Product/i }));

    await waitFor(() => {
      expect(createProduct).toHaveBeenCalledWith({
        code: "WIDGET-001",
        name: "Test Widget",
        category: "",
        description: "",
        unit: "pcs",
        standard_cost: "12.5000",
      });
    });
  });

  it("shows friendly message on duplicate code error", async () => {
    const onSuccess = vi.fn();
    const error = new Error("Product code already exists");
    (createProduct as ReturnType<typeof vi.fn>).mockRejectedValue(error);

    render(<CreateProductForm onSuccess={onSuccess} />);
    fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: /Create Product/i }));

    const msg = await screen.findByText("Product code already exists");
    expect(msg).toBeTruthy();
  });

  it("disables submit button while loading", async () => {
    let resolveCreateProduct: (value: ProductResponse) => void;
    const createProductPromise = new Promise<ProductResponse>((resolve) => {
      resolveCreateProduct = resolve;
    });
    (createProduct as ReturnType<typeof vi.fn>).mockReturnValue(createProductPromise);

    const onSuccess = vi.fn();
    render(<CreateProductForm onSuccess={onSuccess} />);
    fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: /Create Product/i }));

    const btn = screen.getByRole("button", { name: /Creating/i });
    expect(btn).toBeTruthy();
    expect((btn as HTMLButtonElement).disabled).toBe(true);

    resolveCreateProduct!(mockProduct);
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });

  it("renders all form fields", () => {
    const onSuccess = vi.fn();
    render(<CreateProductForm onSuccess={onSuccess} />);

    expect(screen.getByLabelText(/Code/i)).toBeTruthy();
    expect(screen.getByLabelText(/Name/i)).toBeTruthy();
    expect(screen.getByRole("combobox", { name: /Category/i })).toBeTruthy();
    expect(screen.getByLabelText(/Description/i)).toBeTruthy();
    expect(screen.getByLabelText(/Unit/i)).toBeTruthy();
    expect(screen.getByLabelText(/Standard Cost/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Create Product/i })).toBeTruthy();
  });
});
