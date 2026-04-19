import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CustomerProductProfile } from "../../domain/intelligence/components/CustomerProductProfile";
import { fetchCustomerProductProfile } from "../../lib/api/intelligence";

vi.mock("../../lib/api/intelligence", () => ({
  fetchCustomerProductProfile: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CustomerProductProfile", () => {
  it("renders dormant badge and new-category chips", async () => {
    vi.mocked(fetchCustomerProductProfile).mockResolvedValue({
      customer_id: "customer-1",
      company_name: "Acme Trading",
      total_revenue_12m: "570.00",
      order_count_12m: 3,
      order_count_3m: 2,
      order_count_6m: 3,
      order_count_prior_12m: 1,
      order_count_prior_3m: 1,
      frequency_trend: "increasing",
      avg_order_value: "190.00",
      avg_order_value_prior: "90.00",
      aov_trend: "increasing",
      top_categories: [
        {
          category: "Supplies",
          revenue: "350.00",
          order_count: 2,
          revenue_pct_of_total: "0.6140",
        },
      ],
      top_products: [
        {
          product_id: "prod-1",
          product_name: "Printer Ink",
          category: "Supplies",
          order_count: 2,
          total_quantity: "3.000",
          total_revenue: "200.00",
        },
      ],
      last_order_date: "2026-03-24",
      days_since_last_order: 20,
      is_dormant: true,
      new_categories: ["Supplies"],
      confidence: "medium",
      activity_basis: "confirmed_or_later_orders",
    });

    render(<CustomerProductProfile customerId="customer-1" />);

    expect(await screen.findByText("Product Profile")).toBeTruthy();
    expect(screen.getByText("Dormant")).toBeTruthy();
    expect(screen.getByText("New")).toBeTruthy();
    expect(screen.getByText("Printer Ink")).toBeTruthy();
  });

  it("renders empty states when there is no product activity", async () => {
    vi.mocked(fetchCustomerProductProfile).mockResolvedValue({
      customer_id: "customer-1",
      company_name: "Quiet Account",
      total_revenue_12m: "0.00",
      order_count_12m: 0,
      order_count_3m: 0,
      order_count_6m: 0,
      order_count_prior_12m: 0,
      order_count_prior_3m: 0,
      frequency_trend: "stable",
      avg_order_value: "0.00",
      avg_order_value_prior: "0.00",
      aov_trend: "stable",
      top_categories: [],
      top_products: [],
      last_order_date: null,
      days_since_last_order: null,
      is_dormant: true,
      new_categories: [],
      confidence: "low",
      activity_basis: "confirmed_or_later_orders",
    });

    render(<CustomerProductProfile customerId="customer-1" />);

    expect(await screen.findByText("No category activity yet.")).toBeTruthy();
    expect(screen.getByText("No product activity yet.")).toBeTruthy();
  });
});