import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { OpportunityListPage } from "../../pages/crm/OpportunityListPage";
import { listOpportunities } from "../../lib/api/crm";
import { CRM_OPPORTUNITIES_ROUTE } from "../../lib/routes";

vi.mock("../../lib/api/crm", () => ({
  listOpportunities: vi.fn(),
}));

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canAccess: () => true,
    canWrite: () => true,
  }),
}));

const mockedListOpportunities = vi.mocked(listOpportunities);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("OpportunityListPage", () => {
  it("renders the opportunity list and pipeline summary returned by the API", async () => {
    mockedListOpportunities.mockResolvedValue({
      items: [
        {
          id: "opp-1",
          opportunity_title: "Rotor Works Expansion",
          opportunity_from: "lead",
          party_name: "lead-1",
          party_label: "Rotor Works",
          status: "open",
          sales_stage: "qualification",
          probability: 55,
          expected_closing: "2026-05-31",
          currency: "TWD",
          opportunity_amount: "25000.00",
          opportunity_owner: "alice@sales.test",
          territory: "North",
          updated_at: "2026-04-21T00:00:00Z",
        },
      ],
      page: 1,
      page_size: 50,
      total_count: 1,
      total_pages: 1,
    });

    render(
      <MemoryRouter initialEntries={[CRM_OPPORTUNITIES_ROUTE]}>
        <Routes>
          <Route path={CRM_OPPORTUNITIES_ROUTE} element={<OpportunityListPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Opportunities" })).toBeTruthy();
    expect(await screen.findByRole("button", { name: "Opportunity Rotor Works Expansion" })).toBeTruthy();
    expect(screen.getByText("1")).toBeTruthy();
  });

  it("shows API load failures instead of an empty state", async () => {
    mockedListOpportunities.mockRejectedValueOnce(new Error("Forbidden"));

    render(
      <MemoryRouter initialEntries={[CRM_OPPORTUNITIES_ROUTE]}>
        <Routes>
          <Route path={CRM_OPPORTUNITIES_ROUTE} element={<OpportunityListPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Forbidden")).toBeTruthy();
  });
});