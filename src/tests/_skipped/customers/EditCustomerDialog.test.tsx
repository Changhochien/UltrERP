import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EditCustomerDialog } from "@/domain/customers/components/EditCustomerDialog";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const CUSTOMER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

function mockCustomerResponse() {
  return {
    id: CUSTOMER_ID,
    tenant_id: "00000000-0000-0000-0000-000000000001",
    company_name: "台灣好公司有限公司",
    normalized_business_number: "04595257",
    billing_address: "台北市信義區信義路五段7號",
    contact_name: "王大明",
    contact_phone: "0912-345-678",
    contact_email: "wang@example.com",
    credit_limit: "100000.00",
    status: "active",
    version: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function renderDialog(props?: { onClose?: () => void; onSaved?: () => void }) {
  return render(
    <EditCustomerDialog
      customerId={CUSTOMER_ID}
      onClose={props?.onClose ?? vi.fn()}
      onSaved={props?.onSaved ?? vi.fn()}
    />,
  );
}

describe("EditCustomerDialog", () => {
  it("renders loading state and then pre-fills form", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockCustomerResponse(),
    } as Response);

    renderDialog();
    expect(screen.getByText("Loading…")).toBeTruthy();

    const nameInput = await screen.findByLabelText(/Company Name/);
    expect((nameInput as HTMLInputElement).value).toBe("台灣好公司有限公司");
    expect((screen.getByLabelText(/Business Number/) as HTMLInputElement).value).toBe("04595257");
    expect((screen.getByLabelText(/Contact Email/) as HTMLInputElement).value).toBe(
      "wang@example.com",
    );
  });

  it("shows not found when customer doesn't exist", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Not found" }),
    } as Response);

    renderDialog();
    const msg = await screen.findByText("Customer not found.");
    expect(msg).toBeTruthy();
  });

  it("saves and calls onSaved on success", async () => {
    const onSaved = vi.fn();
    const updatedCustomer = { ...mockCustomerResponse(), company_name: "新名稱", version: 2 };

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockCustomerResponse(),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => updatedCustomer,
      } as Response);

    renderDialog({ onSaved });

    const nameInput = await screen.findByLabelText(/Company Name/);
    fireEvent.change(nameInput, { target: { value: "新名稱" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    await waitFor(() => {
      expect(onSaved).toHaveBeenCalled();
    });
  });

  it("shows version conflict warning on 409 version_conflict", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockCustomerResponse(),
      } as Response)
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({
          error: "version_conflict",
          expected_version: 1,
          actual_version: 2,
        }),
      } as Response);

    renderDialog();

    const nameInput = await screen.findByLabelText(/Company Name/);
    fireEvent.change(nameInput, { target: { value: "Changed" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    const warning = await screen.findByText(/Version conflict/);
    expect(warning).toBeTruthy();
    // Form should be hidden during conflict
    expect(screen.queryByRole("button", { name: "Save Changes" })).toBeNull();
  });

  it("shows duplicate warning on 409 duplicate_business_number", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockCustomerResponse(),
      } as Response)
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({
          error: "duplicate_business_number",
          existing_customer_id: "other-id",
          existing_customer_name: "Other Corp",
          normalized_business_number: "22099131",
        }),
      } as Response);

    renderDialog();

    const bnInput = await screen.findByLabelText(/Business Number/);
    fireEvent.change(bnInput, { target: { value: "22099131" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    const heading = await screen.findByText("Duplicate Business Number");
    expect(heading).toBeTruthy();
    expect(screen.getByText(/Other Corp/)).toBeTruthy();
  });

  it("cancel button on duplicate clears warning and shows form", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockCustomerResponse(),
      } as Response)
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({
          error: "duplicate_business_number",
          existing_customer_id: "other-id",
          existing_customer_name: "Other Corp",
          normalized_business_number: "22099131",
        }),
      } as Response);

    renderDialog();

    const bnInput = await screen.findByLabelText(/Business Number/);
    fireEvent.change(bnInput, { target: { value: "22099131" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    await screen.findByText("Duplicate Business Number");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    // Form should reappear
    expect(screen.getByRole("button", { name: "Save Changes" })).toBeTruthy();
  });

  it("shows server validation errors on 422", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockCustomerResponse(),
      } as Response)
      .mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({
          detail: [{ field: "contact_phone", message: "Phone must be a valid Taiwan phone number." }],
        }),
      } as Response);

    renderDialog();

    const phoneInput = await screen.findByLabelText(/Contact Phone/);
    fireEvent.change(phoneInput, { target: { value: "bad-phone" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    const error = await screen.findByText(/Phone must be a valid Taiwan phone number/);
    expect(error).toBeTruthy();
  });

  it("shows a form-level error and clears submitting when save fails before a response", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockCustomerResponse(),
      } as Response)
      .mockRejectedValueOnce(new Error("network down"));

    renderDialog();

    const nameInput = await screen.findByLabelText(/Company Name/);
    fireEvent.change(nameInput, { target: { value: "Changed" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    expect(
      await screen.findByText("Unable to reach the server. Please try again."),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Save Changes" })).toBeTruthy();
  });

  it("displays Save Changes button, not Create Customer", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockCustomerResponse(),
    } as Response);

    renderDialog();
    await screen.findByLabelText(/Company Name/);
    expect(screen.getByRole("button", { name: "Save Changes" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Create Customer" })).toBeNull();
  });
});
