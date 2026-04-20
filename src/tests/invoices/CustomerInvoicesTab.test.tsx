import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { CustomerInvoicesTab } from "../../components/customers/CustomerInvoicesTab";

const translationMock = vi.hoisted(() => ({
  t: (key: string) => key,
}));
const navigateMock = vi.fn();
const fetchInvoicesMock = vi.fn();

vi.mock("react-i18next", () => ({
  useTranslation: () => translationMock,
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../../lib/api/invoices", () => ({
  fetchInvoices: (...args: unknown[]) => fetchInvoicesMock(...args),
}));

afterEach(() => {
  navigateMock.mockReset();
  fetchInvoicesMock.mockReset();
  vi.clearAllMocks();
});

describe("CustomerInvoicesTab", () => {
  it("sorts customer invoices by invoice date when the header is clicked", async () => {
    fetchInvoicesMock.mockResolvedValue({
      items: [
        {
          id: "invoice-2",
          invoice_number: "AA00000002",
          invoice_date: "2026-04-10",
          total_amount: "200.00",
          currency_code: "TWD",
          payment_status: "partial",
        },
        {
          id: "invoice-1",
          invoice_number: "AA00000001",
          invoice_date: "2026-04-01",
          total_amount: "100.00",
          currency_code: "TWD",
          payment_status: "unpaid",
        },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    });

    render(
      <MemoryRouter>
        <CustomerInvoicesTab customerId="cust-123" />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getAllByText(/2026-04-/).map((node) => node.textContent)).toEqual([
        "2026-04-10",
        "2026-04-01",
      ]);
    });

    fireEvent.click(screen.getByRole("button", { name: "invoice.listPage.invoiceDate" }));

    await waitFor(() => {
      expect(screen.getAllByText(/2026-04-/).map((node) => node.textContent)).toEqual([
        "2026-04-01",
        "2026-04-10",
      ]);
    });
  });
});