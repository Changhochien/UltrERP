import { act, cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

const dataTableMock = vi.hoisted(() => ({
  lastOnSortChange: undefined as ((next: { columnId: string; direction: "asc" | "desc" } | null) => void) | undefined,
}));

vi.mock("../../../components/layout/DataTable", async () => {
  const actual = await vi.importActual<typeof import("../../../components/layout/DataTable")>("../../../components/layout/DataTable");
  return {
    ...actual,
    DataTable: ({ onSortChange }: { onSortChange?: (next: { columnId: string; direction: "asc" | "desc" } | null) => void }) => {
      dataTableMock.lastOnSortChange = onSortChange;
      return <div>Mock DataTable</div>;
    },
  };
});

const invoiceListResponse = {
  items: [
    {
      id: "inv-1",
      invoice_number: "AA00000001",
      invoice_date: "2026-04-01",
      customer_id: "cust-1",
      currency_code: "TWD",
      total_amount: "1000.00",
      status: "issued",
      created_at: "2026-04-01T00:00:00Z",
      amount_paid: "300.00",
      outstanding_balance: "700.00",
      payment_status: "partial",
      due_date: "2026-05-01",
      days_overdue: 0,
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  dataTableMock.lastOnSortChange = undefined;
});

describe("InvoiceList TanStack compatibility", () => {
  it("requests a new invoice sort when the table emits a sort state", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => invoiceListResponse,
    } as Response);

    const { InvoiceList } = await import("../components/InvoiceList");

    render(
      <MemoryRouter initialEntries={["/invoices"]}>
        <InvoiceList onSelect={() => undefined} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(dataTableMock.lastOnSortChange).toBeTruthy();
    });

    await act(async () => {
      dataTableMock.lastOnSortChange?.({
        columnId: "outstanding_balance",
        direction: "asc",
      });
    });

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(2);
    });

    const secondRequest = String(fetchSpy.mock.calls[1]?.[0]);
    expect(secondRequest).toContain("sort_by=outstanding_balance");
    expect(secondRequest).toContain("sort_order=asc");
  });

  it("clears invoice sort params when a TanStack-style off state is requested", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => invoiceListResponse,
    } as Response);

    const { InvoiceList } = await import("../components/InvoiceList");

    render(
      <MemoryRouter initialEntries={["/invoices?sort_by=invoice_date&sort_order=desc"]}>
        <InvoiceList onSelect={() => undefined} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(dataTableMock.lastOnSortChange).toBeTruthy();
    });

    await act(async () => {
      dataTableMock.lastOnSortChange?.(null);
    });

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(2);
    });

    const secondRequest = String(fetchSpy.mock.calls[1]?.[0]);
    expect(secondRequest).not.toContain("sort_by=");
    expect(secondRequest).not.toContain("sort_order=");
  });
});