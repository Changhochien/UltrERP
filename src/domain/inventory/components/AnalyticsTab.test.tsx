import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { AnalyticsTab } from "./AnalyticsTab";
import { MonthlyDemandChart } from "../components/MonthlyDemandChart";
import { useProductMonthlyDemand } from "../hooks/useProductMonthlyDemand";
import { useProductPlanningSupport } from "../hooks/useProductPlanningSupport";

vi.mock("react-i18next", () => ({
  useTranslation: (_ns?: string, options?: { keyPrefix?: string }) => ({
    t: (key: string) => (options?.keyPrefix ? `${options.keyPrefix}.${key}` : key),
  }),
}));

vi.mock("../hooks/useProductMonthlyDemand", () => ({
  useProductMonthlyDemand: vi.fn(() => ({
    items: [{ month: "2026-03", total_qty: 12 }],
    total: 1,
    loading: false,
    error: null,
  })),
}));

vi.mock("../hooks/useProductSalesHistory", () => ({
  useProductSalesHistory: vi.fn(() => ({
    items: [
      {
        date: "2026-04-10T00:00:00Z",
        quantity_change: -2,
        reason_code: "sales_reservation",
        actor_id: "planner@example.com",
      },
    ],
    total: 1,
    loading: false,
    error: null,
  })),
}));

vi.mock("../hooks/useProductTopCustomer", () => ({
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

vi.mock("../hooks/useStockHistory", () => ({
  useStockHistory: vi.fn(() => ({
    avgDailyUsage: 1.5,
    leadTimeDays: 7,
    safetyStock: 5.25,
  })),
}));

vi.mock("../hooks/useProductPlanningSupport", () => ({
  useProductPlanningSupport: vi.fn(() => ({
    data: {
      product_id: "product-1",
      items: [
        { month: "2026-03", quantity: "12.000", source: "aggregated" },
        { month: "2026-04", quantity: "5.000", source: "live" },
      ],
      avg_monthly_quantity: "8.500",
      peak_monthly_quantity: "12.000",
      low_monthly_quantity: "5.000",
      seasonality_index: "1.412",
      above_average_months: ["2026-03"],
      history_months_used: 2,
      current_month_live_quantity: "5.000",
      reorder_point: 22,
      on_order_qty: 7,
      in_transit_qty: 3,
      reserved_qty: 3,
      data_basis: "aggregated_plus_live_current_month",
      advisory_only: true,
      data_gap: false,
      window: {
        start_month: "2026-03",
        end_month: "2026-04",
        includes_current_month: true,
        is_partial: true,
      },
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

vi.mock("../components/MonthlyDemandChart", () => ({
  MonthlyDemandChart: vi.fn(({ variant }: { variant?: "bar" | "line" }) => (
    <div>monthly-demand-chart-{variant ?? "bar"}</div>
  )),
}));

vi.mock("../components/SalesHistoryTable", () => ({
  SalesHistoryTable: () => <div>sales-history-table</div>,
}));

vi.mock("../components/TopCustomerCard", () => ({
  TopCustomerCard: () => <div>top-customer-card</div>,
}));

vi.mock("../components/AnalyticsSummaryCard", () => ({
  AnalyticsSummaryCard: () => <div>analytics-summary-card</div>,
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("AnalyticsTab", () => {
  it("renders planning support inside the existing analytics layout", () => {
    render(
      <AnalyticsTab
        productId="product-1"
        warehouses={[
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
        ]}
      />,
    );

    expect(screen.getByText("analytics-summary-card")).toBeTruthy();
    expect(screen.getByText("inventory.productDetail.analyticsTab.planningSupport.title")).toBeTruthy();
    expect(screen.getByText("inventory.productDetail.analyticsTab.planningSupport.advisory")).toBeTruthy();
    expect(
      screen.getByText(
        "inventory.productDetail.analyticsTab.planningSupport.dataBasisLabels.aggregated_plus_live_current_month",
      ),
    ).toBeTruthy();
    expect(screen.getByText("inventory.productDetail.analyticsTab.planningSupport.metrics.avgMonthly")).toBeTruthy();
    expect(screen.getByText("inventory.productDetail.analyticsTab.planningSupport.sourceLabels.live")).toBeTruthy();
    expect(screen.getAllByText("2026-03")).toHaveLength(2);
    expect(screen.getByText("monthly-demand-chart-bar")).toBeTruthy();
    expect(screen.getByText("sales-history-table")).toBeTruthy();
    expect(screen.getByText("top-customer-card")).toBeTruthy();
    expect(vi.mocked(useProductMonthlyDemand)).toHaveBeenLastCalledWith("product-1", {
      months: 12,
      includeCurrentMonth: true,
    });
    expect(vi.mocked(MonthlyDemandChart)).toHaveBeenLastCalledWith(
      expect.objectContaining({ variant: "bar" }),
      undefined,
    );
  });

  it("lets the user change the monthly demand time frame", () => {
    render(
      <AnalyticsTab
        productId="product-1"
        warehouses={[
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
        ]}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "inventory.productDetail.analyticsTab.monthlyDemand.period48m",
      }),
    );

    expect(vi.mocked(useProductMonthlyDemand)).toHaveBeenLastCalledWith("product-1", {
      months: 48,
      includeCurrentMonth: true,
    });
  });

  it("lets the user switch the monthly demand chart to line mode", () => {
    render(
      <AnalyticsTab
        productId="product-1"
        warehouses={[
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
        ]}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "inventory.productDetail.analyticsTab.monthlyDemand.chartModeLine",
      }),
    );

    expect(screen.getByText("monthly-demand-chart-line")).toBeTruthy();
    expect(vi.mocked(MonthlyDemandChart)).toHaveBeenLastCalledWith(
      expect.objectContaining({ variant: "line" }),
      undefined,
    );
  });

  it("suppresses planning support when the feature is disabled", () => {
    vi.mocked(useProductPlanningSupport).mockReturnValue({
      data: null,
      loading: false,
      error: "Planning support is disabled",
      refetch: vi.fn(),
    });

    render(
      <AnalyticsTab
        productId="product-1"
        warehouses={[
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
        ]}
      />,
    );

    expect(screen.queryByText("inventory.productDetail.analyticsTab.planningSupport.title")).toBeNull();
    expect(screen.getByText("analytics-summary-card")).toBeTruthy();
    expect(screen.getByText("monthly-demand-chart-bar")).toBeTruthy();
    expect(screen.getByText("sales-history-table")).toBeTruthy();
    expect(screen.getByText("top-customer-card")).toBeTruthy();
  });
});