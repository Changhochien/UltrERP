import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { CustomerAnalyticsTab } from "../../components/customers/CustomerAnalyticsTab";
import {
  getCustomerAnalyticsSummary,
  getCustomerRevenueTrend,
} from "../../lib/api/customers";

vi.mock("../../lib/api/customers", () => ({
  getCustomerAnalyticsSummary: vi.fn(),
  getCustomerRevenueTrend: vi.fn(),
}));

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");

  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
    LineChart: ({ children }: { children: React.ReactNode }) => <svg>{children}</svg>,
    CartesianGrid: () => null,
    XAxis: () => null,
    YAxis: () => null,
    Tooltip: () => null,
    Line: () => null,
  };
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CustomerAnalyticsTab", () => {
  it("renders translated analytics labels and chart data", async () => {
    vi.mocked(getCustomerAnalyticsSummary).mockResolvedValue({
      total_revenue_12m: "150000.00",
      invoice_count_12m: 9,
      avg_invoice_value: "16666.67",
      outstanding_balance: "10000.00",
      credit_limit: "50000.00",
      credit_utilization_pct: 20,
      avg_days_to_pay: 18.2,
      payment_score: "prompt",
      days_overdue_avg: 4,
    });
    vi.mocked(getCustomerRevenueTrend).mockResolvedValue({
      trend: [{ month: "2026-03", revenue: "12000.00" }],
    });

    render(<CustomerAnalyticsTab customerId="customer-1" />);

    expect(await screen.findByText("Total Revenue (12 months)")).toBeTruthy();
    expect(screen.getByText("Invoice Count")).toBeTruthy();
    expect(screen.getByText("Prompt")).toBeTruthy();
    expect(screen.getByTestId("responsive-container")).toBeTruthy();
    expect(screen.queryByText("customer.analytics.totalRevenue")).toBeNull();
  });

  it("shows a localized empty state when there is no revenue history", async () => {
    vi.mocked(getCustomerAnalyticsSummary).mockResolvedValue({
      total_revenue_12m: "0.00",
      invoice_count_12m: 0,
      avg_invoice_value: "0.00",
      outstanding_balance: "0.00",
      credit_limit: "50000.00",
      credit_utilization_pct: 0,
      avg_days_to_pay: null,
      payment_score: "at_risk",
      days_overdue_avg: null,
    });
    vi.mocked(getCustomerRevenueTrend).mockResolvedValue({
      trend: [],
    });

    render(<CustomerAnalyticsTab customerId="customer-1" />);

    expect(await screen.findByText("No revenue activity yet")).toBeTruthy();
    expect(
      screen.getByText("This customer has no invoice revenue in the last 12 months."),
    ).toBeTruthy();
  });
});