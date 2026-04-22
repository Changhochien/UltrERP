import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import RecordUnmatchedPayment from "../../domain/payments/components/RecordUnmatchedPayment";
import { listCustomers } from "../../lib/api/customers";
import { createUnmatchedPayment } from "../../lib/api/payments";
import { setAppTimeGetter } from "../../lib/time";

const successToastMock = vi.fn();
const errorToastMock = vi.fn();

vi.mock("../../lib/api/customers", () => ({
  listCustomers: vi.fn(),
}));

vi.mock("../../lib/api/payments", () => ({
  createUnmatchedPayment: vi.fn(),
}));

vi.mock("../../hooks/useToast", () => ({
  useToast: () => ({
    success: successToastMock,
    error: errorToastMock,
  }),
}));

describe("RecordUnmatchedPayment", () => {
  beforeEach(() => {
    setAppTimeGetter(() => new Date("2026-03-31T16:30:00Z"));
    vi.mocked(listCustomers).mockResolvedValue({
      items: [
        {
          id: "cust-1",
          company_name: "Acme Trading",
          normalized_business_number: "12345678",
          contact_phone: "0912-345-678",
          status: "active",
        },
      ],
      page: 1,
      page_size: 200,
      total_count: 1,
      total_pages: 1,
    });
    vi.mocked(createUnmatchedPayment).mockResolvedValue({
      ok: true,
      data: {
        id: "pay-1",
        invoice_id: null,
        customer_id: "cust-1",
        payment_ref: "PAY-001",
        amount: "100.00",
        payment_method: "BANK_TRANSFER",
        payment_date: "2026-03-31",
        reference_number: null,
        notes: null,
        created_by: "system",
        created_at: "2026-03-31T00:00:00Z",
        updated_at: "2026-03-31T00:00:00Z",
        match_status: "unmatched",
        match_type: null,
        matched_at: null,
        suggested_invoice_id: null,
      },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    setAppTimeGetter(() => new Date());
  });

  it("submits the Taiwan calendar date as the default unmatched payment date", async () => {
    const onSuccess = vi.fn();
    const { container } = render(
      <RecordUnmatchedPayment onSuccess={onSuccess} onCancel={vi.fn()} />,
    );

    expect(container.querySelector("#unmatched-date")?.textContent).toContain(
      "Apr 1, 2026",
    );

    await waitFor(() => {
      expect(
        (container.querySelector("#customer-id") as HTMLSelectElement | null)?.options.length,
      ).toBeGreaterThan(1);
    });

    fireEvent.change(container.querySelector("#customer-id") as HTMLSelectElement, {
      target: { value: "cust-1" },
    });
    fireEvent.change(container.querySelector("#unmatched-amount") as HTMLInputElement, {
      target: { value: "125.50" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Record Payment" }));

    await waitFor(() => {
      expect(createUnmatchedPayment).toHaveBeenCalledWith(
        expect.objectContaining({ payment_date: "2026-04-01" }),
      );
    });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});