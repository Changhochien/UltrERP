import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CreateQuotationPage from "../../pages/crm/CreateQuotationPage";
import { createQuotation, listLeads } from "../../lib/api/crm";
import { listCustomers } from "../../lib/api/customers";

vi.mock("../../lib/api/crm", () => ({
  createQuotation: vi.fn(),
  listLeads: vi.fn(),
}));

vi.mock("../../lib/api/customers", () => ({
  listCustomers: vi.fn(),
}));

vi.mock("../../hooks/useToast", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const mockedCreateQuotation = vi.mocked(createQuotation);
const mockedListLeads = vi.mocked(listLeads);
const mockedListCustomers = vi.mocked(listCustomers);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  mockedCreateQuotation.mockReset();
  mockedListLeads.mockResolvedValue({ items: [], page: 1, page_size: 100, total_count: 0, total_pages: 1 });
  mockedListCustomers.mockResolvedValue({ items: [], page: 1, page_size: 100, total_count: 0, total_pages: 1 });
});

describe("CreateQuotationPage", () => {
  it("creates a quotation and shows the created state", async () => {
    mockedCreateQuotation.mockResolvedValue({
      ok: true,
      data: {
        id: "qtn-1",
        tenant_id: "tenant-1",
        quotation_to: "prospect",
        party_name: "Rotor Works",
        party_label: "Rotor Works",
        status: "draft",
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
        opportunity_id: null,
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
      },
    });

    render(
      <MemoryRouter>
        <CreateQuotationPage />
      </MemoryRouter>,
    );

    fireEvent.change(await screen.findByLabelText("Quotation To"), {
      target: { value: "prospect" },
    });
    fireEvent.change(screen.getByLabelText("Party Name *"), {
      target: { value: "Rotor Works" },
    });
    fireEvent.change(screen.getByLabelText("Company *"), {
      target: { value: "UltrERP Taiwan" },
    });
    fireEvent.change(screen.getByLabelText("Transaction Date *"), {
      target: { value: "2026-04-21" },
    });
    fireEvent.change(screen.getByLabelText("Valid Till *"), {
      target: { value: "2026-05-21" },
    });
    fireEvent.change(screen.getByLabelText("Item Name *"), {
      target: { value: "Rotor Assembly" },
    });
    fireEvent.change(screen.getByLabelText("Quantity *"), {
      target: { value: "2" },
    });
    fireEvent.change(screen.getByLabelText("Unit Price"), {
      target: { value: "12500" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Quotation" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Quotation Created" })).toBeTruthy();
  });

  it("prefills a quotation from opportunity handoff state", async () => {
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
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/crm/quotations/new",
            state: {
              handoff: {
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
              },
            },
          },
        ]}
      >
        <CreateQuotationPage />
      </MemoryRouter>,
    );

    expect(await screen.findByDisplayValue("lead-1")).toBeTruthy();
    expect(screen.getByDisplayValue("UltrERP Taiwan")).toBeTruthy();
    expect(screen.getByDisplayValue("Rotor Assembly")).toBeTruthy();
  });
});