import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { InventoryValuationPage } from "./InventoryValuationPage";

const valuationState = vi.hoisted(() => ({
  items: [
    {
      product_id: "prod-1",
      product_code: "VAL-001",
      product_name: "Widget A",
      category: "Hardware",
      warehouse_id: "wh-1",
      warehouse_name: "Main Warehouse",
      quantity: 5,
      unit_cost: "12.5000",
      extended_value: "62.5000",
      cost_source: "latest_purchase" as const,
    },
    {
      product_id: "prod-2",
      product_code: "VAL-002",
      product_name: "Widget B",
      category: null,
      warehouse_id: "wh-1",
      warehouse_name: "Main Warehouse",
      quantity: 2,
      unit_cost: null,
      extended_value: "0.0000",
      cost_source: "missing" as const,
    },
  ],
  warehouseTotals: [
    {
      warehouse_id: "wh-1",
      warehouse_name: "Main Warehouse",
      total_quantity: 7,
      total_value: "62.5000",
      row_count: 2,
    },
  ],
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../domain/inventory/context/WarehouseContext", () => ({
  WarehouseProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useWarehouseContext: () => ({
    selectedWarehouse: { id: "wh-1", code: "MAIN", name: "Main Warehouse", is_active: true },
    setSelectedWarehouse: vi.fn(),
  }),
}));

vi.mock("../../domain/inventory/components/WarehouseSelector", () => ({
  WarehouseSelector: () => <div>warehouse-selector</div>,
}));

vi.mock("../../domain/inventory/hooks/useInventoryValuation", () => ({
  useInventoryValuation: () => ({
    items: valuationState.items,
    warehouseTotals: valuationState.warehouseTotals,
    grandTotalValue: "62.5000",
    grandTotalQuantity: 7,
    totalRows: 2,
    loading: false,
    error: null,
  }),
}));

afterEach(() => {
  cleanup();
});

describe("InventoryValuationPage", () => {
  it("renders valuation rows, subtotals, and missing-cost rows", () => {
    render(
      <MemoryRouter>
        <InventoryValuationPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("VAL-001")).toBeTruthy();
    expect(screen.getByText("Widget B")).toBeTruthy();
    expect(screen.getByText("costSource.latest_purchase")).toBeTruthy();
    expect(screen.getByText("costSource.missing")).toBeTruthy();
    expect(screen.getAllByText("62.5000").length).toBeGreaterThanOrEqual(2);
  });
});