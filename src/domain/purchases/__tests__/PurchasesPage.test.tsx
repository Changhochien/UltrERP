import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { PurchasesPage } from "../../../pages/PurchasesPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      if (options && "invoiceNumber" in options) {
        return `${key}:${String(options.invoiceNumber)}`;
      }
      return key;
    },
  }),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const listResponse = {
  items: [
    {
      id: "sup-inv-1",
      supplier_id: "sup-1",
      supplier_name: "Acme Supply",
      invoice_number: "PI-2025001",
      invoice_date: "2025-03-15",
      currency_code: "TWD",
      total_amount: "105.00",
      status: "open",
      created_at: "2025-03-15T00:00:00Z",
      updated_at: "2025-03-15T00:00:00Z",
      line_count: 1,
    },
  ],
  status_totals: { open: 1, paid: 0, voided: 0 },
  total: 1,
  page: 1,
  page_size: 20,
};

const detailResponse = {
  id: "sup-inv-1",
  supplier_id: "sup-1",
  supplier_name: "Acme Supply",
  invoice_number: "PI-2025001",
  invoice_date: "2025-03-15",
  currency_code: "TWD",
  subtotal_amount: "100.00",
  tax_amount: "5.00",
  total_amount: "105.00",
  status: "open",
  notes: "Imported from legacy purchase history",
  created_at: "2025-03-15T00:00:00Z",
  updated_at: "2025-03-15T00:00:00Z",
  lines: [
    {
      id: "line-1",
      line_number: 1,
      product_id: "prod-1",
      product_code_snapshot: "P-100",
      product_name: "Widget Pro",
      description: "Widget",
      quantity: "2.000",
      unit_price: "50.00",
      subtotal_amount: "100.00",
      tax_type: 1,
      tax_rate: "0.0500",
      tax_amount: "5.00",
      total_amount: "105.00",
      created_at: "2025-03-15T00:00:00Z",
    },
  ],
};

describe("PurchasesPage", () => {
  it("renders the supplier invoice list and opens detail on row click", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/api/v1/purchases/supplier-invoices/sup-inv-1")) {
        return {
          ok: true,
          json: async () => detailResponse,
        } as Response;
      }
      if (url.includes("/api/v1/purchases/supplier-invoices")) {
        return {
          ok: true,
          json: async () => listResponse,
        } as Response;
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    render(<PurchasesPage />);

    await waitFor(() => {
      expect(screen.getByText("PI-2025001")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("PI-2025001"));

    await waitFor(() => {
      expect(screen.getByText("Acme Supply")).toBeTruthy();
    });
    expect(screen.getByText("Widget Pro")).toBeTruthy();
    expect(screen.getByText("Imported from legacy purchase history")).toBeTruthy();
  });

  it("shows an error when the supplier invoice list fails to load", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));

    render(<PurchasesPage />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeTruthy();
    });
  });
});