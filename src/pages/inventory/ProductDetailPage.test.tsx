import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const mocks = vi.hoisted(() => ({
  product: {
    id: "product-1",
    code: "SKU-1",
    name: "Widget",
    category: "Hardware",
    description: "Original description",
    unit: "pcs",
    standard_cost: "5.2500",
    status: "active",
    total_stock: 12,
    warehouses: [
      {
        stock_id: "stock-1",
        warehouse_id: "warehouse-1",
        warehouse_name: "Main Warehouse",
        current_stock: 12,
        reorder_point: 5,
        safety_factor: 0.5,
        lead_time_days: 7,
        policy_type: "periodic",
        target_stock_qty: 0,
        on_order_qty: 0,
        in_transit_qty: 0,
        reserved_qty: 0,
        planning_horizon_days: 30,
        review_cycle_days: 85,
        is_below_reorder: false,
        last_adjusted: null,
      },
    ],
    adjustment_history: [],
  },
  updatedProduct: {
    id: "product-1",
    code: "SKU-2",
    name: "Widget Pro",
    category: "Hardware",
    description: "Updated description",
    unit: "box",
    standard_cost: "7.1250",
    status: "active",
    created_at: "2026-04-01T00:00:00Z",
  },
  reload: vi.fn(),
  applyLocalUpdate: vi.fn(),
  setProductStatus: vi.fn(),
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
    reload: mocks.reload,
    applyLocalUpdate: mocks.applyLocalUpdate,
  })),
}));

vi.mock("@/lib/api/inventory", () => ({
  setProductStatus: (...args: unknown[]) => mocks.setProductStatus(...args),
}));

vi.mock("@/domain/inventory/components/EditProductForm", () => ({
  EditProductForm: ({ onSuccess }: { onSuccess: (product: typeof mocks.updatedProduct) => void }) => (
    <button type="button" onClick={() => onSuccess(mocks.updatedProduct)}>
      mock-save-edit
    </button>
  ),
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

vi.mock("@/domain/inventory/components/AnalyticsTab", () => ({
  AnalyticsTab: () => (
    <div>
      <div>inventory.productDetail.analyticsTab.summary.title</div>
      <div>inventory.productDetail.analyticsTab.monthlyDemand.title</div>
      <div>inventory.productDetail.analyticsTab.salesHistory.title</div>
      <div>inventory.productDetail.analyticsTab.topCustomer.title</div>
      <div>inventory.productDetail.analyticsTab.salesHistory.columns.date</div>
    </div>
  ),
}));

afterEach(() => {
  cleanup();
  mocks.reload.mockReset();
  mocks.applyLocalUpdate.mockReset();
  mocks.setProductStatus.mockReset();
  vi.restoreAllMocks();
});

describe("ProductDetailPage", () => {
  it("renders translated product detail copy and shows analytics content when the analytics tab is selected", async () => {
    const { ProductDetailPage } = await import("./ProductDetailPage");

    render(
      <MemoryRouter initialEntries={["/inventory/product-1"]}>
        <Routes>
          <Route path="/inventory/:productId" element={<ProductDetailPage />} />
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

  it("opens directly on the settings tab when tab=settings is provided", async () => {
    const { ProductDetailPage } = await import("./ProductDetailPage");

    render(
      <MemoryRouter initialEntries={["/inventory/product-1?tab=settings"]}>
        <Routes>
          <Route path="/inventory/:productId" element={<ProductDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("inventory.productDetail.settingsTab.reorderPoint")).toBeTruthy();
    expect(screen.getByText("inventory.productDetail.settingsTab.reviewCycle")).toBeTruthy();
  });

  it("opens the edit dialog and refreshes the product detail after save", async () => {
    const { ProductDetailPage } = await import("./ProductDetailPage");

    render(
      <MemoryRouter initialEntries={["/inventory/product-1"]}>
        <Routes>
          <Route path="/inventory/:productId" element={<ProductDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "inventory.productDetail.edit" }));
    fireEvent.click(screen.getByRole("button", { name: "mock-save-edit" }));

    await waitFor(() => {
      expect(mocks.applyLocalUpdate).toHaveBeenCalledWith(mocks.updatedProduct);
    });
    await waitFor(() => {
      expect(mocks.reload).toHaveBeenCalled();
    });
  });

  it("confirms deactivation before updating product status", async () => {
    mocks.setProductStatus.mockResolvedValue({
      ok: true,
      data: {
        ...mocks.updatedProduct,
        status: "inactive",
      },
    });

    const { ProductDetailPage } = await import("./ProductDetailPage");

    render(
      <MemoryRouter initialEntries={["/inventory/product-1"]}>
        <Routes>
          <Route path="/inventory/:productId" element={<ProductDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "inventory.productDetail.deactivate" }));
    fireEvent.click(screen.getByRole("button", { name: "inventory.productDetail.confirmDeactivate" }));

    await waitFor(() => {
      expect(mocks.setProductStatus).toHaveBeenCalledWith("product-1", "inactive");
    });
    await waitFor(() => {
      expect(mocks.applyLocalUpdate).toHaveBeenCalledWith({
        ...mocks.updatedProduct,
        status: "inactive",
      });
    });
    await waitFor(() => {
      expect(mocks.reload).toHaveBeenCalled();
    });
  });
});