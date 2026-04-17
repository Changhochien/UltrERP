import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { GrossMarginCard } from "./GrossMarginCard";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("GrossMarginCard", () => {
  it("shows the unavailable state when the backend marks margin data incomplete", () => {
    render(
      <GrossMarginCard
        data={{
          available: false,
          gross_margin: "0.00",
          gross_margin_percent: "0.0",
          margin_percent: null,
          revenue: "1000.00",
          cogs: "0.00",
          previous_period: {
            available: false,
            gross_margin_percent: null,
          },
        }}
        isLoading={false}
        error={null}
      />,
    );

    expect(screen.getByTestId("gross-margin-card-unavailable")).toBeTruthy();
  });

  it("renders revenue and cogs when previous-period trend is unavailable", () => {
    render(
      <GrossMarginCard
        data={{
          available: true,
          gross_margin: "400.00",
          gross_margin_percent: "40.0",
          margin_percent: "40.0",
          revenue: "1000.00",
          cogs: "600.00",
          previous_period: {
            available: false,
            gross_margin_percent: null,
          },
        }}
        isLoading={false}
        error={null}
      />,
    );

    expect(screen.getByTestId("gross-margin-card")).toBeTruthy();
    expect(screen.getByText("NT$ 1,000.00")).toBeTruthy();
    expect(screen.getByText("NT$ 600.00")).toBeTruthy();
  });

  it("renders an em dash when gross margin percent is null", () => {
    render(
      <GrossMarginCard
        data={{
          available: true,
          gross_margin: "0.00",
          gross_margin_percent: null,
          margin_percent: null,
          revenue: "0.00",
          cogs: "0.00",
          previous_period: {
            available: false,
            gross_margin_percent: null,
          },
        }}
        isLoading={false}
        error={null}
      />,
    );

    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});