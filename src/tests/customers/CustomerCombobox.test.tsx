import "../helpers/i18n";

import type { ReactNode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CustomerCombobox } from "@/domain/customers/components/CustomerCombobox";
import { createCustomer, listCustomers } from "../../lib/api/customers";
import { ToastProvider } from "../../providers/ToastProvider";

vi.mock("../../lib/api/customers", () => ({
  createCustomer: vi.fn(),
  listCustomers: vi.fn(),
}));

function renderWithToastProvider(component: ReactNode) {
  return render(<ToastProvider>{component}</ToastProvider>);
}

describe("CustomerCombobox", () => {
  beforeEach(() => {
    vi.mocked(listCustomers).mockResolvedValue({
      items: [],
      page: 1,
      page_size: 50,
      total_count: 0,
      total_pages: 1,
    });

    vi.mocked(createCustomer).mockResolvedValue({
      ok: true,
      data: {
        id: "cust-1",
        tenant_id: "tenant-1",
        company_name: "Acme Corp",
        normalized_business_number: "04595257",
        billing_address: "",
        contact_name: "Jane Doe",
        contact_phone: "02-12345678",
        contact_email: "sales@acme.com",
        credit_limit: "0.00",
        status: "active",
        version: 1,
        created_at: "2026-04-03T00:00:00Z",
        updated_at: "2026-04-03T00:00:00Z",
      },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("uses the shared customer schema for quick-create payloads", async () => {
    const onChange = vi.fn();

    renderWithToastProvider(<CustomerCombobox value="" onChange={onChange} />);

    fireEvent.click(screen.getByRole("combobox"));

    fireEvent.change(screen.getByPlaceholderText("Search customer by name or BAN…"), {
      target: { value: "Acme" },
    });

    await waitFor(() => {
      expect(screen.getByText("Create new customer")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Create new customer"));

    const createButton = screen.getByRole("button", { name: "Create" }) as HTMLButtonElement;
    expect(createButton.disabled).toBe(true);

    fireEvent.change(screen.getByPlaceholderText("Company name *"), {
      target: { value: "  Acme Corp  " },
    });
    fireEvent.change(screen.getByPlaceholderText("Business number *"), {
      target: { value: "04595257" },
    });
    fireEvent.change(screen.getByPlaceholderText("Contact phone *"), {
      target: { value: "02-12345678" },
    });
    fireEvent.change(screen.getByPlaceholderText("Contact name *"), {
      target: { value: "Jane Doe" },
    });
    fireEvent.change(screen.getByPlaceholderText("Contact email *"), {
      target: { value: "Sales@Acme.COM" },
    });

    expect(createButton.disabled).toBe(false);

    fireEvent.click(createButton);

    await waitFor(() => {
      expect(createCustomer).toHaveBeenCalledWith({
        company_name: "Acme Corp",
        business_number: "04595257",
        billing_address: "",
        contact_name: "Jane Doe",
        contact_phone: "02-12345678",
        contact_email: "sales@acme.com",
        credit_limit: "0.00",
      });
    });

    expect(onChange).toHaveBeenCalledWith("cust-1");
  });

  it("shows quick-create field errors for invalid client-side input", async () => {
    renderWithToastProvider(<CustomerCombobox value="" onChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.change(screen.getByPlaceholderText("Search customer by name or BAN…"), {
      target: { value: "Acme" },
    });

    await waitFor(() => {
      expect(screen.getByText("Create new customer")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Create new customer"));

    fireEvent.change(screen.getByPlaceholderText("Company name *"), {
      target: { value: "Acme Corp" },
    });
    fireEvent.change(screen.getByPlaceholderText("Business number *"), {
      target: { value: "04595257" },
    });
    fireEvent.change(screen.getByPlaceholderText("Contact phone *"), {
      target: { value: "02-12345678" },
    });
    fireEvent.change(screen.getByPlaceholderText("Contact name *"), {
      target: { value: "Jane Doe" },
    });
    fireEvent.change(screen.getByPlaceholderText("Contact email *"), {
      target: { value: "not-an-email" },
    });

    expect(screen.getByText(/customer\.form\.invalidEmail|valid email address/i)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Create" }) as HTMLButtonElement).disabled).toBe(true);
    expect(createCustomer).not.toHaveBeenCalled();
  });

  it("offers an accessible path to select an existing duplicate customer", async () => {
    const onChange = vi.fn();
    vi.mocked(createCustomer).mockResolvedValue({
      ok: false,
      duplicate: {
        existing_customer_id: "cust-existing",
        existing_customer_name: "Acme Corp",
        normalized_business_number: "04595257",
      },
      errors: [],
    });

    renderWithToastProvider(<CustomerCombobox value="" onChange={onChange} />);

    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.change(screen.getByPlaceholderText("Search customer by name or BAN…"), {
      target: { value: "Acme" },
    });

    await waitFor(() => {
      expect(screen.getByText("Create new customer")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Create new customer"));

    fireEvent.change(screen.getByPlaceholderText("Company name *"), {
      target: { value: "Acme Corp" },
    });
    fireEvent.change(screen.getByPlaceholderText("Business number *"), {
      target: { value: "04595257" },
    });
    fireEvent.change(screen.getByPlaceholderText("Contact phone *"), {
      target: { value: "02-12345678" },
    });
    fireEvent.change(screen.getByPlaceholderText("Contact name *"), {
      target: { value: "Jane Doe" },
    });
    fireEvent.change(screen.getByPlaceholderText("Contact email *"), {
      target: { value: "sales@acme.com" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByRole("button", { name: "Use existing customer" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Use existing customer" }));

    expect(onChange).toHaveBeenCalledWith("cust-existing");
  });
});