import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReorderPointAdmin } from "./ReorderPointAdmin";

const hookMocks = vi.hoisted(() => ({
  applyReorderPoints: vi.fn(),
  clearResults: vi.fn(),
  computeReorderPoints: vi.fn(),
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
}));

vi.mock("../hooks/useReorderPointAdmin", () => ({
  useReorderPointAdmin: () => ({
    candidates: hookMocks.candidates,
    skipped: [],
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
  useWarehouses: () => ({ warehouses: [] }),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("ReorderPointAdmin", () => {
  it("lets the user select a preview row and shows unit guidance", () => {
    render(<ReorderPointAdmin />);

    expect(screen.getByText("ROP / safety stock = units")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Apply Selected/i }).textContent).toContain("0 selected");

    const [, rowCheckbox] = screen.getAllByRole("checkbox");
    fireEvent.click(rowCheckbox);

    expect(screen.getByRole("button", { name: /Apply Selected/i }).textContent).toContain("1 selected");
  });
});
