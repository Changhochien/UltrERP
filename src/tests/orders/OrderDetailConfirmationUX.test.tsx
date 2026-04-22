import "../helpers/i18n";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { OrderDetail } from "../../domain/orders/components/OrderDetail";
import { ToastProvider } from "../../providers/ToastProvider";
import type { OrderResponse } from "../../domain/orders/types";

const navigateMock = vi.fn();
const reloadMock = vi.fn();
const updateOrderStatusMock = vi.fn();
const permissionMock = vi.hoisted(() => ({
  canWrite: vi.fn<(feature: string) => boolean>(),
}));

let mockOrder: OrderResponse = {
  id: "order-123",
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
  sales_team: [],
  total_commission: "0.00",
  invoice_id: null as string | null,
  invoice_number: null as string | null,
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
  utm_source: "",
  utm_medium: "",
  utm_campaign: "",
  utm_content: "",
  utm_attribution_origin: null,
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

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canWrite: permissionMock.canWrite,
  }),
}));

beforeEach(() => {
  navigateMock.mockReset();
  reloadMock.mockReset();
  updateOrderStatusMock.mockReset();
  permissionMock.canWrite.mockReset();
  permissionMock.canWrite.mockImplementation((feature) => feature === "orders");
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
  it("keeps commercial, warehouse, and billing actions visually grouped", () => {
    render(
      <ToastProvider>
        <MemoryRouter>
          <OrderDetail orderId="order-123" onBack={() => undefined} />
        </MemoryRouter>
      </ToastProvider>,
    );

    expect(screen.getByText("Grouped actions")).toBeTruthy();
    expect(screen.getByText("Commercial actions")).toBeTruthy();
    expect(screen.getByText("Warehouse actions")).toBeTruthy();
    expect(screen.getByText("Billing navigation")).toBeTruthy();
    expect(screen.getByText("The invoice will appear here after the order is confirmed.")).toBeTruthy();
  });

  it("uses explicit invoice and stock reservation confirmation copy", () => {
    render(
      <ToastProvider>
        <MemoryRouter>
          <OrderDetail orderId="order-123" onBack={() => undefined} />
        </MemoryRouter>
      </ToastProvider>,
    );

    expect(screen.getByRole("button", { name: /create invoice/i })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /create invoice/i }));

    expect(screen.getByText(/create the invoice/i)).toBeTruthy();
    expect(screen.getByText(/reserve stock/i)).toBeTruthy();
  });

  it("surfaces warehouse exceptions where shipping decisions are made", () => {
    mockOrder = {
      ...mockOrder,
      status: "confirmed",
      invoice_id: "invoice-123",
      invoice_number: "AA00000001",
      invoice_payment_status: "unpaid",
      confirmed_at: "2026-01-02T00:00:00Z",
      execution: {
        commercial_status: "committed",
        fulfillment_status: "not_started",
        billing_status: "unpaid",
        reservation_status: "not_reserved",
        ready_to_ship: false,
        has_backorder: true,
        backorder_line_count: 2,
      },
    };

    render(
      <ToastProvider>
        <MemoryRouter>
          <OrderDetail orderId="order-123" onBack={() => undefined} />
        </MemoryRouter>
      </ToastProvider>,
    );

    expect(screen.getByText("Backorder risk remains on 2 lines. Rebalance stock before shipping.")).toBeTruthy();
    expect(screen.getByText("Inventory reservation is incomplete. Recheck stock before shipping.")).toBeTruthy();
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
      <ToastProvider>
        <MemoryRouter>
          <OrderDetail orderId="order-123" onBack={() => undefined} />
        </MemoryRouter>
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /create invoice/i }));
    fireEvent.click(screen.getByRole("button", { name: /yes/i }));

    await waitFor(() => {
      expect(reloadMock).toHaveBeenCalled();
    });
    expect(screen.getByText("Invoice AA00000001 was created.")).toBeTruthy();
    expect(screen.getByText("Order confirmed")).toBeTruthy();
    expect(screen.getByText("Invoice AA00000001 was created and stock was reserved.")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /view AA00000001/i }));
    expect(navigateMock).toHaveBeenCalledWith("/invoices/invoice-123");
  });

  it("shows actionable retryable errors when confirmation fails", async () => {
    updateOrderStatusMock.mockResolvedValue({
      ok: false,
      error: "Insufficient stock to reserve requested quantity.",
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <OrderDetail orderId="order-123" onBack={() => undefined} />
        </MemoryRouter>
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /create invoice/i }));
    fireEvent.click(screen.getByRole("button", { name: /yes/i }));

    await waitFor(() => {
      expect(screen.getByText(/stock reservation failed/i)).toBeTruthy();
    });
    expect(screen.getByText("Order update failed")).toBeTruthy();
    expect(screen.getByText(/adjust quantities or replenish stock/i)).toBeTruthy();
    expect(screen.getByText(/confirm status change/i)).toBeTruthy();
  });

  it("shows persisted CRM attribution and override origin", () => {
    mockOrder = {
      ...mockOrder,
      source_quotation_id: "quotation-123",
      crm_context_snapshot: { party_label: "Rotor Works" },
      utm_source: "partner",
      utm_medium: "referral",
      utm_campaign: "channel-push",
      utm_content: "landing-page-b",
      utm_attribution_origin: "manual_override",
    };

    render(
      <ToastProvider>
        <MemoryRouter>
          <OrderDetail orderId="order-123" onBack={() => undefined} />
        </MemoryRouter>
      </ToastProvider>,
    );

    expect(screen.getByText("Attribution")).toBeTruthy();
    expect(screen.getByText("Manual override")).toBeTruthy();
    expect(screen.getByText("partner")).toBeTruthy();
    expect(screen.getByText("referral")).toBeTruthy();
    expect(screen.getByText("channel-push")).toBeTruthy();
    expect(screen.getByText("landing-page-b")).toBeTruthy();
  });

  it("hides workflow mutation actions for read-only order roles", () => {
    permissionMock.canWrite.mockReturnValue(false);
    mockOrder = {
      ...mockOrder,
      status: "confirmed",
      invoice_id: "invoice-123",
      invoice_number: "AA00000001",
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
    };

    render(
      <ToastProvider>
        <MemoryRouter>
          <OrderDetail orderId="order-123" onBack={() => undefined} />
        </MemoryRouter>
      </ToastProvider>,
    );

    expect(screen.queryByRole("button", { name: /ship order/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /create invoice/i })).toBeNull();
    expect(screen.getAllByText("This order is read-only for your role. Sales and admin users can change its workflow state.").length).toBe(2);
    expect(screen.getByRole("button", { name: /view AA00000001/i })).toBeTruthy();
  });
});