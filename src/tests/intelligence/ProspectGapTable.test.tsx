import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProspectGapTable } from "../../domain/intelligence/components/ProspectGapTable";
import { fetchCategoryTrends, fetchProspectGaps } from "../../lib/api/intelligence";

vi.mock("../../lib/api/intelligence", () => ({
  fetchCategoryTrends: vi.fn(),
  fetchProspectGaps: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ProspectGapTable", () => {
  it("renders prospects ranked by affinity score with the buyer badge", async () => {
    vi.mocked(fetchCategoryTrends).mockResolvedValue({
      period: "last_12m",
      generated_at: "2026-04-14T03:30:00Z",
      trends: [
        { category: "Electronics", current_period_revenue: "500.00", prior_period_revenue: "100.00", revenue_delta_pct: 400, current_period_orders: 2, prior_period_orders: 1, order_delta_pct: 100, customer_count: 2, prior_customer_count: 1, new_customer_count: 0, churned_customer_count: 0, top_products: [], trend: "growing", trend_context: null, activity_basis: "confirmed_or_later_orders" },
      ],
    });
    vi.mocked(fetchProspectGaps).mockResolvedValue({
      target_category: "Electronics",
      target_category_revenue: "500.00",
      existing_buyers_count: 2,
      prospects_count: 2,
      available_categories: ["Electronics", "Supplies"],
      generated_at: "2026-04-14T03:30:00Z",
      prospects: [
        {
          customer_id: "warm",
          company_name: "Warm Prospect",
          total_revenue: "330.00",
          category_count: 2,
          avg_order_value: "165.00",
          last_order_date: "2026-03-25",
          affinity_score: 0.78,
          score_components: {
            frequency_similarity: 0.8,
            breadth_similarity: 0.75,
            adjacent_category_support: 0.66,
            recency_factor: 0.8,
          },
          reason_codes: ["adjacent_category_support"],
          confidence: "high",
          reason: "Warm Prospect is a fit candidate and buys 2 adjacent categories.",
          tags: ["adjacent_category", "high_value"],
        },
        {
          customer_id: "cold",
          company_name: "Cold Prospect",
          total_revenue: "90.00",
          category_count: 1,
          avg_order_value: "90.00",
          last_order_date: "2026-03-05",
          affinity_score: 0.24,
          score_components: {
            frequency_similarity: 0.2,
            breadth_similarity: 0.2,
            adjacent_category_support: 0,
            recency_factor: 0.4,
          },
          reason_codes: [],
          confidence: "low",
          reason: "Cold Prospect is a fit candidate.",
          tags: [],
        },
      ],
    });

    render(<ProspectGapTable defaultCategory="Electronics" />);

    expect(await screen.findByText("Prospect Gap Analysis")).toBeTruthy();
    await waitFor(() => {
      expect(fetchProspectGaps).toHaveBeenCalledWith("Electronics", "dealer", 20);
    });
    expect(await screen.findByText("2 existing buyers")).toBeTruthy();
    const rows = screen.getAllByTestId("prospect-gap-row");
    expect(within(rows[0]).getByText("Warm Prospect")).toBeTruthy();
    expect(within(rows[0]).getByText("78.0%")).toBeTruthy();
  });

  it("refetches when the category changes", async () => {
    vi.mocked(fetchCategoryTrends).mockResolvedValue({
      period: "last_12m",
      generated_at: "2026-04-14T03:30:00Z",
      trends: [
        { category: "Electronics", current_period_revenue: "500.00", prior_period_revenue: "100.00", revenue_delta_pct: 400, current_period_orders: 2, prior_period_orders: 1, order_delta_pct: 100, customer_count: 2, prior_customer_count: 1, new_customer_count: 0, churned_customer_count: 0, top_products: [], trend: "growing", trend_context: null, activity_basis: "confirmed_or_later_orders" },
        { category: "Supplies", current_period_revenue: "300.00", prior_period_revenue: "200.00", revenue_delta_pct: 50, current_period_orders: 2, prior_period_orders: 1, order_delta_pct: 100, customer_count: 2, prior_customer_count: 1, new_customer_count: 0, churned_customer_count: 0, top_products: [], trend: "growing", trend_context: null, activity_basis: "confirmed_or_later_orders" },
      ],
    });
    vi.mocked(fetchProspectGaps).mockResolvedValue({
      target_category: "Electronics",
      target_category_revenue: "500.00",
      existing_buyers_count: 2,
      prospects_count: 0,
      available_categories: ["Electronics", "Supplies"],
      generated_at: "2026-04-14T03:30:00Z",
      prospects: [],
    });

    render(<ProspectGapTable defaultCategory="Electronics" />);

    await screen.findByText("Prospect Gap Analysis");
    await waitFor(() => {
      expect(fetchProspectGaps).toHaveBeenCalledWith("Electronics", "dealer", 20);
    });

    fireEvent.change(screen.getByRole("combobox", { name: "Target Category" }), {
      target: { value: "Supplies" },
    });

    await waitFor(() => {
      expect(fetchProspectGaps).toHaveBeenCalledWith("Supplies", "dealer", 20);
    });
  });

  it("refetches when the customer type chip changes", async () => {
    vi.mocked(fetchCategoryTrends).mockResolvedValue({
      period: "last_12m",
      generated_at: "2026-04-14T03:30:00Z",
      trends: [
        { category: "Electronics", current_period_revenue: "500.00", prior_period_revenue: "100.00", revenue_delta_pct: 400, current_period_orders: 2, prior_period_orders: 1, order_delta_pct: 100, customer_count: 2, prior_customer_count: 1, new_customer_count: 0, churned_customer_count: 0, top_products: [], trend: "growing", trend_context: null, activity_basis: "confirmed_or_later_orders" },
      ],
    });
    vi.mocked(fetchProspectGaps).mockResolvedValue({
      target_category: "Electronics",
      target_category_revenue: "500.00",
      existing_buyers_count: 2,
      prospects_count: 0,
      available_categories: ["Electronics"],
      generated_at: "2026-04-14T03:30:00Z",
      prospects: [],
    });

    render(<ProspectGapTable defaultCategory="Electronics" />);

    await screen.findByText("Prospect Gap Analysis");
    await waitFor(() => {
      expect(fetchProspectGaps).toHaveBeenCalledWith("Electronics", "dealer", 20);
    });

    fireEvent.click(screen.getByRole("button", { name: "End Users" }));

    await waitFor(() => {
      expect(fetchProspectGaps).toHaveBeenCalledWith("Electronics", "end_user", 20);
    });

    fireEvent.click(screen.getByRole("button", { name: "All" }));

    await waitFor(() => {
      expect(fetchProspectGaps).toHaveBeenCalledWith("Electronics", "all", 20);
    });
  });

  it("renders the empty state when no prospects match the category", async () => {
    vi.mocked(fetchCategoryTrends).mockResolvedValue({
      period: "last_12m",
      generated_at: "2026-04-14T03:30:00Z",
      trends: [
        { category: "Electronics", current_period_revenue: "0.00", prior_period_revenue: "0.00", revenue_delta_pct: null, current_period_orders: 0, prior_period_orders: 0, order_delta_pct: null, customer_count: 0, prior_customer_count: 0, new_customer_count: 0, churned_customer_count: 0, top_products: [], trend: "stable", trend_context: "insufficient_history", activity_basis: "confirmed_or_later_orders" },
      ],
    });
    vi.mocked(fetchProspectGaps).mockResolvedValue({
      target_category: "Electronics",
      target_category_revenue: "0.00",
      existing_buyers_count: 0,
      prospects_count: 0,
      available_categories: ["Electronics"],
      generated_at: "2026-04-14T03:30:00Z",
      prospects: [],
    });

    render(<ProspectGapTable defaultCategory="Electronics" />);

    expect(await screen.findByText("No whitespace prospects for this category yet.")).toBeTruthy();
  });

  it("does not issue an invalid starter request before categories are known", async () => {
    vi.mocked(fetchCategoryTrends).mockResolvedValue({
      period: "last_12m",
      generated_at: "2026-04-14T03:30:00Z",
      trends: [
        { category: "Electronics", current_period_revenue: "500.00", prior_period_revenue: "100.00", revenue_delta_pct: 400, current_period_orders: 2, prior_period_orders: 1, order_delta_pct: 100, customer_count: 2, prior_customer_count: 1, new_customer_count: 0, churned_customer_count: 0, top_products: [], trend: "growing", trend_context: null, activity_basis: "confirmed_or_later_orders" },
      ],
    });
    vi.mocked(fetchProspectGaps).mockResolvedValue({
      target_category: "Electronics",
      target_category_revenue: "500.00",
      existing_buyers_count: 2,
      prospects_count: 0,
      prospects: [],
    });

    render(<ProspectGapTable />);

    await screen.findByText("Prospect Gap Analysis");
    await waitFor(() => {
      expect(fetchProspectGaps).toHaveBeenCalledTimes(1);
    });
    expect(fetchProspectGaps).toHaveBeenCalledWith("Electronics", "dealer", 20);
  });
});