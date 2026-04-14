import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CUSTOMERS_ROUTE } from "../../lib/routes";
import CreateCustomerPage from "../../pages/customers/CreateCustomerPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      // Validation messages from CustomerForm
      if (key === "customer.form.companyNameRequired") return "Company name is required.";
      if (key === "customer.form.creditLimitNonNegative") return "Credit limit must be non-negative.";
      return key; // fallback to key itself for all other keys
    },
  }),
}));

afterEach(() => {
  cleanup();
});

function fillValidForm() {
  fireEvent.change(screen.getByLabelText(/Company Name/), {
    target: { value: "台灣好公司有限公司" },
  });
  fireEvent.change(screen.getByLabelText(/Business Number/), {
    target: { value: "04595257" },
  });
  fireEvent.change(screen.getByLabelText(/Contact Name/), {
    target: { value: "王大明" },
  });
  fireEvent.change(screen.getByLabelText(/Contact Phone/), {
    target: { value: "0912-345-678" },
  });
  fireEvent.change(screen.getByLabelText(/Contact Email/), {
    target: { value: "wang@example.com" },
  });
}

describe("CreateCustomerPage", () => {
  it("renders the create customer heading", () => {
    render(<CreateCustomerPage />);
    expect(screen.getByRole("heading", { name: "Create Customer" })).toBeTruthy();
  });

  it("shows validation error for empty company name on submit", () => {
    render(<CreateCustomerPage />);
    fireEvent.click(screen.getByRole("button", { name: "Create Customer" }));
    expect(screen.getByText("Company name is required.")).toBeTruthy();
  });

  it("shows validation error for invalid business number on submit", () => {
    render(<CreateCustomerPage />);
    const bnInput = screen.getByLabelText(/Business Number/);
    fireEvent.change(bnInput, { target: { value: "1234" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Customer" }));
    expect(screen.getByText(/must be exactly 8 digits/)).toBeTruthy();
  });

  it("shows validation error for negative credit limit", () => {
    render(<CreateCustomerPage />);
    const limitInput = screen.getByLabelText(/Credit Limit/);
    fireEvent.change(limitInput, { target: { value: "-5" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Customer" }));
    expect(screen.getByText("Credit limit must be non-negative.")).toBeTruthy();
  });

  it("submits valid form without client-side errors", async () => {
    // Mock fetch to simulate a successful create
    const mockResponse = {
      id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      tenant_id: "00000000-0000-0000-0000-000000000001",
      company_name: "台灣好公司有限公司",
      normalized_business_number: "04595257",
      billing_address: "台北市",
      contact_name: "王大明",
      contact_phone: "0912-345-678",
      contact_email: "wang@example.com",
      credit_limit: "100000.00",
      status: "active",
      version: 1,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    render(<CreateCustomerPage />);
    fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: "Create Customer" }));

    // Wait for the success view — use h1 to avoid ambiguity with h3 in SectionCard
    const heading = await screen.findByRole("heading", { level: 1, name: "Customer Created" });
    expect(heading).toBeTruthy();
    expect(screen.getByText(/台灣好公司有限公司/)).toBeTruthy();

    fetchSpy.mockRestore();
  });

  it("shows a form-level error when create request fails before a response", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new Error("network down"));

    render(<CreateCustomerPage />);
    fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: "Create Customer" }));

    expect(
      await screen.findByText("Unable to reach the server. Please try again."),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Create Customer" })).toBeTruthy();

    fetchSpy.mockRestore();
  });
});

describe("CreateCustomerPage — duplicate handling", () => {
  it("shows duplicate warning when server returns 409", async () => {
    const duplicateResponse = {
      error: "duplicate_business_number",
      existing_customer_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      existing_customer_name: "Existing Corp",
      normalized_business_number: "04595257",
    };

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => duplicateResponse,
    } as Response);

    render(<CreateCustomerPage />);
    fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: "Create Customer" }));

    const heading = await screen.findByRole("heading", { name: "Duplicate Business Number" });
    expect(heading).toBeTruthy();
    expect(screen.getByText(/Existing Corp/)).toBeTruthy();
    expect(screen.getByText(/04595257/)).toBeTruthy();

    fetchSpy.mockRestore();
  });

  it("hides form when duplicate is shown", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({
        error: "duplicate_business_number",
        existing_customer_id: "aaa",
        existing_customer_name: "Corp",
        normalized_business_number: "04595257",
      }),
    } as Response);

    render(<CreateCustomerPage />);
    fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: "Create Customer" }));

    await screen.findByText("Duplicate Business Number");
    // The form should be hidden (no Create Customer button visible)
    expect(screen.queryByRole("button", { name: "Create Customer" })).toBeNull();

    fetchSpy.mockRestore();
  });

  it("cancel button clears duplicate and shows form again", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({
        error: "duplicate_business_number",
        existing_customer_id: "aaa",
        existing_customer_name: "Corp",
        normalized_business_number: "04595257",
      }),
    } as Response);

    render(<CreateCustomerPage />);
    fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: "Create Customer" }));

    await screen.findByText("Duplicate Business Number");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    // Form should reappear
    expect(screen.getByRole("button", { name: "Create Customer" })).toBeTruthy();

    fetchSpy.mockRestore();
  });

  it("view existing customer button calls onNavigate", async () => {
    const navigateSpy = vi.fn();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({
        error: "duplicate_business_number",
        existing_customer_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        existing_customer_name: "Corp",
        normalized_business_number: "04595257",
      }),
    } as Response);

    render(<CreateCustomerPage onNavigate={navigateSpy} />);
    fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: "Create Customer" }));

    await screen.findByText("Duplicate Business Number");
    fireEvent.click(screen.getByRole("button", { name: "View Existing Customer" }));

    expect(navigateSpy).toHaveBeenCalledWith(CUSTOMERS_ROUTE);

    fetchSpy.mockRestore();
  });
});
