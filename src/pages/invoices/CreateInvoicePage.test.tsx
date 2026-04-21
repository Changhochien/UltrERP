import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CreateInvoicePage from "./CreateInvoicePage";
import { listCustomers } from "../../lib/api/customers";
import { setAppTimeGetter } from "../../lib/time";

const successToastMock = vi.fn();
const errorToastMock = vi.fn();

vi.mock("../../components/customers/CustomerCombobox", () => ({
  CustomerCombobox: () => <div data-testid="customer-combobox" />,
}));

vi.mock("../../components/invoices/InvoiceLineEditor", () => ({
  InvoiceLineEditor: () => <div data-testid="invoice-line-editor" />,
}));

vi.mock("../../components/invoices/InvoiceTotalsCard", () => ({
  InvoiceTotalsCard: () => <div data-testid="invoice-totals-card" />,
}));

vi.mock("../../hooks/useToast", () => ({
  useToast: () => ({
    success: successToastMock,
    error: errorToastMock,
  }),
}));

vi.mock("../../lib/api/customers", () => ({
  listCustomers: vi.fn(),
}));

vi.mock("../../lib/api/invoices", () => ({
  createInvoice: vi.fn(),
}));

describe("CreateInvoicePage", () => {
  beforeEach(() => {
    setAppTimeGetter(() => new Date("2026-03-31T16:30:00Z"));
    vi.mocked(listCustomers).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 200,
      total_count: 0,
      total_pages: 1,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    setAppTimeGetter(() => new Date());
  });

  it("uses the Taiwan calendar date for the default invoice date", () => {
    const { container } = render(
      <MemoryRouter>
        <CreateInvoicePage />
      </MemoryRouter>,
    );

    expect(container.querySelector("#invoice-date")?.textContent).toContain("Apr 1, 2026");
    expect(screen.queryByText("Mar 31, 2026")).toBeNull();
  });
});