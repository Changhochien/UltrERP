import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { BelowReorderReportPage } from "./BelowReorderReportPage";

const reportState = vi.hoisted(() => ({
  items: [
    {
      product_id: "prod-1",
      product_code: "LOW-001",
      product_name: "Widget A",
      category: "Hardware",
      warehouse_id: "wh-1",
      warehouse_name: "Main Warehouse",
      current_stock: 3,
      reorder_point: 8,
      shortage_qty: 5,
      on_order_qty: 2,
      in_transit_qty: 1,
      default_supplier: null,
    },
  ],
  exportReport: vi.fn(),
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

vi.mock("../../domain/inventory/hooks/useBelowReorderReport", () => ({
  useBelowReorderReport: () => ({
    items: reportState.items,
    total: reportState.items.length,
    loading: false,
    error: null,
  }),
}));

vi.mock("../../lib/api/inventory", () => ({
  exportBelowReorderReport: (...args: unknown[]) => reportState.exportReport(...args),
}));

afterEach(() => {
  cleanup();
  reportState.exportReport.mockReset();
});

describe("BelowReorderReportPage", () => {
  it("renders the preview table and wires export to the selected warehouse", async () => {
    reportState.exportReport.mockResolvedValue({ ok: true, filename: "below-reorder-report.csv" });

    render(
      <MemoryRouter>
        <BelowReorderReportPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("LOW-001")).toBeTruthy();
    expect(screen.getByText("Widget A")).toBeTruthy();
    expect(screen.getByText("5")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "exportCsv" }));

    await waitFor(() => {
      expect(reportState.exportReport).toHaveBeenCalledWith({ warehouseId: "wh-1" });
    });
  });
});