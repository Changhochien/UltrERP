import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SuppliersPage } from "./SuppliersPage";

const mocks = vi.hoisted(() => ({
  canWrite: vi.fn(() => true),
  navigate: vi.fn(),
  reload: vi.fn().mockResolvedValue(undefined),
  createSupplier: vi.fn(),
  setSupplierStatus: vi.fn(),
}));

const SUPPLIER = {
  id: "supplier-1",
  tenant_id: "tenant-1",
  name: "Acme Supply",
  contact_email: "acme@example.com",
  phone: "555-0100",
  address: "123 Supply St",
  default_lead_time_days: 7,
  default_currency_code: "TWD",
  payment_terms_template_id: "terms-net-30",
  is_active: true,
  created_at: "2026-04-01T00:00:00Z",
};

vi.mock("../../hooks/useCommercialDefaultsOptions", () => ({
  useCommercialDefaultsOptions: () => ({
    currencies: [{ id: "currency-twd", code: "TWD", is_base_currency: true }],
    paymentTerms: [{ id: "terms-net-30", template_name: "Net 30" }],
    loading: false,
    error: null,
    refresh: vi.fn(),
  }),
}));

vi.mock("react-i18next", () => ({
  useTranslation: (_ns?: string, options?: { keyPrefix?: string }) => ({
    t: (key: string, vars?: Record<string, unknown>) => {
      if (key === "total" && vars?.count != null) {
        return `${vars.count} suppliers`;
      }
      return options?.keyPrefix ? `${options.keyPrefix}.${key}` : key;
    },
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mocks.navigate,
  };
});

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canWrite: mocks.canWrite,
  }),
}));

vi.mock("../../domain/inventory/hooks/useSuppliers", () => ({
  useSuppliers: () => ({
    suppliers: [SUPPLIER],
    total: 1,
    loading: false,
    error: null,
    reload: mocks.reload,
  }),
}));

vi.mock("../../lib/api/inventory", () => ({
  createSupplier: (...args: unknown[]) => mocks.createSupplier(...args),
  setSupplierStatus: (...args: unknown[]) => mocks.setSupplierStatus(...args),
}));

beforeEach(() => {
  mocks.createSupplier.mockResolvedValue({
    ok: true,
    data: { ...SUPPLIER, id: "supplier-2", name: "Beta Supply" },
  });
  mocks.setSupplierStatus.mockResolvedValue({
    ok: true,
    data: { ...SUPPLIER, is_active: false },
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SuppliersPage", () => {
  it("creates a supplier from the management page", async () => {
    render(<SuppliersPage />);

    fireEvent.change(screen.getByLabelText(/supplier name/i), {
      target: { value: "Beta Supply" },
    });
    fireEvent.click(screen.getByRole("button", { name: "save" }));

    await waitFor(() => {
      expect(mocks.createSupplier).toHaveBeenCalledWith({
        name: "Beta Supply",
        contact_email: undefined,
        phone: undefined,
        address: undefined,
        default_lead_time_days: undefined,
        default_currency_code: null,
        payment_terms_template_id: null,
      });
    });
  });

  it("deactivates a supplier from the directory", async () => {
    render(<SuppliersPage />);

    fireEvent.click(screen.getByRole("button", { name: "deactivate" }));

    await waitFor(() => {
      expect(mocks.setSupplierStatus).toHaveBeenCalledWith("supplier-1", false);
    });
  });
});