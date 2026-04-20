import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { OrderDetail } from "../../domain/orders/components/OrderDetail";

const navigateMock = vi.fn();
const reloadMock = vi.fn();
const updateOrderStatusMock = vi.fn();

let mockOrder = {
  id: "order-123",
  tenant_id: "tenant-1",
  customer_id: "customer-1",
  customer_name: "Test Corp",
  order_number: "ORD-20260401-ABCD1234",
  status: "pending",
  payment_terms_code: "NET_30",
  payment_terms_days: 30,
  subtotal_amount: "1000.00",
  discount_amount: "0.00",
  discount_percent: "0.00",
  tax_amount: "50.00",
  total_amount: "1050.00",
  invoice_id: null,
  invoice_number: null,
  invoice_payment_status: null,
  notes: null,
  created_by: "system",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  confirmed_at: null,
  execution: {
    commercial_status: "pre_commit",
    fulfillment_status: "not_started",
    billing_status: "not_invoiced",
    reservation_status: "not_reserved",
    ready_to_ship: false,
    has_backorder: false,
    backorder_line_count: 0,
  },
  lines: [
    {
      id: "line-1",
      product_id: "product-1",
      line_number: 1,
      quantity: "10",
      list_unit_price: "100.00",
      unit_price: "100.00",
      discount_amount: "0.00",
      tax_policy_code: "standard",
      tax_type: 1,
      tax_rate: "0.0500",
      tax_amount: "50.00",
      subtotal_amount: "1000.00",
      total_amount: "1050.00",
      description: "Widget A",
      available_stock_snapshot: 100,
      backorder_note: null,
    },
  ],
};

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../../domain/orders/hooks/useOrders", () => ({
  useOrderDetail: () => ({
    order: mockOrder,
    loading: false,
    error: null,
    reload: reloadMock,
  }),
  statusBadgeVariant: () => "neutral",
  statusLabel: (status: string) => status,
}));

vi.mock("../../lib/api/orders", () => ({
  updateOrderStatus: (...args: unknown[]) => updateOrderStatusMock(...args),
}));

beforeEach(() => {
  navigateMock.mockReset();
  reloadMock.mockReset();
  updateOrderStatusMock.mockReset();
  reloadMock.mockResolvedValue(undefined);
  mockOrder = {
    ...mockOrder,
    status: "pending",
    invoice_id: null,
    invoice_number: null,
    invoice_payment_status: null,
    confirmed_at: null,
    execution: {
      commercial_status: "pre_commit",
      fulfillment_status: "not_started",
      billing_status: "not_invoiced",
      reservation_status: "not_reserved",
      ready_to_ship: false,
      has_backorder: false,
      backorder_line_count: 0,
    },
  };
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("OrderDetail confirmation UX", () => {
  it("uses explicit invoice and stock reservation confirmation copy", () => {
    render(
      <MemoryRouter>
        <OrderDetail orderId="order-123" onBack={() => undefined} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("button", { name: /create invoice/i })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /create invoice/i }));

    expect(screen.getByText(/creates the invoice/i)).toBeTruthy();
    expect(screen.getByText(/reserves stock/i)).toBeTruthy();
  });

  it("shows success feedback and invoice continuity after confirmation", async () => {
    updateOrderStatusMock.mockResolvedValue({
      ok: true,
      data: {
        ...mockOrder,
        status: "confirmed",
        invoice_id: "invoice-123",
        invoice_number: "AA00000001",
        invoice_payment_status: "unpaid",
        confirmed_at: "2026-01-02T00:00:00Z",
        execution: {
          commercial_status: "committed",
          fulfillment_status: "ready_to_ship",
          billing_status: "unpaid",
          reservation_status: "reserved",
          ready_to_ship: true,
          has_backorder: false,
          backorder_line_count: 0,
        },
      },
    });

    render(
      <MemoryRouter>
        <OrderDetail orderId="order-123" onBack={() => undefined} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: /create invoice/i }));
    fireEvent.click(screen.getByRole("button", { name: /yes/i }));

    await waitFor(() => {
      expect(reloadMock).toHaveBeenCalled();
    });
    expect(screen.getByText(/Invoice AA00000001 was created/i)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /view AA00000001/i }));
    expect(navigateMock).toHaveBeenCalledWith("/invoices/invoice-123");
  });

  it("shows actionable retryable errors when confirmation fails", async () => {
    updateOrderStatusMock.mockResolvedValue({
      ok: false,
      error: "Insufficient stock to reserve requested quantity.",
    });

    render(
      <MemoryRouter>
        <OrderDetail orderId="order-123" onBack={() => undefined} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: /create invoice/i }));
    fireEvent.click(screen.getByRole("button", { name: /yes/i }));

    await waitFor(() => {
      expect(screen.getByText(/stock reservation failed/i)).toBeTruthy();
    });
    expect(screen.getByText(/adjust quantities or replenish stock/i)).toBeTruthy();
    expect(screen.getByText(/confirm status change/i)).toBeTruthy();
  });
});