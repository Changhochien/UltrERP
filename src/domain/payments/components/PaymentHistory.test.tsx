import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import PaymentHistory from "./PaymentHistory";

const usePaymentsMock = vi.hoisted(() => vi.fn());

vi.mock("../hooks/usePayments", () => ({
  usePayments: (...args: Parameters<typeof usePaymentsMock>) => usePaymentsMock(...args),
}));

vi.mock("../../../components/layout/DataTable", () => ({
  DataTable: ({ data }: { data: Array<{ id: string; payment_ref: string }> }) => (
    <div data-testid="payment-history-table">
      {data.map((payment) => (
        <div key={payment.id}>{payment.payment_ref}</div>
      ))}
    </div>
  ),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("PaymentHistory", () => {
  it("shows a loading state", () => {
    usePaymentsMock.mockReturnValue({ items: [], loading: true, error: null });

    render(<PaymentHistory invoiceId="inv-1" />);

    expect(screen.getByText(/Loading payments/)).toBeTruthy();
  });

  it("shows an empty state when no payments are recorded", () => {
    usePaymentsMock.mockReturnValue({ items: [], loading: false, error: null });

    render(<PaymentHistory invoiceId="inv-1" />);

    expect(screen.getByText("No payments recorded.")).toBeTruthy();
  });

  it("renders the payment history table when items exist", () => {
    usePaymentsMock.mockReturnValue({
      items: [
        {
          id: "payment-1",
          payment_ref: "PAY-001",
          amount: "100.00",
          payment_method: "cash",
          payment_date: "2026-04-10",
          created_by: "alice",
        },
      ],
      loading: false,
      error: null,
    });

    render(<PaymentHistory invoiceId="inv-1" />);

    expect(screen.getByTestId("payment-history")).toBeTruthy();
    expect(screen.getByText("Payment History")).toBeTruthy();
    expect(screen.getByText("PAY-001")).toBeTruthy();
  });
});