import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReorderPointAdmin } from "./ReorderPointAdmin";

const hookMocks = vi.hoisted(() => ({
  applyReorderPoints: vi.fn(),
  clearResults: vi.fn(),
  computeReorderPoints: vi.fn(),
  renderSettingsTab: vi.fn(),
  candidates: [
    {
      stock_id: "stock-1",
      product_id: "product-1",
      product_name: "Widget",
      warehouse_id: "warehouse-1",
      warehouse_name: "Main Warehouse",
      current_quantity: 10,
      current_reorder_point: 5,
      computed_reorder_point: 12,
      avg_daily_usage: 1.5,
      lead_time_days: 4,
      lead_time_sample_count: 1,
      lead_time_confidence: "low",
      review_cycle_days: 30,
      safety_stock: 3,
      target_stock_level: 57,
      demand_basis: "sales_reservation",
      movement_count: 6,
      lead_time_source: "actual",
      quality_note: null,
      skip_reason: null,
      is_selected: false,
      suggested_order_qty: 2,
    },
  ],
  skipped: [
    {
      stock_id: "stock-2",
      product_id: "product-2",
      product_name: "Cable",
      warehouse_id: "warehouse-1",
      warehouse_name: "Main Warehouse",
      current_quantity: 4,
      current_reorder_point: 2,
      computed_reorder_point: null,
      avg_daily_usage: 0,
      lead_time_days: 0,
      lead_time_confidence: null,
      review_cycle_days: 0,
      safety_stock: 0,
      target_stock_level: null,
      demand_basis: null,
      movement_count: 1,
      lead_time_source: "fallback_7d",
      quality_note: "Only 1 demand event in 90 days; need at least 2",
      skip_reason: "insufficient_history",
      is_selected: false,
      suggested_order_qty: null,
    },
  ],
}));

vi.mock("../hooks/useReorderPointAdmin", () => ({
  useReorderPointAdmin: () => ({
    candidates: hookMocks.candidates,
    skipped: hookMocks.skipped,
    computeParams: {},
    loading: false,
    applying: false,
    error: null,
    applyResult: null,
    computeReorderPoints: hookMocks.computeReorderPoints,
    applyReorderPoints: hookMocks.applyReorderPoints,
    clearResults: hookMocks.clearResults,
  }),
}));

vi.mock("../hooks/useWarehouses", () => ({
  useWarehouses: () => ({
    warehouses: [{ id: "warehouse-1", name: "Main Warehouse" }],
  }),
}));

vi.mock("./SettingsTab", () => ({
  SettingsTab: ({
    productId,
    warehouseFilterId,
    onSaveSuccess,
  }: {
    productId: string;
    warehouseFilterId?: string;
    onSaveSuccess?: () => void;
  }) => (
    (hookMocks.renderSettingsTab({ productId, warehouseFilterId }),
    <div>
      <div>mock-settings-tab</div>
      <button type="button" onClick={() => onSaveSuccess?.()}>
        Save settings
      </button>
    </div>)
  ),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("ReorderPointAdmin", () => {
  it("lets the user select a preview row and shows comparison inputs", () => {
    render(<ReorderPointAdmin />);

    expect(screen.getByText("ROP / safety stock = units")).toBeTruthy();
    expect(screen.getByText("Difference (units)")).toBeTruthy();
    expect(screen.getByText("Low")).toBeTruthy();
    expect(
      screen.getByText("Lead time is based on 1 historical samples, so confidence is low."),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /Apply Selected/i }).textContent).toContain("0 selected");

    const [, rowCheckbox] = screen.getAllByRole("checkbox");
    fireEvent.click(rowCheckbox);

    expect(screen.getByRole("button", { name: /Apply Selected/i }).textContent).toContain("1 selected");
  });

  it("shows skipped rows with the translated reason", () => {
    render(<ReorderPointAdmin />);

    fireEvent.click(screen.getAllByRole("button", { name: /Skipped Rows/i })[0]);

    expect(screen.getByText("Insufficient demand history")).toBeTruthy();
    expect(screen.getByText("Only 1 demand event in 90 days; need at least 2")).toBeTruthy();
  });

  it("reruns preview after settings save with the current warehouse filter", async () => {
    render(<ReorderPointAdmin />);

    fireEvent.change(screen.getByLabelText("Warehouse"), {
      target: { value: "warehouse-1" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Preview" })[0]);

    const widgetRow = screen.getAllByText("Widget")[0].closest("tr");
    expect(widgetRow).not.toBeNull();
    fireEvent.click(within(widgetRow as HTMLTableRowElement).getByRole("button", { name: "Planning settings" }));

    expect(screen.getByText("mock-settings-tab")).toBeTruthy();
    expect(hookMocks.renderSettingsTab).toHaveBeenCalledWith({
      productId: "product-1",
      warehouseFilterId: "warehouse-1",
    });

    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => {
      expect(hookMocks.computeReorderPoints).toHaveBeenLastCalledWith({
        safetyFactor: 0.5,
        lookbackDays: 90,
        lookbackDaysLeadTime: 180,
        warehouseId: "warehouse-1",
      });
    });
  });
});
