import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import OpportunityDetailPage from "../../pages/crm/OpportunityDetailPage";
import {
  getCRMSetupBundle,
  getOpportunity,
  listLeads,
  prepareOpportunityQuotationHandoff,
  transitionOpportunityStatus,
  updateOpportunity,
} from "../../lib/api/crm";
import { listCustomers } from "../../lib/api/customers";
import { CRM_OPPORTUNITY_DETAIL_ROUTE, buildOpportunityDetailPath } from "../../lib/routes";

vi.mock("../../lib/api/crm", () => ({
  getCRMSetupBundle: vi.fn(),
  getOpportunity: vi.fn(),
  listLeads: vi.fn(),
  OPPORTUNITY_STATUS_OPTIONS: ["open", "replied", "quotation", "converted", "closed", "lost"],
  prepareOpportunityQuotationHandoff: vi.fn(),
  transitionOpportunityStatus: vi.fn(),
  updateOpportunity: vi.fn(),
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

const mockedGetOpportunity = vi.mocked(getOpportunity);
const mockedGetCRMSetupBundle = vi.mocked(getCRMSetupBundle);
const mockedListLeads = vi.mocked(listLeads);
const mockedListCustomers = vi.mocked(listCustomers);
const mockedUpdateOpportunity = vi.mocked(updateOpportunity);
const mockedTransitionOpportunityStatus = vi.mocked(transitionOpportunityStatus);
const mockedPrepareOpportunityQuotationHandoff = vi.mocked(prepareOpportunityQuotationHandoff);

const sampleOpportunity = {
  id: "opp-1",
  tenant_id: "tenant-1",
  opportunity_title: "Rotor Works Expansion",
  opportunity_from: "lead" as const,
  party_name: "lead-1",
  party_label: "Rotor Works",
  status: "replied" as const,
  sales_stage: "proposal",
  probability: 70,
  expected_closing: "2026-05-31",
  currency: "TWD",
  opportunity_amount: "25000.00",
  base_opportunity_amount: "25000.00",
  opportunity_owner: "alice@sales.test",
  territory: "North",
  customer_group: "Industrial",
  contact_person: "Amy Chen",
  contact_email: "amy@rotor.example",
  contact_mobile: "0912-000-111",
  job_title: "Procurement Manager",
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
  notes: "Priority expansion project.",
  lost_reason: "",
  competitor_name: "",
  loss_notes: "",
  version: 1,
  created_at: "2026-04-21T00:00:00Z",
  updated_at: "2026-04-21T00:00:00Z",
};

function renderOpportunityDetail() {
  return render(
    <MemoryRouter initialEntries={[buildOpportunityDetailPath("opp-1")]}>
      <Routes>
        <Route path={CRM_OPPORTUNITY_DETAIL_ROUTE} element={<OpportunityDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  mockedGetCRMSetupBundle.mockResolvedValue({
    settings: {
      lead_duplicate_policy: "block",
      default_quotation_validity_days: 30,
      contact_creation_enabled: true,
      carry_forward_communications: true,
      carry_forward_comments: true,
      opportunity_auto_close_days: 45,
    },
    sales_stages: [
      { id: "stage-1", name: "qualification", probability: 20, sort_order: 10, is_active: true },
      { id: "stage-2", name: "proposal", probability: 70, sort_order: 20, is_active: true },
    ],
    territories: [{ id: "territory-1", name: "North", parent_id: null, is_group: false, sort_order: 10, is_active: true }],
    customer_groups: [{ id: "group-1", name: "Industrial", parent_id: null, is_group: false, sort_order: 10, is_active: true }],
  });
  mockedGetOpportunity.mockResolvedValue(sampleOpportunity);
  mockedListLeads.mockResolvedValue({ items: [], page: 1, page_size: 100, total_count: 0, total_pages: 1 });
  mockedListCustomers.mockResolvedValue({ items: [], page: 1, page_size: 100, total_count: 0, total_pages: 1 });
  mockedUpdateOpportunity.mockResolvedValue({ ok: true, data: sampleOpportunity });
  mockedTransitionOpportunityStatus.mockResolvedValue({ ok: true, data: sampleOpportunity });
});

describe("OpportunityDetailPage", () => {
  it("shows quotation handoff preview after handoff", async () => {
    mockedPrepareOpportunityQuotationHandoff.mockResolvedValue({
      ok: true,
      data: {
        opportunity_id: "opp-1",
        opportunity_title: "Rotor Works Expansion",
        opportunity_from: "lead",
        party_name: "lead-1",
        party_label: "Rotor Works",
        customer_group: "Industrial",
        currency: "TWD",
        opportunity_amount: "25000.00",
        base_opportunity_amount: "25000.00",
        territory: "North",
        contact_person: "Amy Chen",
        contact_email: "amy@rotor.example",
        contact_mobile: "0912-000-111",
        job_title: "Procurement Manager",
        utm_source: "expo",
        utm_medium: "field",
        utm_campaign: "spring-2026",
        utm_content: "booth-a3",
        items: sampleOpportunity.items,
      },
    });

    renderOpportunityDetail();

    expect(await screen.findByRole("heading", { name: "Rotor Works Expansion" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Prepare quotation handoff" }));

    expect(await screen.findByText("Quotation handoff ready")).toBeTruthy();
    expect(screen.getByText("25000.00")).toBeTruthy();
  });

  it("captures lost context when transitioning to lost", async () => {
    mockedTransitionOpportunityStatus.mockResolvedValue({
      ok: true,
      data: {
        ...sampleOpportunity,
        status: "lost",
        lost_reason: "price",
        competitor_name: "Acme Dynamics",
        loss_notes: "Lost on delivery lead time.",
      },
    });

    renderOpportunityDetail();

    expect(await screen.findByRole("heading", { name: "Rotor Works Expansion" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Next status"), { target: { value: "lost" } });
    fireEvent.change(screen.getByLabelText("Lost Reason"), { target: { value: "price" } });
    fireEvent.change(screen.getByLabelText("Competitor"), { target: { value: "Acme Dynamics" } });
    fireEvent.change(screen.getByLabelText("Loss Notes"), { target: { value: "Lost on delivery lead time." } });
    fireEvent.click(screen.getByRole("button", { name: "Update status" }));

    expect(await screen.findByText("Lost")).toBeTruthy();
  });
});