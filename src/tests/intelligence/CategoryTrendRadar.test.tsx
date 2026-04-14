import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CategoryTrendRadar } from "../../domain/intelligence/components/CategoryTrendRadar";
import { fetchCategoryTrends, fetchMarketOpportunities } from "../../lib/api/intelligence";

vi.mock("../../lib/api/intelligence", () => ({
  fetchCategoryTrends: vi.fn(),
  fetchMarketOpportunities: vi.fn(),
}));

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="recharts-container">{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="recharts-bar-chart">{children}</div>,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  Bar: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  Cell: () => null,
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CategoryTrendRadar", () => {
  it("renders categories ranked by revenue delta descending", async () => {
    vi.mocked(fetchMarketOpportunities).mockResolvedValue({
      period: "last_90d",
      generated_at: "2026-04-14T02:10:00Z",
      signals: [],
      deferred_signal_types: ["new_product_adoption", "churn_risk"],
    });
    vi.mocked(fetchCategoryTrends).mockResolvedValue({
      period: "last_90d",
      generated_at: "2026-04-14T02:10:00Z",
      trends: [
        {
          category: "Office",
          current_period_revenue: "0.00",
          prior_period_revenue: "150.00",
          revenue_delta_pct: -100,
          current_period_orders: 0,
          prior_period_orders: 1,
          order_delta_pct: -100,
          customer_count: 0,
          prior_customer_count: 1,
          new_customer_count: 0,
          churned_customer_count: 1,
          top_products: [],
          trend: "declining",
          trend_context: null,
          activity_basis: "confirmed_or_later_orders",
        },
        {
          category: "Supplies",
          current_period_revenue: "300.00",
          prior_period_revenue: "100.00",
          revenue_delta_pct: 200,
          current_period_orders: 2,
          prior_period_orders: 1,
          order_delta_pct: 100,
          customer_count: 2,
          prior_customer_count: 1,
          new_customer_count: 1,
          churned_customer_count: 0,
          top_products: [
            { product_id: "p2", product_name: "Laser Toner", revenue: "180.00" },
          ],
          trend: "growing",
          trend_context: null,
          activity_basis: "confirmed_or_later_orders",
        },
      ],
    });

    render(<CategoryTrendRadar />);

    expect(await screen.findByText("Category Trend Radar")).toBeTruthy();
    expect(screen.getByTestId("category-trend-chart")).toBeTruthy();
    const rows = screen.getAllByRole("row");
    const firstDataRow = rows[1];
    expect(within(firstDataRow).getByText("Supplies")).toBeTruthy();
    expect(within(firstDataRow).getByText("+200.00%")).toBeTruthy();
  });

  it("refetches when the period button changes", async () => {
    vi.mocked(fetchMarketOpportunities).mockResolvedValue({
      period: "last_90d",
      generated_at: "2026-04-14T02:10:00Z",
      signals: [],
      deferred_signal_types: ["new_product_adoption", "churn_risk"],
    });
    vi.mocked(fetchCategoryTrends).mockResolvedValue({
      period: "last_90d",
      generated_at: "2026-04-14T02:10:00Z",
      trends: [],
    });

    render(<CategoryTrendRadar />);

    await screen.findByText("Category Trend Radar");
    expect(fetchCategoryTrends).toHaveBeenCalledWith("last_90d");
    expect(fetchMarketOpportunities).toHaveBeenCalledWith("last_90d");

    fireEvent.click(screen.getByRole("button", { name: "30d" }));

    expect(fetchCategoryTrends).toHaveBeenCalledWith("last_30d");
    expect(fetchMarketOpportunities).toHaveBeenCalledWith("last_30d");
  });

  it("renders the empty state when no trends qualify", async () => {
    vi.mocked(fetchMarketOpportunities).mockResolvedValue({
      period: "last_90d",
      generated_at: "2026-04-14T02:10:00Z",
      signals: [],
      deferred_signal_types: ["new_product_adoption", "churn_risk"],
    });
    vi.mocked(fetchCategoryTrends).mockResolvedValue({
      period: "last_90d",
      generated_at: "2026-04-14T02:10:00Z",
      trends: [],
    });

    render(<CategoryTrendRadar />);

    expect(await screen.findByText("No category demand signals yet.")).toBeTruthy();
  });

  it("ignores stale responses when the selected period changes", async () => {
    vi.mocked(fetchMarketOpportunities).mockResolvedValue({
      period: "last_90d",
      generated_at: "2026-04-14T02:10:00Z",
      signals: [],
      deferred_signal_types: ["new_product_adoption", "churn_risk"],
    });
    let resolveFirst: ((value: Awaited<ReturnType<typeof fetchCategoryTrends>>) => void) | undefined;
    let resolveSecond: ((value: Awaited<ReturnType<typeof fetchCategoryTrends>>) => void) | undefined;

    vi.mocked(fetchCategoryTrends)
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirst = resolve;
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecond = resolve;
          }),
      );

    render(<CategoryTrendRadar />);

    fireEvent.click(await screen.findByRole("button", { name: "30d" }));

    resolveSecond?.({
      period: "last_30d",
      generated_at: "2026-04-14T02:10:00Z",
      trends: [
        {
          category: "Current Window",
          current_period_revenue: "200.00",
          prior_period_revenue: "50.00",
          revenue_delta_pct: 300,
          current_period_orders: 2,
          prior_period_orders: 1,
          order_delta_pct: 100,
          customer_count: 2,
          prior_customer_count: 1,
          new_customer_count: 1,
          churned_customer_count: 0,
          top_products: [],
          trend: "growing",
          trend_context: null,
          activity_basis: "confirmed_or_later_orders",
        },
      ],
    });

    expect(await screen.findByText("Current Window")).toBeTruthy();

    resolveFirst?.({
      period: "last_90d",
      generated_at: "2026-04-14T02:10:00Z",
      trends: [
        {
          category: "Stale Window",
          current_period_revenue: "10.00",
          prior_period_revenue: "10.00",
          revenue_delta_pct: 0,
          current_period_orders: 1,
          prior_period_orders: 1,
          order_delta_pct: 0,
          customer_count: 1,
          prior_customer_count: 1,
          new_customer_count: 0,
          churned_customer_count: 0,
          top_products: [],
          trend: "stable",
          trend_context: null,
          activity_basis: "confirmed_or_later_orders",
        },
      ],
    });

    await waitFor(() => {
      expect(screen.queryByText("Stale Window")).toBeNull();
    });
  });
});