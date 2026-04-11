import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const mocks = vi.hoisted(() => ({
  product: {
    id: "product-1",
    code: "SKU-1",
    name: "Widget",
    category: "Hardware",
    status: "active",
    total_stock: 12,
    warehouses: [
      {
        stock_id: "stock-1",
        warehouse_id: "warehouse-1",
        warehouse_name: "Main Warehouse",
        current_stock: 12,
        reorder_point: 5,
        is_below_reorder: false,
        last_adjusted: null,
      },
    ],
    adjustment_history: [],
  },
}));

vi.mock("react-i18next", () => ({
  useTranslation: (_ns?: string, options?: { keyPrefix?: string }) => ({
    t: (key: string) => (options?.keyPrefix ? `${options.keyPrefix}.${key}` : key),
  }),
}));

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");

  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    CartesianGrid: () => null,
    XAxis: () => null,
    YAxis: () => null,
    Tooltip: () => null,
    Bar: () => null,
  };
});

vi.mock("@/domain/inventory/hooks/useProductDetail", () => ({
  useProductDetail: vi.fn(() => ({
    product: mocks.product,
    loading: false,
    error: null,
  })),
}));

vi.mock("@/domain/inventory/hooks/useStockHistory", () => ({
  useStockHistory: vi.fn(() => ({
    history: [],
    reorderPoint: 5,
    safetyStock: 2,
    avgDailyUsage: 1.5,
    leadTimeDays: 7,
    loading: false,
    error: null,
  })),
}));

vi.mock("@/domain/inventory/hooks/useProductMonthlyDemand", () => ({
  useProductMonthlyDemand: vi.fn(() => ({
    items: [{ month: "2026-01", total_qty: 12 }],
    total: 1,
    loading: false,
    error: null,
  })),
}));

vi.mock("@/domain/inventory/hooks/useProductSalesHistory", () => ({
  useProductSalesHistory: vi.fn(() => ({
    items: [
      {
        date: "2026-01-02",
        quantity_change: -2,
        reason_code: "sales_reservation",
        actor_id: "owner@example.com",
      },
    ],
    total: 1,
    loading: false,
    error: null,
  })),
}));

vi.mock("@/domain/inventory/hooks/useProductTopCustomer", () => ({
  useProductTopCustomer: vi.fn(() => ({
    customer: {
      customer_id: "customer-1",
      customer_name: "Acme Corp",
      total_qty: 18,
    },
    loading: false,
    error: null,
  })),
}));

vi.mock("@/domain/inventory/hooks/useProductAuditLog", () => ({
  useProductAuditLog: vi.fn(() => ({
    items: [],
    total: 0,
    loading: false,
    error: null,
  })),
}));

vi.mock("@/domain/inventory/components/StockTrendChart", () => ({
  StockTrendChart: () => <div>stock-trend-chart</div>,
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ProductDetailPage", () => {
  it("renders translated product detail copy and shows analytics content when the analytics tab is selected", async () => {
    const { ProductDetailPage } = await import("./ProductDetailPage");

    render(
      <MemoryRouter initialEntries={["/inventory/products/product-1"]}>
        <Routes>
          <Route path="/inventory/products/:productId" element={<ProductDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole("tab", { name: "inventory.productDetail.analytics" })).toBeTruthy();
    expect(screen.getByText("inventory.productDetail.statuses.active")).toBeTruthy();
    expect(screen.getByText("inventory.productDetail.adjustmentTimeline.empty")).toBeTruthy();

    fireEvent.mouseDown(screen.getByRole("tab", { name: "inventory.productDetail.analytics" }), {
      button: 0,
    });

    expect(screen.getByText("inventory.productDetail.analyticsTab.summary.title")).toBeTruthy();
    expect(screen.getByText("inventory.productDetail.analyticsTab.monthlyDemand.title")).toBeTruthy();
    expect(screen.getByText("inventory.productDetail.analyticsTab.salesHistory.title")).toBeTruthy();
    expect(screen.getByText("inventory.productDetail.analyticsTab.topCustomer.title")).toBeTruthy();
    expect(screen.getByText("inventory.productDetail.analyticsTab.salesHistory.columns.date")).toBeTruthy();
  });
});