import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductPerformanceCard } from "../../domain/intelligence/components/ProductPerformanceCard";
import { fetchProductPerformance } from "../../lib/api/intelligence";

vi.mock("../../lib/api/intelligence", () => ({
  fetchProductPerformance: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ProductPerformanceCard", () => {
  it("renders ranked product rows with lifecycle context", async () => {
    vi.mocked(fetchProductPerformance).mockResolvedValue({
      current_window: { start_month: "2026-03-01", end_month: "2026-05-01" },
      prior_window: { start_month: "2025-12-01", end_month: "2026-02-01" },
      computed_at: "2026-05-20T04:00:00Z",
      products: [
        {
          product_id: "prod-1",
          product_name: "Growth Belt",
          product_category_snapshot: "Belts",
          lifecycle_stage: "growing",
          stage_reasons: ["rule:growing"],
          first_sale_month: "2024-01-01",
          last_sale_month: "2026-05-01",
          months_on_sale: 29,
          current_period: {
            revenue: "450.00",
            quantity: "30.000",
            order_count: 8,
            avg_unit_price: "15.00",
          },
          prior_period: {
            revenue: "220.00",
            quantity: "16.000",
            order_count: 5,
            avg_unit_price: "13.75",
          },
          peak_month_revenue: "190.00",
          revenue_delta_pct: 104.5,
          data_basis: "aggregate_plus_live_current_month",
          window_is_partial: true,
        },
      ],
      total: 1,
      data_basis: "aggregate_plus_live_current_month",
      window_is_partial: true,
    });

    render(
      <MemoryRouter>
        <ProductPerformanceCard />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Product Performance")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Growth Belt" }).getAttribute("href")).toBe(
      "/inventory/prod-1?tab=analytics",
    );
    expect(screen.getByText("Belts")).toBeTruthy();
    expect(screen.getByText("Growing", { selector: "div" })).toBeTruthy();
    expect(screen.getByText("Current revenue is at least 20% above the prior comparison window.")).toBeTruthy();
    expect(screen.getByText("+104.5%")).toBeTruthy();
  });

  it("refetches when filters change", async () => {
    vi.mocked(fetchProductPerformance).mockResolvedValue({
      current_window: { start_month: "2026-03-01", end_month: "2026-05-01" },
      prior_window: { start_month: "2025-12-01", end_month: "2026-02-01" },
      computed_at: "2026-05-20T04:00:00Z",
      products: [],
      total: 0,
      data_basis: "aggregate_only",
      window_is_partial: false,
    });

    render(
      <MemoryRouter>
        <ProductPerformanceCard />
      </MemoryRouter>,
    );

    await screen.findByText("Product Performance");
    expect(fetchProductPerformance).toHaveBeenCalledWith(undefined, undefined, 25, false);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "growing" } });
    expect(fetchProductPerformance).toHaveBeenCalledWith(undefined, "growing", 25, false);

    fireEvent.click(screen.getByRole("button", { name: "Include current month" }));
    expect(fetchProductPerformance).toHaveBeenCalledWith(undefined, "growing", 25, true);
  });

  it("renders the empty state when no products qualify", async () => {
    vi.mocked(fetchProductPerformance).mockResolvedValue({
      current_window: { start_month: "2026-03-01", end_month: "2026-05-01" },
      prior_window: { start_month: "2025-12-01", end_month: "2026-02-01" },
      computed_at: "2026-05-20T04:00:00Z",
      products: [],
      total: 0,
      data_basis: "aggregate_only",
      window_is_partial: false,
    });

    render(
      <MemoryRouter>
        <ProductPerformanceCard />
      </MemoryRouter>,
    );

    expect(await screen.findByText("No qualifying products for this comparison window.")).toBeTruthy();
  });
});