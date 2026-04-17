import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RevenueDiagnosisCard } from "../../domain/intelligence/components/RevenueDiagnosisCard";
import { fetchRevenueDiagnosis } from "../../lib/api/intelligence";

vi.mock("../../lib/api/intelligence", () => ({
  fetchRevenueDiagnosis: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("RevenueDiagnosisCard", () => {
  it("renders summary metrics and ranked driver rows", async () => {
    vi.mocked(fetchRevenueDiagnosis).mockResolvedValue({
      period: "1m",
      anchor_month: "2026-03-01",
      current_window: { start_month: "2026-03-01", end_month: "2026-03-01" },
      prior_window: { start_month: "2026-02-01", end_month: "2026-02-01" },
      computed_at: "2026-04-16T03:00:00Z",
      summary: {
        current_revenue: "170.00",
        prior_revenue: "200.00",
        revenue_delta: "-30.00",
        revenue_delta_pct: -15,
      },
      components: {
        price_effect_total: "20.00",
        volume_effect_total: "-25.00",
        mix_effect_total: "-25.00",
      },
      drivers: [
        {
          product_id: "prod-2",
          product_name: "Beta Pulley",
          product_category_snapshot: "Pulleys",
          current_quantity: "5.000",
          prior_quantity: "10.000",
          current_revenue: "50.00",
          prior_revenue: "100.00",
          current_order_count: 1,
          prior_order_count: 1,
          current_avg_unit_price: "10.00",
          prior_avg_unit_price: "10.00",
          price_effect: "0.00",
          volume_effect: "-25.00",
          mix_effect: "-25.00",
          revenue_delta: "-50.00",
          revenue_delta_pct: -50,
          data_basis: "aggregate_only",
          window_is_partial: false,
        },
      ],
      data_basis: "aggregate_only",
      window_is_partial: false,
    });

    render(<RevenueDiagnosisCard />);

    expect(await screen.findByText("Revenue Diagnosis")).toBeTruthy();
    expect(screen.getByText("NT$ 170.00")).toBeTruthy();
    expect(screen.getByText("Beta Pulley")).toBeTruthy();
    expect(screen.getByText("Pulleys")).toBeTruthy();
    expect(screen.getByText("-50.0%")).toBeTruthy();
  });

  it("refetches when the period changes", async () => {
    vi.mocked(fetchRevenueDiagnosis).mockResolvedValue({
      period: "1m",
      anchor_month: "2026-03-01",
      current_window: { start_month: "2026-03-01", end_month: "2026-03-01" },
      prior_window: { start_month: "2026-02-01", end_month: "2026-02-01" },
      computed_at: "2026-04-16T03:00:00Z",
      summary: {
        current_revenue: "0.00",
        prior_revenue: "0.00",
        revenue_delta: "0.00",
        revenue_delta_pct: null,
      },
      components: {
        price_effect_total: "0.00",
        volume_effect_total: "0.00",
        mix_effect_total: "0.00",
      },
      drivers: [],
      data_basis: "aggregate_only",
      window_is_partial: false,
    });

    render(<RevenueDiagnosisCard />);

    await screen.findByText("Revenue Diagnosis");
    expect(fetchRevenueDiagnosis).toHaveBeenCalledWith("1m", undefined, undefined, 10);

    fireEvent.click(screen.getByRole("button", { name: "3m" }));

    expect(fetchRevenueDiagnosis).toHaveBeenCalledWith("3m", undefined, undefined, 10);
  });

  it("renders the empty state when there are no qualifying drivers", async () => {
    vi.mocked(fetchRevenueDiagnosis).mockResolvedValue({
      period: "1m",
      anchor_month: "2026-03-01",
      current_window: { start_month: "2026-03-01", end_month: "2026-03-01" },
      prior_window: { start_month: "2026-02-01", end_month: "2026-02-01" },
      computed_at: "2026-04-16T03:00:00Z",
      summary: {
        current_revenue: "0.00",
        prior_revenue: "0.00",
        revenue_delta: "0.00",
        revenue_delta_pct: null,
      },
      components: {
        price_effect_total: "0.00",
        volume_effect_total: "0.00",
        mix_effect_total: "0.00",
      },
      drivers: [],
      data_basis: "aggregate_only",
      window_is_partial: false,
    });

    render(<RevenueDiagnosisCard />);

    expect(await screen.findByText("No qualifying revenue drivers for this comparison window.")).toBeTruthy();
  });

  it("suppresses the card when the feature is disabled", async () => {
    vi.mocked(fetchRevenueDiagnosis).mockRejectedValue(new Error("Revenue diagnosis is disabled"));

    render(<RevenueDiagnosisCard />);

    await waitFor(() => {
      expect(screen.queryByText("Revenue Diagnosis")).toBeNull();
    });
  });
});
