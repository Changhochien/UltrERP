import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SettingsTab } from "./SettingsTab";

const hookMocks = vi.hoisted(() => ({
  reload: vi.fn(),
  update: vi.fn(),
}));

vi.mock("../hooks/useProductDetail", () => ({
  useProductDetail: () => ({
    product: {
      warehouses: [
        {
          stock_id: "stock-1",
          warehouse_id: "warehouse-1",
          warehouse_name: "Main Warehouse",
          current_stock: 12,
          reorder_point: 5,
          safety_factor: 0.5,
          lead_time_days: 7,
          policy_type: "continuous",
          target_stock_qty: 0,
          on_order_qty: 0,
          in_transit_qty: 0,
          reserved_qty: 0,
          planning_horizon_days: 0,
          review_cycle_days: 3,
          is_below_reorder: false,
          last_adjusted: null,
        },
        {
          stock_id: "stock-2",
          warehouse_id: "warehouse-2",
          warehouse_name: "Overflow Warehouse",
          current_stock: 8,
          reorder_point: 2,
          safety_factor: 0.4,
          lead_time_days: 10,
          policy_type: "continuous",
          target_stock_qty: 0,
          on_order_qty: 0,
          in_transit_qty: 0,
          reserved_qty: 0,
          planning_horizon_days: 0,
          review_cycle_days: 0,
          is_below_reorder: false,
          last_adjusted: null,
        },
      ],
    },
    loading: false,
    reload: hookMocks.reload,
  }),
}));

vi.mock("../hooks/useStockHistory", () => ({
  useStockHistory: () => ({ avgDailyUsage: 1.2 }),
}));

vi.mock("../hooks/useUpdateStockSettings", () => ({
  useUpdateStockSettings: () => ({
    update: hookMocks.update,
    submitting: false,
    error: null,
    clearError: vi.fn(),
  }),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("SettingsTab", () => {
  it("filters to the requested warehouse and calls the save callback after update", async () => {
    const onSaveSuccess = vi.fn().mockResolvedValue(undefined);
    hookMocks.reload.mockResolvedValue(undefined);
    hookMocks.update.mockResolvedValue({ id: "stock-1" });

    render(
      <SettingsTab
        productId="product-1"
        warehouseFilterId="warehouse-1"
        onSaveSuccess={onSaveSuccess}
      />,
    );

    expect(screen.getByText("Main Warehouse")).toBeTruthy();
    expect(screen.queryByText("Overflow Warehouse")).toBeNull();

    const reorderPointInput = screen.getByDisplayValue("5");
    fireEvent.change(reorderPointInput, { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(hookMocks.update).toHaveBeenCalledWith("stock-1", {
        reorder_point: 9,
        safety_factor: 0.5,
        lead_time_days: 7,
        review_cycle_days: 3,
      });
    });
    expect(hookMocks.reload).toHaveBeenCalledTimes(1);
    expect(onSaveSuccess).toHaveBeenCalledTimes(1);
  });
});
