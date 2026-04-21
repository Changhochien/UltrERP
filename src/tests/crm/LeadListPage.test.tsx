import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { LeadListPage } from "../../pages/crm/LeadListPage";
import { listLeads } from "../../lib/api/crm";
import { CRM_LEADS_ROUTE } from "../../lib/routes";

vi.mock("../../lib/api/crm", () => ({
  convertLeadToCustomer: vi.fn(),
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
  listLeads: vi.fn(),
  transitionLeadStatus: vi.fn(),
  updateLead: vi.fn(),
}));

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canAccess: () => true,
    canWrite: () => true,
  }),
}));

const mockedListLeads = vi.mocked(listLeads);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("LeadListPage", () => {
  it("renders the lead list returned by the API", async () => {
    mockedListLeads.mockResolvedValue({
      items: [
        {
          id: "lead-1",
          lead_name: "Rotor Works",
          company_name: "Rotor Works",
          email_id: "owner@rotor.example",
          phone: "02-1234-5678",
          mobile_no: "0912-000-111",
          territory: "North",
          lead_owner: "Alice",
          source: "Expo",
          status: "open",
          qualification_status: "in_process",
          updated_at: "2026-04-21T00:00:00Z",
        },
      ],
      page: 1,
      page_size: 20,
      total_count: 1,
      total_pages: 1,
    });

    render(
      <MemoryRouter initialEntries={[CRM_LEADS_ROUTE]}>
        <Routes>
          <Route path={CRM_LEADS_ROUTE} element={<LeadListPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Leads" })).toBeTruthy();
    expect(await screen.findByRole("button", { name: "Lead Rotor Works" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Create Lead" })).toBeTruthy();
  });

  it("shows API load failures instead of an empty state", async () => {
    mockedListLeads.mockRejectedValueOnce(new Error("Forbidden"));

    render(
      <MemoryRouter initialEntries={[CRM_LEADS_ROUTE]}>
        <Routes>
          <Route path={CRM_LEADS_ROUTE} element={<LeadListPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Forbidden")).toBeTruthy();
  });
});
