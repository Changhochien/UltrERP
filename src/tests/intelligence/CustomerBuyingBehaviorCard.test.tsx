import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CustomerBuyingBehaviorCard } from "../../domain/intelligence/components/CustomerBuyingBehaviorCard";
import { fetchCustomerBuyingBehavior } from "../../lib/api/intelligence";

vi.mock("../../lib/api/intelligence", () => ({
  fetchCustomerBuyingBehavior: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CustomerBuyingBehaviorCard", () => {
  it("renders summary metrics, category evidence, and cross-sell lift", async () => {
    vi.mocked(fetchCustomerBuyingBehavior).mockResolvedValue({
      customer_type: "dealer",
      period: "3m",
      window: { start_month: "2026-01-01", end_month: "2026-03-01" },
      computed_at: "2026-05-20T04:00:00Z",
      customer_count: 6,
      avg_revenue_per_customer: "116.67",
      avg_order_count_per_customer: "1.00",
      avg_categories_per_customer: "1.50",
      top_categories: [
        {
          category: "Belts",
          revenue: "480.00",
          order_count: 5,
          customer_count: 5,
          revenue_share: "0.6857",
        },
      ],
      cross_sell_opportunities: [
        {
          anchor_category: "Belts",
          recommended_category: "Pulleys",
          anchor_customer_count: 5,
          shared_customer_count: 3,
          outside_segment_anchor_customer_count: 2,
          outside_segment_shared_customer_count: 1,
          segment_penetration: "0.6000",
          outside_segment_penetration: "0.5000",
          lift_score: "1.2000",
        },
      ],
      buying_patterns: [
        { month_start: "2026-01-01", revenue: "0.00", order_count: 0, customer_count: 0 },
        { month_start: "2026-02-01", revenue: "250.00", order_count: 2, customer_count: 2 },
      ],
      data_basis: "transactional_fallback",
      window_is_partial: false,
    });

    render(<CustomerBuyingBehaviorCard />);

    expect(await screen.findByText("Customer Buying Behavior")).toBeTruthy();
    expect(screen.getByText("NT$ 116.67")).toBeTruthy();
    const categoryRows = screen.getAllByTestId("customer-buying-category-row");
    expect(within(categoryRows[0]).getByText("Belts")).toBeTruthy();
    expect(within(categoryRows[0]).getByText("68.6%")).toBeTruthy();
    const crossSellRows = screen.getAllByTestId("customer-buying-cross-sell-row");
    expect(within(crossSellRows[0]).getByText("Pulleys")).toBeTruthy();
    expect(within(crossSellRows[0]).getByText("60.0%")).toBeTruthy();
    expect(within(crossSellRows[0]).getByText("1.20x")).toBeTruthy();
  });

  it("refetches when the segment, period, and current-month toggle change", async () => {
    vi.mocked(fetchCustomerBuyingBehavior).mockResolvedValue({
      customer_type: "dealer",
      period: "12m",
      window: { start_month: "2025-04-01", end_month: "2026-03-01" },
      computed_at: "2026-05-20T04:00:00Z",
      customer_count: 0,
      avg_revenue_per_customer: "0.00",
      avg_order_count_per_customer: "0.00",
      avg_categories_per_customer: "0.00",
      top_categories: [],
      cross_sell_opportunities: [],
      buying_patterns: [],
      data_basis: "transactional_fallback",
      window_is_partial: false,
    });

    render(<CustomerBuyingBehaviorCard />);

    await screen.findByText("Customer Buying Behavior");
    await waitFor(() => {
      expect(fetchCustomerBuyingBehavior).toHaveBeenCalledWith("dealer", "12m", 20, false);
    });

    fireEvent.click(screen.getByRole("button", { name: "End Users" }));
    await waitFor(() => {
      expect(fetchCustomerBuyingBehavior).toHaveBeenCalledWith("end_user", "12m", 20, false);
    });

    fireEvent.click(screen.getByRole("button", { name: "6m" }));
    await waitFor(() => {
      expect(fetchCustomerBuyingBehavior).toHaveBeenCalledWith("end_user", "6m", 20, false);
    });

    fireEvent.click(screen.getByRole("button", { name: "Include current month" }));
    await waitFor(() => {
      expect(fetchCustomerBuyingBehavior).toHaveBeenCalledWith("end_user", "6m", 20, true);
    });
  });

  it("renders the empty state when the selected segment has no qualifying orders", async () => {
    vi.mocked(fetchCustomerBuyingBehavior).mockResolvedValue({
      customer_type: "dealer",
      period: "12m",
      window: { start_month: "2025-04-01", end_month: "2026-03-01" },
      computed_at: "2026-05-20T04:00:00Z",
      customer_count: 0,
      avg_revenue_per_customer: "0.00",
      avg_order_count_per_customer: "0.00",
      avg_categories_per_customer: "0.00",
      top_categories: [],
      cross_sell_opportunities: [],
      buying_patterns: [
        { month_start: "2026-01-01", revenue: "0.00", order_count: 0, customer_count: 0 },
      ],
      data_basis: "transactional_fallback",
      window_is_partial: false,
    });

    render(<CustomerBuyingBehaviorCard />);

    expect(await screen.findByText("No qualifying customer buying behavior for this segment yet.")).toBeTruthy();
  });
});