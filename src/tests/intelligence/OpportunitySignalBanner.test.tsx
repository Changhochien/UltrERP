import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OpportunitySignalBanner } from "../../domain/intelligence/components/OpportunitySignalBanner";

describe("OpportunitySignalBanner", () => {
  it("renders severity-coded banners and expands details", () => {
    render(
      <OpportunitySignalBanner
        signals={[
          {
            signal_type: "concentration_risk",
            severity: "alert",
            headline: "Acme Corp represents 47% of total revenue — concentration risk",
            detail: "Acme Corp contributed NT$ 470.00 of NT$ 1,000.00 total revenue.",
            affected_customer_count: 1,
            revenue_impact: "470.00",
            recommended_action: "Diversify revenue concentration and review mitigation actions.",
            support_counts: { customers_considered: 4 },
            source_period: "last_90d",
          },
        ]}
        deferredSignalTypes={["new_product_adoption", "churn_risk"]}
      />,
    );

    const banner = screen.getByTestId("opportunity-signal-banner");
    expect(banner.className).toContain("bg-red-500");
    expect(screen.getByText("Deferred in v1: new_product_adoption, churn_risk")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Show detail" }));

    expect(screen.getByText(/Diversify revenue concentration/)).toBeTruthy();
    expect(screen.getByText(/Source period:/)).toBeTruthy();
    expect(screen.getByText(/customers_considered=4/)).toBeTruthy();
  });
});