import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import LeadDetailPage from "../../pages/crm/LeadDetailPage";
import {
  convertLeadToCustomer,
  getCRMSetupBundle,
  getLead,
  handoffLeadToOpportunity,
  transitionLeadStatus,
  updateLead,
} from "../../lib/api/crm";
import { CRM_LEAD_DETAIL_ROUTE, buildLeadDetailPath } from "../../lib/routes";

vi.mock("../../lib/api/crm", () => ({
  convertLeadToCustomer: vi.fn(),
  getCRMSetupBundle: vi.fn(),
  getLead: vi.fn(),
  handoffLeadToOpportunity: vi.fn(),
  LEAD_STATUS_OPTIONS: [
    "lead",
    "open",
    "replied",
    "opportunity",
    "quotation",
    "lost_quotation",
    "interested",
    "converted",
    "do_not_contact",
  ],
  transitionLeadStatus: vi.fn(),
  updateLead: vi.fn(),
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

const mockedGetLead = vi.mocked(getLead);
const mockedGetCRMSetupBundle = vi.mocked(getCRMSetupBundle);
const mockedUpdateLead = vi.mocked(updateLead);
const mockedTransitionLeadStatus = vi.mocked(transitionLeadStatus);
const mockedHandoffLeadToOpportunity = vi.mocked(handoffLeadToOpportunity);
const mockedConvertLeadToCustomer = vi.mocked(convertLeadToCustomer);

const sampleLead = {
  id: "lead-1",
  tenant_id: "tenant-1",
  lead_name: "Rotor Works",
  company_name: "Rotor Works",
  email_id: "owner@rotor.example",
  phone: "02-1234-5678",
  mobile_no: "0912-000-111",
  territory: "North",
  lead_owner: "Alice",
  source: "Expo",
  status: "replied" as const,
  qualification_status: "qualified" as const,
  qualified_by: "Alice",
  annual_revenue: "1250000.00",
  no_of_employees: 15,
  industry: "Industrial",
  market_segment: "Manufacturing",
  utm_source: "expo",
  utm_medium: "field",
  utm_campaign: "spring-2026",
  utm_content: "booth-a3",
  notes: "Warm inbound lead",
  conversion_state: "not_converted" as const,
  conversion_path: "",
  converted_by: "",
  converted_customer_id: null,
  converted_opportunity_id: null,
  converted_quotation_id: null,
  converted_at: null,
  version: 1,
  created_at: "2026-04-21T00:00:00Z",
  updated_at: "2026-04-21T00:00:00Z",
};

function renderLeadDetail() {
  return render(
    <MemoryRouter initialEntries={[buildLeadDetailPath("lead-1")]}> 
      <Routes>
        <Route path={CRM_LEAD_DETAIL_ROUTE} element={<LeadDetailPage />} />
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
    sales_stages: [],
    territories: [{ id: "territory-1", name: "North", parent_id: null, is_group: false, sort_order: 10, is_active: true }],
    customer_groups: [],
  });
  mockedGetLead.mockResolvedValue(sampleLead);
  mockedUpdateLead.mockResolvedValue({ ok: true, data: sampleLead });
  mockedTransitionLeadStatus.mockResolvedValue({ ok: true, data: sampleLead });
});

describe("LeadDetailPage", () => {
  it("shows opportunity handoff preview after handoff", async () => {
    mockedHandoffLeadToOpportunity.mockResolvedValue({
      ok: true,
      data: {
        lead_id: "lead-1",
        lead_name: "Rotor Works",
        company_name: "Rotor Works",
        email_id: "owner@rotor.example",
        phone: "02-1234-5678",
        mobile_no: "0912-000-111",
        territory: "North",
        lead_owner: "Alice",
        source: "Expo",
        qualification_status: "qualified",
        utm_source: "expo",
        utm_medium: "field",
        utm_campaign: "spring-2026",
        utm_content: "booth-a3",
      },
    });

    renderLeadDetail();

    expect(await screen.findByRole("heading", { name: "Rotor Works" })).toBeTruthy();
    expect(screen.queryByRole("option", { name: "Opportunity" })).toBeNull();
    expect(screen.queryByRole("option", { name: "Converted" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Mark as opportunity handoff" }));

    expect(await screen.findByText("Ready for Story 23.2 handoff")).toBeTruthy();
    expect(screen.getByText("spring-2026")).toBeTruthy();
  });

  it("shows duplicate guidance when saving would collide with another record", async () => {
    mockedUpdateLead.mockResolvedValue({
      ok: false,
      duplicate: {
        candidates: [
          {
            kind: "customer",
            id: "customer-1",
            label: "Acme Industrial",
            matched_on: "company_name",
          },
        ],
      },
      errors: [],
    });

    renderLeadDetail();

    expect(await screen.findByRole("heading", { name: "Rotor Works" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    expect(await screen.findByRole("heading", { name: "Possible duplicate lead" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open customer" })).toBeTruthy();
    expect(mockedUpdateLead).toHaveBeenCalledWith(
      "lead-1",
      expect.objectContaining({
        company_name: "Rotor Works",
        email_id: "owner@rotor.example",
        version: 1,
      }),
    );
  });

  it("shows the real load error instead of masking it as not found", async () => {
    mockedGetLead.mockRejectedValueOnce(new Error("Forbidden"));

    renderLeadDetail();

    expect(await screen.findByText("Forbidden")).toBeTruthy();
  });

  it("converts a lead to a customer and shows the customer shortcut", async () => {
    mockedHandoffLeadToOpportunity.mockResolvedValue({ ok: false, errors: [] });
    mockedConvertLeadToCustomer.mockResolvedValue({
      ok: true,
      data: {
        lead_id: "lead-1",
        customer_id: "customer-1",
        status: "converted",
      },
    });

    renderLeadDetail();

    expect(await screen.findByRole("heading", { name: "Rotor Works" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Business Number"), {
      target: { value: "12345675" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Convert to customer" }));

    expect(await screen.findByRole("button", { name: "View customer" })).toBeTruthy();
  });

  it("shows conversion summary and linked record shortcuts", async () => {
    mockedGetLead.mockResolvedValue({
      ...sampleLead,
      status: "quotation",
      conversion_state: "partially_converted",
      conversion_path: "customer+quotation",
      converted_by: "sales.owner@test",
      converted_customer_id: "customer-1",
      converted_opportunity_id: "opp-1",
      converted_quotation_id: "qtn-1",
      converted_at: "2026-04-22T08:30:00Z",
    });

    renderLeadDetail();

    expect(await screen.findByText("Customer + Quotation")).toBeTruthy();
    expect(screen.getByRole("button", { name: "View customer" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "View opportunity" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "View quotation" })).toBeTruthy();
  });
});
