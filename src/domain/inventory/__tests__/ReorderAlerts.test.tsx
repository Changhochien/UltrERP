import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ReorderAlerts } from "../components/ReorderAlerts";

const mockUseReorderAlerts = vi.fn();
const mockUseAcknowledgeAlert = vi.fn();
const mockUseSnoozeAlert = vi.fn();
const mockUseDismissAlert = vi.fn();
const mockUseWarehouses = vi.fn();

vi.mock("../hooks/useReorderAlerts", () => ({
  useReorderAlerts: (...args: unknown[]) => mockUseReorderAlerts(...args),
  useAcknowledgeAlert: () => mockUseAcknowledgeAlert(),
  useSnoozeAlert: () => mockUseSnoozeAlert(),
  useDismissAlert: () => mockUseDismissAlert(),
}));

vi.mock("../hooks/useWarehouses", () => ({
  useWarehouses: () => mockUseWarehouses(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ReorderAlerts", () => {
  it("renders lifecycle statuses and dispatches snooze and dismiss actions", async () => {
    const reload = vi.fn();
    const acknowledge = vi.fn().mockResolvedValue(true);
    const snooze = vi.fn().mockResolvedValue(true);
    const dismiss = vi.fn().mockResolvedValue(true);

    mockUseReorderAlerts.mockReturnValue({
      alerts: [
        {
          id: "pending-alert",
          product_id: "product-1",
          product_name: "Pending Widget",
          warehouse_id: "warehouse-1",
          warehouse_name: "Main",
          current_stock: 4,
          reorder_point: 20,
          status: "pending",
          severity: "WARNING",
          created_at: "2026-06-01T00:00:00Z",
          acknowledged_at: null,
          acknowledged_by: null,
          snoozed_until: null,
          snoozed_by: null,
          dismissed_at: null,
          dismissed_by: null,
        },
        {
          id: "snoozed-alert",
          product_id: "product-2",
          product_name: "Snoozed Widget",
          warehouse_id: "warehouse-1",
          warehouse_name: "Main",
          current_stock: 2,
          reorder_point: 10,
          status: "snoozed",
          severity: "CRITICAL",
          created_at: "2026-06-01T00:00:00Z",
          acknowledged_at: null,
          acknowledged_by: null,
          snoozed_until: "2026-06-01T01:00:00Z",
          snoozed_by: "system",
          dismissed_at: null,
          dismissed_by: null,
        },
        {
          id: "resolved-alert",
          product_id: "product-3",
          product_name: "Resolved Widget",
          warehouse_id: "warehouse-1",
          warehouse_name: "Main",
          current_stock: 30,
          reorder_point: 10,
          status: "resolved",
          severity: "INFO",
          created_at: "2026-06-01T00:00:00Z",
          acknowledged_at: null,
          acknowledged_by: null,
          snoozed_until: null,
          snoozed_by: null,
          dismissed_at: null,
          dismissed_by: null,
        },
      ],
      total: 3,
      loading: false,
      error: null,
      reload,
    });
    mockUseWarehouses.mockReturnValue({ warehouses: [], loading: false });
    mockUseAcknowledgeAlert.mockReturnValue({ acknowledge, submitting: false, error: null });
    mockUseSnoozeAlert.mockReturnValue({ snooze, submitting: false, error: null });
    mockUseDismissAlert.mockReturnValue({ dismiss, submitting: false, error: null });

    render(<ReorderAlerts />);

    expect(screen.getByRole("option", { name: "Snoozed" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Dismissed" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Snooze alert for Pending Widget" }));
    fireEvent.click(screen.getByRole("button", { name: "Dismiss alert for Snoozed Widget" }));

    await waitFor(() => {
      expect(snooze).toHaveBeenCalledWith("pending-alert", 60);
      expect(dismiss).toHaveBeenCalledWith("snoozed-alert");
    });

    expect(screen.queryByRole("button", { name: "Dismiss alert for Resolved Widget" })).toBeNull();
  });
});