import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { AlertFeed } from "../components/AlertFeed";

const mockUseReorderAlerts = vi.fn();
const mockUseAcknowledgeAlert = vi.fn();

vi.mock("../hooks/useReorderAlerts", () => ({
  useReorderAlerts: (...args: unknown[]) => mockUseReorderAlerts(...args),
  useAcknowledgeAlert: () => mockUseAcknowledgeAlert(),
}));

vi.mock("../context/WarehouseContext", () => ({
  useWarehouseContext: () => ({ selectedWarehouse: null }),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AlertFeed", () => {
  it("keeps quarter-boundary warnings out of the critical filter", () => {
    mockUseReorderAlerts.mockReturnValue({
      alerts: [
        {
          id: "critical-alert",
          product_id: "product-1",
          product_name: "Critical Widget",
          warehouse_id: "warehouse-1",
          warehouse_name: "Main",
          current_stock: 0,
          reorder_point: 20,
          status: "pending",
          severity: "CRITICAL",
          created_at: "2026-06-01T00:00:00Z",
          acknowledged_at: null,
          acknowledged_by: null,
        },
        {
          id: "warning-alert",
          product_id: "product-2",
          product_name: "Quarter Boundary Widget",
          warehouse_id: "warehouse-1",
          warehouse_name: "Main",
          current_stock: 5,
          reorder_point: 20,
          status: "pending",
          severity: "WARNING",
          created_at: "2026-06-01T00:00:00Z",
          acknowledged_at: null,
          acknowledged_by: null,
        },
      ],
      loading: false,
      reload: vi.fn(),
    });
    mockUseAcknowledgeAlert.mockReturnValue({ acknowledge: vi.fn(), submitting: false });

    render(<AlertFeed />);

    expect(screen.getByText("Critical Widget")).toBeTruthy();
    expect(screen.getByText("Quarter Boundary Widget")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Critical" }));

    expect(screen.getByText("Critical Widget")).toBeTruthy();
    expect(screen.queryByText("Quarter Boundary Widget")).toBeNull();
  });
});