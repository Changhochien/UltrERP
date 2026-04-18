import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SupplierForm } from "../../domain/inventory/components/SupplierForm";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("SupplierForm", () => {
  it("blocks submit when name is blank", async () => {
    const onSubmit = vi.fn();

    render(
      <SupplierForm
        submitLabel="Save Supplier"
        submittingLabel="Saving…"
        onSubmit={onSubmit}
        onSuccess={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Save Supplier" }));

    expect(await screen.findByText("Supplier name is required")).toBeTruthy();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a trimmed payload", async () => {
    const onSubmit = vi.fn().mockResolvedValue({
      ok: true,
      supplier: {
        id: "supplier-1",
        tenant_id: "tenant-1",
        name: "Acme Supply",
        contact_email: "acme@example.com",
        phone: "555-0100",
        address: "123 Supply St",
        default_lead_time_days: 7,
        is_active: true,
        created_at: "2026-04-01T00:00:00Z",
      },
    });

    render(
      <SupplierForm
        submitLabel="Save Supplier"
        submittingLabel="Saving…"
        onSubmit={onSubmit}
        onSuccess={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText(/supplier name/i), {
      target: { value: "  Acme Supply  " },
    });
    fireEvent.change(screen.getByLabelText(/contact email/i), {
      target: { value: "  acme@example.com  " },
    });
    fireEvent.change(screen.getByLabelText(/default lead time/i), {
      target: { value: "7" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save Supplier" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        name: "Acme Supply",
        contact_email: "acme@example.com",
        phone: undefined,
        address: undefined,
        default_lead_time_days: 7,
      });
    });
  });
});