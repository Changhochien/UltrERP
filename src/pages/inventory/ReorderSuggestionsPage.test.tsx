import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ReorderSuggestionsPage } from "./ReorderSuggestionsPage";

const reorderSuggestionsState = vi.hoisted(() => ({
  suggestions: [
    {
      product_id: "prod-1",
      product_code: "SKU-001",
      product_name: "Widget A",
      warehouse_id: "wh-1",
      warehouse_name: "Main Warehouse",
      current_stock: 4,
      reorder_point: 10,
      target_stock_qty: 18,
      on_order_qty: 0,
      in_transit_qty: 0,
      reserved_qty: 0,
      inventory_position: 4,
      suggested_qty: 14,
      supplier_hint: {
        supplier_id: "sup-1",
        name: "North Supply",
        unit_cost: "12.50",
        default_lead_time_days: 9,
      },
    },
    {
      product_id: "prod-2",
      product_code: "SKU-002",
      product_name: "Widget B",
      warehouse_id: "wh-2",
      warehouse_name: "Overflow",
      current_stock: 2,
      reorder_point: 6,
      target_stock_qty: 8,
      on_order_qty: 0,
      in_transit_qty: 0,
      reserved_qty: 0,
      inventory_position: 2,
      suggested_qty: 6,
      supplier_hint: null,
    },
  ],
  reload: vi.fn(),
  create: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canWrite: () => true,
  }),
}));

vi.mock("../../domain/inventory/context/WarehouseContext", () => ({
  WarehouseProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useWarehouseContext: () => ({
    selectedWarehouse: null,
    setSelectedWarehouse: vi.fn(),
  }),
}));

vi.mock("../../domain/inventory/components/WarehouseSelector", () => ({
  WarehouseSelector: () => <div>warehouse-selector</div>,
}));

vi.mock("../../domain/inventory/hooks/useReorderSuggestions", () => ({
  useReorderSuggestions: () => ({
    suggestions: reorderSuggestionsState.suggestions,
    total: reorderSuggestionsState.suggestions.length,
    loading: false,
    error: null,
    reload: reorderSuggestionsState.reload,
  }),
  useCreateReorderSuggestionOrders: () => ({
    create: reorderSuggestionsState.create,
    submitting: false,
    error: null,
  }),
}));

vi.mock("../../domain/inventory/components/SupplierOrderForm", () => ({
  SupplierOrderForm: ({ initialLines }: { initialLines?: Array<{ product_id: string; quantity: number }> }) => (
    <div>manual-draft:{initialLines?.map((line) => `${line.product_id}:${line.quantity}`).join(",")}</div>
  ),
}));

afterEach(() => {
  cleanup();
  reorderSuggestionsState.reload.mockReset();
  reorderSuggestionsState.create.mockReset();
});

describe("ReorderSuggestionsPage", () => {
  it("submits the selected suggestions for draft creation", async () => {
    reorderSuggestionsState.create.mockResolvedValue({
      created_orders: [],
      unresolved_rows: [],
    });

    render(
      <MemoryRouter>
        <ReorderSuggestionsPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("North Supply")).toBeTruthy();

    fireEvent.click(screen.getAllByRole("checkbox")[1]);
    fireEvent.click(screen.getByRole("button", { name: "createSelected" }));

    await waitFor(() => {
      expect(reorderSuggestionsState.create).toHaveBeenCalledWith({
        items: [
          {
            product_id: "prod-1",
            warehouse_id: "wh-1",
            suggested_qty: 14,
          },
        ],
      });
    });
  });

  it("opens the manual draft handoff when a row is unresolved", async () => {
    reorderSuggestionsState.create.mockResolvedValue({
      created_orders: [],
      unresolved_rows: [reorderSuggestionsState.suggestions[1]],
    });

    render(
      <MemoryRouter>
        <ReorderSuggestionsPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "createDraft" })[1]);

    await waitFor(() => {
      expect(screen.getByText("manual-draft:prod-2:6")).toBeTruthy();
    });
  });
});
