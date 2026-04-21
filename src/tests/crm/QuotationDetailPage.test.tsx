import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import QuotationDetailPage from "../../pages/crm/QuotationDetailPage";
import {
  getQuotation,
  listLeads,
  QUOTATION_STATUS_OPTIONS,
  reviseQuotation,
  transitionQuotationStatus,
  updateQuotation,
} from "../../lib/api/crm";
import { listCustomers } from "../../lib/api/customers";
import { buildQuotationDetailPath, CRM_QUOTATION_DETAIL_ROUTE } from "../../lib/routes";

vi.mock("../../lib/api/crm", () => ({
  getQuotation: vi.fn(),
  listLeads: vi.fn(),
  QUOTATION_STATUS_OPTIONS: ["draft", "open", "replied", "partially_ordered", "ordered", "lost", "cancelled", "expired"],
  reviseQuotation: vi.fn(),
  transitionQuotationStatus: vi.fn(),
  updateQuotation: vi.fn(),
}));

vi.mock("../../lib/api/customers", () => ({
  listCustomers: vi.fn(),
}));

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canAccess: () => true,
    canWrite: () => true,
  }),
}));

vi.mock("../../hooks/useToast", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const mockedGetQuotation = vi.mocked(getQuotation);
const mockedListLeads = vi.mocked(listLeads);
const mockedListCustomers = vi.mocked(listCustomers);
const mockedUpdateQuotation = vi.mocked(updateQuotation);
const mockedTransitionQuotationStatus = vi.mocked(transitionQuotationStatus);
const mockedReviseQuotation = vi.mocked(reviseQuotation);

const sampleQuotation = {
  id: "qtn-1",
  tenant_id: "tenant-1",
  quotation_to: "lead" as const,
  party_name: "lead-1",
  party_label: "Rotor Works",
  status: "open" as const,
  transaction_date: "2026-04-21",
  valid_till: "2026-05-21",
  company: "UltrERP Taiwan",
  currency: "TWD",
  subtotal: "25000.00",
  total_taxes: "1250.00",
  grand_total: "26250.00",
  base_grand_total: "26250.00",
  ordered_amount: "0.00",
  order_count: 0,
  contact_person: "Amy Chen",
  contact_email: "amy@rotor.example",
  contact_mobile: "0912-000-111",
  job_title: "Procurement Manager",
  territory: "North",
  customer_group: "Industrial",
  billing_address: "No. 1, Zhongshan Rd, Taipei",
  shipping_address: "Warehouse 7, Taoyuan",
  utm_source: "expo",
  utm_medium: "field",
  utm_campaign: "spring-2026",
  utm_content: "booth-a3",
  items: [
    {
      line_no: 1,
      item_name: "Rotor Assembly",
      item_code: "",
      description: "24V industrial rotor",
      quantity: "2.00",
      unit_price: "12500.00",
      amount: "25000.00",
    },
  ],
  taxes: [
    {
      line_no: 1,
      description: "VAT",
      rate: "5.00",
      tax_amount: "1250.00",
    },
  ],
  terms_template: "standard-sales",
  terms_and_conditions: "Net 30 days.",
  opportunity_id: "opp-1",
  amended_from: null,
  revision_no: 0,
  lost_reason: "",
  competitor_name: "",
  loss_notes: "",
  auto_repeat_enabled: true,
  auto_repeat_frequency: "monthly",
  auto_repeat_until: "2026-12-31",
  notes: "Initial commercial offer.",
  version: 1,
  created_at: "2026-04-21T00:00:00Z",
  updated_at: "2026-04-21T00:00:00Z",
};

function renderQuotationDetail() {
  return render(
    <MemoryRouter initialEntries={[buildQuotationDetailPath("qtn-1")]}>
      <Routes>
        <Route path={CRM_QUOTATION_DETAIL_ROUTE} element={<QuotationDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  mockedGetQuotation.mockResolvedValue(sampleQuotation);
  mockedListLeads.mockResolvedValue({ items: [], page: 1, page_size: 100, total_count: 0, total_pages: 1 });
  mockedListCustomers.mockResolvedValue({ items: [], page: 1, page_size: 100, total_count: 0, total_pages: 1 });
  mockedUpdateQuotation.mockResolvedValue({ ok: true, data: sampleQuotation });
  mockedTransitionQuotationStatus.mockResolvedValue({ ok: true, data: sampleQuotation });
  mockedReviseQuotation.mockResolvedValue({ ok: true, data: { ...sampleQuotation, id: "qtn-2", revision_no: 1, amended_from: "qtn-1", status: "draft" } });
});

describe("QuotationDetailPage", () => {
  it("captures lost context when transitioning to lost", async () => {
    mockedTransitionQuotationStatus.mockResolvedValue({
      ok: true,
      data: {
        ...sampleQuotation,
        status: "lost",
        lost_reason: "price",
        competitor_name: "Acme Dynamics",
        loss_notes: "Lost on delivery lead time.",
      },
    });

    renderQuotationDetail();

    expect(await screen.findByRole("heading", { name: "Rotor Works" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Next status"), { target: { value: "lost" } });
    fireEvent.change(screen.getByLabelText("Lost Reason"), { target: { value: "price" } });
    fireEvent.change(screen.getByLabelText("Competitor"), { target: { value: "Acme Dynamics" } });
    fireEvent.change(screen.getByLabelText("Loss Notes"), { target: { value: "Lost on delivery lead time." } });
    fireEvent.click(screen.getByRole("button", { name: "Update status" }));

    expect(await screen.findByText("Lost")).toBeTruthy();
  });

  it("creates a revision and loads the new quotation lineage", async () => {
    mockedGetQuotation.mockResolvedValueOnce(sampleQuotation).mockResolvedValueOnce({
      ...sampleQuotation,
      id: "qtn-2",
      revision_no: 1,
      amended_from: "qtn-1",
      valid_till: "2026-06-15",
      status: "draft",
    });
    mockedReviseQuotation.mockResolvedValue({
      ok: true,
      data: {
        ...sampleQuotation,
        id: "qtn-2",
        revision_no: 1,
        amended_from: "qtn-1",
        valid_till: "2026-06-15",
        status: "draft",
      },
    });

    renderQuotationDetail();

    expect(await screen.findByRole("heading", { name: "Rotor Works" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Revision Valid Till"), { target: { value: "2026-06-15" } });
    fireEvent.change(screen.getByLabelText("Revision Notes"), { target: { value: "Reissued with updated validity." } });
    fireEvent.click(screen.getByRole("button", { name: "Create revision" }));

    expect(await screen.findByText("Revision 1")).toBeTruthy();
    expect(mockedGetQuotation).toHaveBeenCalledWith("qtn-2");
  });
});