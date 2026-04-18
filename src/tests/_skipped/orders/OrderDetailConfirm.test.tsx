import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { OrderDetail } from "../../domain/orders/components/OrderDetail";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const ORDER_ID = "11111111-1111-1111-1111-111111111111";

function mockOrderFetch(overrides: Record<string, unknown> = {}) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({
      id: ORDER_ID,
      tenant_id: "00000000-0000-0000-0000-000000000001",
      customer_id: "22222222-2222-2222-2222-222222222222",
      order_number: "ORD-20260101-ABCD1234",
      status: "pending",
      payment_terms_code: "NET_30",
      payment_terms_days: 30,
      subtotal_amount: "1000.00",
      tax_amount: "50.00",
      total_amount: "1050.00",
      invoice_id: null,
      notes: null,
      created_by: "system",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      confirmed_at: null,
      lines: [
        {
          id: "33333333-3333-3333-3333-333333333333",
          product_id: "44444444-4444-4444-4444-444444444444",
          line_number: 1,
          description: "Widget A",
          quantity: "10",
          unit_price: "100.00",
          tax_policy_code: "standard",
          tax_type: 1,
          tax_rate: "0.0500",
          tax_amount: "50.00",
          subtotal_amount: "1000.00",
          total_amount: "1050.00",
          available_stock_snapshot: 100,
          backorder_note: null,
        },
      ],
      ...overrides,
    }),
  } as Response);
}

describe("OrderDetail — status actions", () => {
  const noop = () => {};

  it("shows Confirm Order and Cancel Order buttons for pending orders", async () => {
    mockOrderFetch();
    render(
      <MemoryRouter>
        <OrderDetail orderId={ORDER_ID} onBack={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Confirm Order")).toBeTruthy();
    });
    expect(screen.getByText("Cancel Order")).toBeTruthy();
  });

  it("shows Mark Shipped button for confirmed orders", async () => {
    mockOrderFetch({ status: "confirmed", confirmed_at: "2026-01-02T00:00:00Z" });
    render(
      <MemoryRouter>
        <OrderDetail orderId={ORDER_ID} onBack={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Mark Shipped")).toBeTruthy();
    });
    expect(screen.queryByText("Confirm Order")).toBeNull();
  });

  it("shows Mark Fulfilled button for shipped orders", async () => {
    mockOrderFetch({ status: "shipped" });
    render(
      <MemoryRouter>
        <OrderDetail orderId={ORDER_ID} onBack={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Mark Fulfilled")).toBeTruthy();
    });
  });

  it("shows no action buttons for fulfilled orders", async () => {
    mockOrderFetch({ status: "fulfilled" });
    render(
      <MemoryRouter>
        <OrderDetail orderId={ORDER_ID} onBack={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/Fulfilled/)).toBeTruthy();
    });
    expect(screen.queryByText("Confirm Order")).toBeNull();
    expect(screen.queryByText("Mark Shipped")).toBeNull();
    expect(screen.queryByText("Mark Fulfilled")).toBeNull();
    expect(screen.queryByText("Cancel Order")).toBeNull();
  });

  it("shows no action buttons for cancelled orders", async () => {
    mockOrderFetch({ status: "cancelled" });
    render(
      <MemoryRouter>
        <OrderDetail orderId={ORDER_ID} onBack={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/Cancelled/)).toBeTruthy();
    });
    expect(screen.queryByText("Confirm Order")).toBeNull();
    expect(screen.queryByText("Cancel Order")).toBeNull();
  });

  it("shows confirmation dialog when clicking Confirm Order", async () => {
    mockOrderFetch();
    render(
      <MemoryRouter>
        <OrderDetail orderId={ORDER_ID} onBack={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Confirm Order")).toBeTruthy();
    });
    fireEvent.click(screen.getByText("Confirm Order"));
    expect(screen.getByText(/auto-generate an invoice/)).toBeTruthy();
    expect(screen.getByText("Yes, Confirm Order")).toBeTruthy();
  });

  it("shows cancel confirmation dialog when clicking Cancel Order", async () => {
    mockOrderFetch();
    render(
      <MemoryRouter>
        <OrderDetail orderId={ORDER_ID} onBack={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Cancel Order")).toBeTruthy();
    });
    fireEvent.click(screen.getByText("Cancel Order"));
    expect(screen.getByText(/cancel this order/)).toBeTruthy();
    expect(screen.getByText("Yes, Cancel Order")).toBeTruthy();
  });

  it("renders the invoice link with transparent chrome and theme foreground text", async () => {
    mockOrderFetch({ invoice_id: "6b33136e-61fb-5213-8ff0-dd70d555dec3" });
    render(
      <MemoryRouter>
        <OrderDetail orderId={ORDER_ID} onBack={noop} />
      </MemoryRouter>,
    );

    const invoiceLink = await screen.findByRole("button", {
      name: "6b33136e-61fb-5213-8ff0-dd70d555dec3",
    });

    expect(invoiceLink.className).toContain("bg-transparent");
    expect(invoiceLink.className).toContain("text-foreground");
    expect(invoiceLink.className).not.toContain("text-info-token");
  });
});
