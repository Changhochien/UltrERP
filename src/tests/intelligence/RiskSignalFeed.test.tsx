import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RiskSignalFeed } from "../../domain/intelligence/components/RiskSignalFeed";
import { fetchCustomerRiskSignals } from "../../lib/api/intelligence";

vi.mock("../../lib/api/intelligence", () => ({
  fetchCustomerRiskSignals: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("RiskSignalFeed", () => {
  it("renders the ranked risk signal cards", async () => {
    vi.mocked(fetchCustomerRiskSignals).mockResolvedValue({
      customers: [
        {
          customer_id: "cust-1",
          company_name: "Dormant Co",
          status: "dormant",
          revenue_current: "300.00",
          revenue_prior: "400.00",
          revenue_delta_pct: -25,
          order_count_current: 1,
          order_count_prior: 1,
          avg_order_value_current: "300.00",
          avg_order_value_prior: "400.00",
          days_since_last_order: 80,
          reason_codes: ["dormant_60d"],
          confidence: "medium",
          signals: ["no orders in 80 days"],
          products_expanded_into: [],
          products_contracted_from: ["Office"],
          last_order_date: "2026-01-20",
          first_order_date: "2024-01-20",
        },
        {
          customer_id: "cust-2",
          company_name: "Growing Co",
          status: "growing",
          revenue_current: "320.00",
          revenue_prior: "120.00",
          revenue_delta_pct: 166.7,
          order_count_current: 1,
          order_count_prior: 1,
          avg_order_value_current: "320.00",
          avg_order_value_prior: "120.00",
          days_since_last_order: 20,
          reason_codes: ["revenue_growth_20pct"],
          confidence: "medium",
          signals: ["revenue up 167%"],
          products_expanded_into: ["Displays"],
          products_contracted_from: [],
          last_order_date: "2026-03-20",
          first_order_date: "2024-02-20",
        },
      ],
      total: 2,
      status_filter: "all",
      limit: 50,
      generated_at: "2026-04-14T03:00:00Z",
    });

    render(<RiskSignalFeed />);

    expect(await screen.findByText("Customer Risk Signals")).toBeTruthy();
    const cards = screen.getAllByTestId("risk-signal-card");
    expect(cards).toHaveLength(2);
    expect(screen.getByText("Dormant Co")).toBeTruthy();
    expect(screen.getByText("Growing Co")).toBeTruthy();
    expect(screen.getByTestId("risk-badge-dormant").className).toContain("tone-warning");
    expect(screen.getByTestId("risk-badge-growing").className).toContain("tone-success");
  });

  it("refetches when a status filter is selected", async () => {
    vi.mocked(fetchCustomerRiskSignals).mockResolvedValue({
      customers: [],
      total: 0,
      status_filter: "all",
      limit: 50,
      generated_at: "2026-04-14T03:00:00Z",
    });

    render(<RiskSignalFeed />);

    await screen.findByText("Customer Risk Signals");
    expect(fetchCustomerRiskSignals).toHaveBeenCalledWith("all", 50);

    fireEvent.click(screen.getByRole("button", { name: "At Risk" }));

    expect(fetchCustomerRiskSignals).toHaveBeenCalledWith("at_risk", 50);
  });

  it("renders the empty state when no customers match the filter", async () => {
    vi.mocked(fetchCustomerRiskSignals).mockResolvedValue({
      customers: [],
      total: 0,
      status_filter: "all",
      limit: 50,
      generated_at: "2026-04-14T03:00:00Z",
    });

    render(<RiskSignalFeed />);

    expect(await screen.findByText("No customer risk signals yet.")).toBeTruthy();
  });

  it("uses the expected badge variant for every status", async () => {
    vi.mocked(fetchCustomerRiskSignals).mockResolvedValue({
      customers: [
        {
          customer_id: "cust-a",
          company_name: "At Risk Co",
          status: "at_risk",
          revenue_current: "80.00",
          revenue_prior: "300.00",
          revenue_delta_pct: -73.3,
          order_count_current: 1,
          order_count_prior: 1,
          avg_order_value_current: "80.00",
          avg_order_value_prior: "300.00",
          days_since_last_order: 30,
          reason_codes: ["revenue_decline_20pct"],
          confidence: "medium",
          signals: [],
          products_expanded_into: [],
          products_contracted_from: [],
          last_order_date: "2026-03-15",
          first_order_date: "2024-03-15",
        },
        {
          customer_id: "cust-b",
          company_name: "New Co",
          status: "new",
          revenue_current: "90.00",
          revenue_prior: "0.00",
          revenue_delta_pct: null,
          order_count_current: 1,
          order_count_prior: 0,
          avg_order_value_current: "90.00",
          avg_order_value_prior: "0.00",
          days_since_last_order: 10,
          reason_codes: ["new_account_90d"],
          confidence: "low",
          signals: [],
          products_expanded_into: [],
          products_contracted_from: [],
          last_order_date: "2026-04-04",
          first_order_date: "2026-04-04",
        },
        {
          customer_id: "cust-c",
          company_name: "Stable Co",
          status: "stable",
          revenue_current: "200.00",
          revenue_prior: "195.00",
          revenue_delta_pct: 2.6,
          order_count_current: 1,
          order_count_prior: 1,
          avg_order_value_current: "200.00",
          avg_order_value_prior: "195.00",
          days_since_last_order: 14,
          reason_codes: ["stable_demand"],
          confidence: "medium",
          signals: [],
          products_expanded_into: [],
          products_contracted_from: [],
          last_order_date: "2026-03-31",
          first_order_date: "2024-03-31",
        },
      ],
      total: 3,
      status_filter: "all",
      limit: 50,
      generated_at: "2026-04-14T03:00:00Z",
    });

    render(<RiskSignalFeed />);

    expect(await screen.findByText("Customer Risk Signals")).toBeTruthy();
    expect(screen.getByTestId("risk-badge-at_risk").className).toContain("tone-destructive");
    expect(screen.getByTestId("risk-badge-new").className).toContain("tone-info");
    expect(screen.getByTestId("risk-badge-stable").className).toContain("bg-secondary");
  });
});