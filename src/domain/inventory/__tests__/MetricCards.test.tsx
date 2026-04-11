import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { MetricCards } from "../components/MetricCards";

const mockUseProductSearch = vi.fn();
const mockUseReorderAlerts = vi.fn();

vi.mock("../hooks/useProductSearch", () => ({
  useProductSearch: () => mockUseProductSearch(),
}));

vi.mock("../hooks/useReorderAlerts", () => ({
  useReorderAlerts: (...args: unknown[]) => mockUseReorderAlerts(...args),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("MetricCards", () => {
  it("shows unavailable state instead of misleading zeroes when alert loading fails", () => {
    mockUseProductSearch.mockReturnValue({
      total: 10,
      loading: false,
      search: vi.fn(),
    });
    mockUseReorderAlerts.mockReturnValue({
      alerts: [],
      total: 0,
      loading: false,
      error: "Failed to fetch reorder alerts",
      reload: vi.fn(),
    });

    render(<MetricCards warehouseId="warehouse-1" />);

    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3);
    expect(screen.getAllByText("Alert data unavailable").length).toBeGreaterThanOrEqual(1);
  });
});