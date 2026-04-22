import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CreateLeadPage from "../../pages/crm/CreateLeadPage";
import { buildCustomerDetailPath } from "../../lib/routes";
import { createLead, getCRMSetupBundle } from "../../lib/api/crm";

vi.mock("../../lib/api/crm", () => ({
  createLead: vi.fn(),
  getCRMSetupBundle: vi.fn(),
}));

vi.mock("../../hooks/useToast", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const mockedCreateLead = vi.mocked(createLead);
const mockedGetCRMSetupBundle = vi.mocked(getCRMSetupBundle);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  mockedCreateLead.mockReset();
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
});

describe("CreateLeadPage", () => {
  it("creates a lead and shows the created state", async () => {
    mockedCreateLead.mockResolvedValue({
      ok: true,
      data: {
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
        status: "lead",
        qualification_status: "in_process",
        qualified_by: "",
        annual_revenue: "1250000.00",
        no_of_employees: 15,
        industry: "Industrial",
        market_segment: "Manufacturing",
        utm_source: "expo",
        utm_medium: "field",
        utm_campaign: "spring-2026",
        utm_content: "booth-a3",
        notes: "Warm inbound lead",
        conversion_state: "not_converted",
        conversion_path: "direct",
        converted_by: "",
        converted_customer_id: null,
        converted_opportunity_id: null,
        converted_quotation_id: null,
        converted_at: null,
        version: 1,
        created_at: "2026-04-21T00:00:00Z",
        updated_at: "2026-04-21T00:00:00Z",
      },
    });

    render(
      <MemoryRouter>
        <CreateLeadPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Lead Name *"), {
      target: { value: "Rotor Works" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Lead" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Lead Created" })).toBeTruthy();
    expect(screen.getByText(/Rotor Works/)).toBeTruthy();
  });

  it("shows duplicate guidance and opens the matching customer", async () => {
    const navigateSpy = vi.fn();
    mockedCreateLead.mockResolvedValue({
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

    render(
      <MemoryRouter>
        <CreateLeadPage onNavigate={navigateSpy} />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Lead Name *"), {
      target: { value: "Acme Industrial" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Lead" }));

    expect(await screen.findByRole("heading", { name: "Possible duplicate lead" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Open customer" }));
    expect(navigateSpy).toHaveBeenCalledWith(buildCustomerDetailPath("customer-1"));
  });

  it("preserves the submitted draft after dismissing duplicate guidance", async () => {
    mockedCreateLead.mockResolvedValue({
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

    render(
      <MemoryRouter>
        <CreateLeadPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Lead Name *"), {
      target: { value: "Acme Industrial" },
    });
    fireEvent.change(screen.getByLabelText("Company Name"), {
      target: { value: "Acme Industrial" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Lead" }));

    expect(await screen.findByRole("heading", { name: "Possible duplicate lead" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Continue editing" }));

    expect((screen.getByLabelText("Lead Name *") as HTMLInputElement).value).toBe("Acme Industrial");
    expect((screen.getByLabelText("Company Name") as HTMLInputElement).value).toBe("Acme Industrial");
  });
});
