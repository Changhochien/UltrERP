import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { QuotationListPage } from "../../pages/crm/QuotationListPage";
import { listQuotations } from "../../lib/api/crm";
import { CRM_QUOTATIONS_ROUTE } from "../../lib/routes";

vi.mock("../../lib/api/crm", () => ({
  getQuotation: vi.fn(),
  listLeads: vi.fn(),
  listQuotations: vi.fn(),
  QUOTATION_STATUS_OPTIONS: ["draft", "open", "replied", "partially_ordered", "ordered", "lost", "cancelled", "expired"],
  reviseQuotation: vi.fn(),
  transitionQuotationStatus: vi.fn(),
  updateQuotation: vi.fn(),
}));

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canAccess: () => true,
    canWrite: () => true,
  }),
}));

const mockedListQuotations = vi.mocked(listQuotations);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("QuotationListPage", () => {
  it("renders the quotation list returned by the API", async () => {
    mockedListQuotations.mockResolvedValue({
      items: [
        {
          id: "qtn-1",
          quotation_to: "lead",
          party_name: "lead-1",
          party_label: "Rotor Works",
          status: "open",
          transaction_date: "2026-04-21",
          valid_till: "2026-05-21",
          company: "UltrERP Taiwan",
          currency: "TWD",
          grand_total: "26250.00",
          opportunity_id: "opp-1",
          amended_from: null,
          revision_no: 0,
          updated_at: "2026-04-21T00:00:00Z",
        },
      ],
      page: 1,
      page_size: 50,
      total_count: 1,
      total_pages: 1,
    });

    render(
      <MemoryRouter initialEntries={[CRM_QUOTATIONS_ROUTE]}>
        <Routes>
          <Route path={CRM_QUOTATIONS_ROUTE} element={<QuotationListPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Quotations" })).toBeTruthy();
    expect(await screen.findByRole("button", { name: "Quotation Rotor Works" })).toBeTruthy();
    expect(screen.getByText("26250.00")).toBeTruthy();
  });

  it("shows API load failures instead of an empty state", async () => {
    mockedListQuotations.mockRejectedValueOnce(new Error("Forbidden"));

    render(
      <MemoryRouter initialEntries={[CRM_QUOTATIONS_ROUTE]}>
        <Routes>
          <Route path={CRM_QUOTATIONS_ROUTE} element={<QuotationListPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Forbidden")).toBeTruthy();
  });
});