import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProductForm } from "../../domain/inventory/components/ProductForm";

vi.mock("../../domain/inventory/components/CategoryCombobox", () => ({
  CategoryCombobox: ({ valueLabel, ariaLabelledBy, onChange }: { valueLabel: string; ariaLabelledBy?: string; onChange: (categoryId: string | null, categoryName: string) => void }) => (
    <button
      type="button"
      aria-labelledby={ariaLabelledBy}
      onClick={() => onChange("category-1", "Hardware")}
    >
      {valueLabel || "Pick category"}
    </button>
  ),
}));

vi.mock("../../domain/inventory/components/UnitCombobox", () => ({
  UnitCombobox: ({ value, ariaLabelledBy, onChange }: { value: string; ariaLabelledBy?: string; onChange: (unit: string) => void }) => (
    <input aria-labelledby={ariaLabelledBy} value={value} onChange={(event) => onChange(event.target.value)} />
  ),
}));

describe("ProductForm", () => {
  it("submits the normalized product payload through the shared schema", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ ok: true, product: { id: "prod-1" } });
    const onSuccess = vi.fn();

    render(
      <ProductForm
        onSubmit={onSubmit}
        onSuccess={onSuccess}
        submitLabel="Save Product"
        submittingLabel="Saving..."
      />, 
    );

    fireEvent.change(screen.getByLabelText(/Code/i), { target: { value: "  W-100  " } });
    fireEvent.change(screen.getByLabelText(/Name/i), { target: { value: "  Widget  " } });
    fireEvent.click(screen.getByLabelText(/Category/i));
    fireEvent.change(screen.getByLabelText(/Description/i), { target: { value: "  Standard widget  " } });
    fireEvent.change(screen.getByLabelText(/Unit/i), { target: { value: " box " } });
    fireEvent.change(screen.getByLabelText(/Standard Cost/i), { target: { value: "12.5000" } });

    fireEvent.click(screen.getByRole("button", { name: "Save Product" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        code: "W-100",
        name: "Widget",
        category_id: "category-1",
        description: "Standard widget",
        unit: "box",
        standard_cost: "12.5000",
      });
    });
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("blocks submit when standard cost is negative", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ ok: true, product: { id: "prod-1" } });

    render(
      <ProductForm
        onSubmit={onSubmit}
        onSuccess={vi.fn()}
        submitLabel="Save Product"
        submittingLabel="Saving..."
      />,
    );

    fireEvent.change(screen.getByLabelText(/Code/i), { target: { value: "W-100" } });
    fireEvent.change(screen.getByLabelText(/Name/i), { target: { value: "Widget" } });
    fireEvent.change(screen.getByLabelText(/Standard Cost/i), { target: { value: "-1" } });

    fireEvent.click(screen.getByRole("button", { name: "Save Product" }));

    await waitFor(() => {
      expect(screen.getByText("Standard cost must be greater than or equal to 0")).toBeTruthy();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });
});