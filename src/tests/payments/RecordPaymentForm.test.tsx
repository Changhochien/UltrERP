import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import RecordPaymentForm from "../../domain/payments/components/RecordPaymentForm";
import { setAppTimeGetter } from "../../lib/time";

const mutateMock = vi.fn();
const successToastMock = vi.fn();
const errorToastMock = vi.fn();

vi.mock("../../domain/payments/hooks/usePayments", () => ({
  useCreatePayment: () => ({
    mutate: mutateMock,
    isLoading: false,
    error: null,
  }),
}));

vi.mock("../../hooks/useToast", () => ({
  useToast: () => ({
    success: successToastMock,
    error: errorToastMock,
  }),
}));

async function clickCalendarDay(labelFragment: string) {
  const fallbackDay = labelFragment.match(/(\d{1,2})(?!.*\d)/)?.[1];
  const dialog = await screen.findByRole("dialog");
  let dayButton: HTMLElement | undefined;

  await waitFor(() => {
    dayButton = within(dialog).getAllByRole("button").find((button) =>
      button.getAttribute("aria-label")?.includes(labelFragment) ||
      (fallbackDay !== undefined && button.textContent?.trim() === fallbackDay),
    );

    if (!dayButton) {
      throw new Error(`Could not find calendar day button containing "${labelFragment}".`);
    }
  });

  if (!dayButton) {
    throw new Error(`Could not find calendar day button containing "${labelFragment}".`);
  }

  fireEvent.click(dayButton);
}

describe("RecordPaymentForm", () => {
  beforeEach(() => {
    setAppTimeGetter(() => new Date("2026-04-01T00:00:00Z"));
    mutateMock.mockResolvedValue({
      ok: true,
      data: { payment_ref: "PAY-001" },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    setAppTimeGetter(() => new Date());
  });

  it("submits the selected payment date as an ISO calendar string without a native date input", async () => {
    const onSuccess = vi.fn();
    const onCancel = vi.fn();
    const { container } = render(
      <RecordPaymentForm
        invoiceId="invoice-1"
        outstandingBalance={125.5}
        onSuccess={onSuccess}
        onCancel={onCancel}
      />,
    );

    expect(container.querySelector('input[type="date"]')).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Payment Date" }));
    await clickCalendarDay("April 15");
    fireEvent.click(screen.getByRole("button", { name: "Record Payment" }));

    await waitFor(() => {
      expect(mutateMock).toHaveBeenCalledWith(
        expect.objectContaining({ payment_date: "2026-04-15" }),
      );
    });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("uses the Taiwan calendar date for the default payment date near a UTC boundary", async () => {
    setAppTimeGetter(() => new Date("2026-03-31T16:30:00Z"));

    render(
      <RecordPaymentForm
        invoiceId="invoice-1"
        outstandingBalance={125.5}
        onSuccess={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Payment Date" }).textContent).toContain(
      "Apr 1, 2026",
    );

    fireEvent.click(screen.getByRole("button", { name: "Record Payment" }));

    await waitFor(() => {
      expect(mutateMock).toHaveBeenCalledWith(
        expect.objectContaining({ payment_date: "2026-04-01" }),
      );
    });
  });
});