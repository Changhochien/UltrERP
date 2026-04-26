import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SupplierDetailPage } from "./SupplierDetailPage";

const mocks = vi.hoisted(() => ({
  canWrite: vi.fn(() => true),
  navigate: vi.fn(),
  reload: vi.fn().mockResolvedValue(undefined),
  updateSupplier: vi.fn(),
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
    t: (key: string) => (options?.keyPrefix ? `${options.keyPrefix}.${key}` : key),
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mocks.navigate,
    useParams: () => ({ supplierId: "supplier-1" }),
  };
});

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canWrite: mocks.canWrite,
  }),
}));

vi.mock("../../domain/inventory/hooks/useSuppliers", () => ({
  useSupplierDetail: () => ({
    supplier: SUPPLIER,
    loading: false,
    error: null,
    reload: mocks.reload,
  }),
}));

vi.mock("../../lib/api/inventory", () => ({
  setSupplierStatus: vi.fn(),
  updateSupplier: (...args: unknown[]) => mocks.updateSupplier(...args),
}));

beforeEach(() => {
  mocks.updateSupplier.mockResolvedValue({ ok: true, data: { ...SUPPLIER, name: "Beta Supply" } });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SupplierDetailPage", () => {
  it("updates supplier details from the detail page", async () => {
    render(
      <MemoryRouter>
        <SupplierDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "routes.inventorySuppliers.label" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "routes.inventorySuppliers.label" })).toBeTruthy();

    fireEvent.change(screen.getByLabelText(/supplier name/i), {
      target: { value: "Beta Supply" },
    });
    fireEvent.click(screen.getByRole("button", { name: "save" }));

    await waitFor(() => {
      expect(mocks.updateSupplier).toHaveBeenCalledWith("supplier-1", {
        name: "Beta Supply",
        contact_email: "acme@example.com",
        phone: "555-0100",
        address: "123 Supply St",
        default_lead_time_days: 7,
        default_currency_code: "TWD",
        payment_terms_template_id: "terms-net-30",
      });
    });
  });
});