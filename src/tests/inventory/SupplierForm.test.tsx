import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SupplierForm } from "../../domain/inventory/components/SupplierForm";

describe("SupplierForm", () => {
  it("submits the normalized supplier payload through the shared schema", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ ok: true, supplier: { id: "sup-1" } });
    const onSuccess = vi.fn();

    render(
      <SupplierForm
        onSubmit={onSubmit}
        onSuccess={onSuccess}
        submitLabel="Save Supplier"
        submittingLabel="Saving..."
      />,
    );

    fireEvent.change(screen.getByLabelText(/Supplier Name/i), { target: { value: "  Acme Supply  " } });
    fireEvent.change(screen.getByLabelText(/Contact Email/i), { target: { value: "  SALES@ACME.COM  " } });
    fireEvent.change(screen.getByLabelText(/^Phone$/i), { target: { value: " 02-1234-5678 " } });
    fireEvent.change(screen.getByLabelText(/^Address$/i), { target: { value: " 1 Harbor Road " } });
    fireEvent.change(screen.getByLabelText(/Default Lead Time/i), { target: { value: "7" } });

    fireEvent.click(screen.getByRole("button", { name: "Save Supplier" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        name: "Acme Supply",
        contact_email: "SALES@ACME.COM",
        phone: "02-1234-5678",
        address: "1 Harbor Road",
        default_lead_time_days: 7,
      });
    });
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("blocks submit when the lead time is negative", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ ok: true, supplier: { id: "sup-1" } });

    render(
      <SupplierForm
        onSubmit={onSubmit}
        onSuccess={vi.fn()}
        submitLabel="Save Supplier"
        submittingLabel="Saving..."
      />,
    );

    fireEvent.change(screen.getByLabelText(/Supplier Name/i), { target: { value: "Acme Supply" } });
    fireEvent.change(screen.getByLabelText(/Default Lead Time/i), { target: { value: "-1" } });

    fireEvent.click(screen.getByRole("button", { name: "Save Supplier" }));

    await waitFor(() => {
      expect(screen.getByText("Lead time must be zero or greater")).toBeTruthy();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });
});