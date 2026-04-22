import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CreateOpportunityPage from "../../pages/crm/CreateOpportunityPage";
import { createOpportunity, getCRMSetupBundle, listLeads } from "../../lib/api/crm";
import { listCustomers } from "../../lib/api/customers";

vi.mock("../../lib/api/crm", () => ({
  createOpportunity: vi.fn(),
  getCRMSetupBundle: vi.fn(),
  listLeads: vi.fn(),
}));

vi.mock("../../lib/api/customers", () => ({
  listCustomers: vi.fn(),
}));

vi.mock("../../hooks/useToast", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const mockedCreateOpportunity = vi.mocked(createOpportunity);
const mockedGetCRMSetupBundle = vi.mocked(getCRMSetupBundle);
const mockedListLeads = vi.mocked(listLeads);
const mockedListCustomers = vi.mocked(listCustomers);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  mockedCreateOpportunity.mockReset();
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
  mockedListLeads.mockResolvedValue({ items: [], page: 1, page_size: 100, total_count: 0, total_pages: 1 });
  mockedListCustomers.mockResolvedValue({ items: [], page: 1, page_size: 100, total_count: 0, total_pages: 1 });
});

describe("CreateOpportunityPage", () => {
  it("creates an opportunity and shows the created state", async () => {
    mockedCreateOpportunity.mockResolvedValue({
      ok: true,
      data: {
        id: "opp-1",
        tenant_id: "tenant-1",
        opportunity_title: "Rotor Works Expansion",
        opportunity_from: "prospect",
        party_name: "Rotor Works",
        party_label: "Rotor Works",
        status: "open",
        sales_stage: "qualification",
        probability: 55,
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
        items: [],
        notes: "",
        lost_reason: "",
        competitor_name: "",
        loss_notes: "",
        version: 1,
        created_at: "2026-04-21T00:00:00Z",
        updated_at: "2026-04-21T00:00:00Z",
      },
    });

    render(
      <MemoryRouter>
        <CreateOpportunityPage />
      </MemoryRouter>,
    );

    fireEvent.change(await screen.findByLabelText("Opportunity Title *"), {
      target: { value: "Rotor Works Expansion" },
    });
    fireEvent.change(screen.getByLabelText("Party Name"), {
      target: { value: "Rotor Works" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Opportunity" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Opportunity Created" })).toBeTruthy();
  });

  it("prefills a lead-linked opportunity from query params", async () => {
    mockedListLeads.mockResolvedValue({
      items: [
        {
          id: "lead-1",
          lead_name: "Amy Chen",
          company_name: "Rotor Works",
          email_id: "amy@rotor.example",
          phone: "02-1234-5678",
          mobile_no: "0912-000-111",
          territory: "North",
          lead_owner: "alice",
          source: "expo",
          status: "replied",
          qualification_status: "qualified",
          updated_at: "2026-04-21T00:00:00Z",
        },
      ],
      page: 1,
      page_size: 100,
      total_count: 1,
      total_pages: 1,
    });

    render(
      <MemoryRouter initialEntries={["/crm/opportunities/new?partyType=lead&partyName=lead-1&partyLabel=Rotor%20Works"]}>
        <CreateOpportunityPage />
      </MemoryRouter>,
    );

    expect(await screen.findByDisplayValue("lead-1")).toBeTruthy();
    expect(screen.getByDisplayValue("Rotor Works Opportunity")).toBeTruthy();
  });
});