import "../helpers/i18n";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import CustomerForm from "../../components/customers/CustomerForm";

vi.mock("../../hooks/useCommercialDefaultsOptions", () => ({
  useCommercialDefaultsOptions: () => ({
    currencies: [
      { id: "currency-twd", code: "TWD", is_base_currency: true },
      { id: "currency-usd", code: "USD", is_base_currency: false },
    ],
    paymentTerms: [{ id: "terms-net-30", template_name: "Net 30" }],
    loading: false,
    error: null,
    refresh: vi.fn(),
  }),
}));

describe("CustomerForm", () => {
  function fillRequiredFields(overrides?: Partial<Record<string, string>>) {
    fireEvent.change(screen.getByLabelText(/Company Name/i), {
      target: { value: overrides?.company_name ?? "  Acme Trading  " },
    });
    fireEvent.change(screen.getByLabelText(/Business Number/i), {
      target: { value: overrides?.business_number ?? "0459-5257" },
    });
    fireEvent.change(screen.getByLabelText(/Billing Address/i), {
      target: { value: overrides?.billing_address ?? "  No. 1 Harbor Road  " },
    });
    fireEvent.change(screen.getByLabelText(/Contact Name/i), {
      target: { value: overrides?.contact_name ?? "  Jane Doe  " },
    });
    fireEvent.change(screen.getByLabelText(/Contact Phone/i), {
      target: { value: overrides?.contact_phone ?? " 02-1234-5678  " },
    });
    fireEvent.change(screen.getByLabelText(/Contact Email/i), {
      target: { value: overrides?.contact_email ?? "  SALES@ACME.COM  " },
    });
    fireEvent.change(screen.getByLabelText(/Credit Limit/i), {
      target: { value: overrides?.credit_limit ?? "120.5" },
    });
  }

  it("submits a normalized payload from the shared customer schema", async () => {
    const onSubmit = vi.fn();

    render(<CustomerForm onSubmit={onSubmit} />);

    fillRequiredFields();
  fireEvent.change(screen.getByLabelText(/Default Currency/i), { target: { value: "TWD" } });
  fireEvent.change(screen.getByLabelText(/Payment Terms/i), { target: { value: "terms-net-30" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Customer" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        company_name: "Acme Trading",
        business_number: "0459-5257",
        billing_address: "No. 1 Harbor Road",
        contact_name: "Jane Doe",
        contact_phone: "02-1234-5678",
        contact_email: "sales@acme.com",
        credit_limit: "120.50",
        default_currency_code: "TWD",
        payment_terms_template_id: "terms-net-30",
      });
    });
  });

  it("blocks submit and shows the Taiwan business-number checksum error", async () => {
    const onSubmit = vi.fn();

    render(<CustomerForm onSubmit={onSubmit} />);

    fillRequiredFields({ business_number: "04595258" });
    fireEvent.click(screen.getByRole("button", { name: "Create Customer" }));

    await waitFor(() => {
      expect(screen.getByText("Business number checksum is invalid.")).toBeTruthy();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });
});