import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SupplierCombobox } from "../../domain/inventory/components/SupplierCombobox";
import { fetchSuppliers } from "../../lib/api/inventory";

vi.mock("../../lib/api/inventory", () => ({
  fetchSuppliers: vi.fn(),
}));

const SUPPLIER = {
  id: "supplier-1",
  tenant_id: "tenant-1",
  name: "Acme Supply",
  contact_email: "acme@example.com",
  phone: "555-0100",
  address: "123 Supply St",
  default_lead_time_days: 7,
  is_active: true,
  created_at: "2026-04-01T00:00:00Z",
};

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", ResizeObserverMock);
  vi.mocked(fetchSuppliers).mockResolvedValue({
    ok: true,
    data: {
      items: [SUPPLIER],
      total: 1,
    },
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe("SupplierCombobox", () => {
  it("returns the selected supplier id", async () => {
    const onChange = vi.fn();

    render(
      <SupplierCombobox
        value=""
        onChange={onChange}
        placeholder="Search supplier…"
      />,
    );

    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(await screen.findByText("Acme Supply"));

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith("supplier-1");
    });
  });
});