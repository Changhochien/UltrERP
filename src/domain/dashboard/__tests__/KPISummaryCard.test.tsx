import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { KPISummaryCard } from "../components/KPISummaryCard";
import type { KPISummary } from "../types";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const mockData: KPISummary = {
  today_revenue: "50000.00",
  yesterday_revenue: "45000.00",
  revenue_change_pct: "11.1",
  open_invoice_count: 12,
  open_invoice_amount: "250000.00",
  pending_order_count: 7,
  pending_order_revenue: "85000.00",
  low_stock_product_count: 5,
  overdue_receivables_amount: "30000.00",
};

describe("KPISummaryCard", () => {
  it("renders loading skeleton", () => {
    render(<KPISummaryCard data={null} isLoading={true} error={null} onRetry={vi.fn()} />);
    expect(screen.getByTestId("kpi-card-loading")).toBeTruthy();
  });

  it("renders error state with retry button", () => {
    const onRetry = vi.fn();
    render(<KPISummaryCard data={null} isLoading={false} error="Network error" onRetry={onRetry} />);
    expect(screen.getByText("Network error")).toBeTruthy();
    const retryBtn = screen.getByRole("button", { name: /retry/i });
    expect(retryBtn).toBeTruthy();
  });

  it("retry button triggers onRetry callback", () => {
    const onRetry = vi.fn();
    render(<KPISummaryCard data={null} isLoading={false} error="Network error" onRetry={onRetry} />);
    screen.getByRole("button", { name: /retry/i }).click();
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders all KPI fields when data loads", () => {
    render(<KPISummaryCard data={mockData} isLoading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByTestId("kpi-card")).toBeTruthy();
    expect(screen.getByText(/NT\$ 50,000\.00/)).toBeTruthy();
    expect(screen.getByText("12")).toBeTruthy();
    expect(screen.getByText(/NT\$ 250,000\.00/)).toBeTruthy();
    expect(screen.getByText("7")).toBeTruthy();
    expect(screen.getByText(/NT\$ 85,000\.00/)).toBeTruthy();
    expect(screen.getByText("5")).toBeTruthy();
    expect(screen.getByText(/NT\$ 30,000\.00/)).toBeTruthy();
  });

  it("renders null when no data and not loading", () => {
    const { container } = render(<KPISummaryCard data={null} isLoading={false} error={null} onRetry={vi.fn()} />);
    expect(container.innerHTML).toBe("");
  });
});
