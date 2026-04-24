import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const createMock = vi.hoisted(() => vi.fn());
const toastMock = vi.hoisted(() => ({ toast: vi.fn() }));
const fetchSupplierMock = vi.hoisted(() => vi.fn());
const checkSupplierRFQControlsMock = vi.hoisted(() => vi.fn());

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../components/layout/PageLayout", () => ({
  PageHeader: ({ title, description }: { title: string; description?: string }) => (
    <div>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  ),
}));

vi.mock("../../components/ui/button", () => ({
  Button: ({
    children,
    onClick,
    disabled,
    type = "button",
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    type?: "button" | "submit";
  }) => (
    <button type={type} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  ),
}));

vi.mock("../../components/ui/input", () => ({
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}));

vi.mock("../../hooks/useToast", () => ({
  useToast: () => toastMock,
}));

vi.mock("../../domain/procurement/hooks/useRFQ", () => ({
  useCreateRFQ: () => ({
    create: createMock,
    loading: false,
    error: null,
  }),
}));

vi.mock("../../domain/inventory/components/SupplierCombobox", () => ({
  SupplierCombobox: ({
    value,
    onChange,
    onClear,
    ariaLabel,
  }: {
    value: string;
    onChange: (supplierId: string) => void;
    onClear?: () => void;
    ariaLabel?: string;
  }) => (
    <div>
      <button type="button" aria-label={ariaLabel} onClick={() => onChange("sup-1")}>
        {value || "select supplier"}
      </button>
      {value ? (
        <button type="button" onClick={onClear}>
          clear supplier
        </button>
      ) : null}
    </div>
  ),
}));

vi.mock("../../lib/api/inventory", () => ({
  fetchSupplier: fetchSupplierMock,
}));

vi.mock("../../lib/api/procurement", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api/procurement")>("../../lib/api/procurement");
  return {
    ...actual,
    checkSupplierRFQControls: checkSupplierRFQControlsMock,
  };
});

afterEach(() => {
  cleanup();
  createMock.mockReset();
  toastMock.toast.mockReset();
  fetchSupplierMock.mockReset();
  checkSupplierRFQControlsMock.mockReset();
});

describe("CreateRFQPage", () => {
  it("disables saving when a selected supplier is blocked for RFQs", async () => {
    fetchSupplierMock.mockResolvedValue({
      ok: true,
      data: {
        id: "sup-1",
        name: "Blocked Supplier",
        contact_email: "blocked@example.com",
      },
    });
    checkSupplierRFQControlsMock.mockResolvedValue({
      is_blocked: true,
      is_warned: false,
      reason: "Supplier is on hold",
      supplier_name: "Blocked Supplier",
      controls: {},
    });

    const { default: CreateRFQPage } = await import("./CreateRFQPage");

    render(
      <MemoryRouter>
        <CreateRFQPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "procurement.rfq.fields.supplierName" }));

    await waitFor(() => {
      expect(screen.getByText("Supplier is on hold")).toBeTruthy();
    });

    expect(
      (screen.getByRole("button", { name: "procurement.rfq.save" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(createMock).not.toHaveBeenCalled();
  });

  it("creates an RFQ with the resolved supplier id and master data", async () => {
    fetchSupplierMock.mockResolvedValue({
      ok: true,
      data: {
        id: "sup-1",
        name: "Approved Supplier",
        contact_email: "approved@example.com",
      },
    });
    checkSupplierRFQControlsMock.mockResolvedValue({
      is_blocked: false,
      is_warned: false,
      reason: "",
      supplier_name: "Approved Supplier",
      controls: {},
    });
    createMock.mockResolvedValue({ id: "rfq-123" });

    const { default: CreateRFQPage } = await import("./CreateRFQPage");

    render(
      <MemoryRouter>
        <CreateRFQPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "procurement.rfq.fields.supplierName" }));

    await waitFor(() => {
      expect(fetchSupplierMock).toHaveBeenCalledWith("sup-1");
      expect(checkSupplierRFQControlsMock).toHaveBeenCalledWith("sup-1");
    });

    fireEvent.change(screen.getByPlaceholderText("procurement.rfq.fields.companyPlaceholder"), {
      target: { value: "UltrERP Taiwan" },
    });
    fireEvent.change(screen.getByPlaceholderText("procurement.rfq.fields.itemNamePlaceholder"), {
      target: { value: "Industrial Bearing" },
    });
    fireEvent.click(screen.getByRole("button", { name: "procurement.rfq.save" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith(
        expect.objectContaining({
          company: "UltrERP Taiwan",
          suppliers: [
            expect.objectContaining({
              supplier_id: "sup-1",
              supplier_name: "Approved Supplier",
              contact_email: "approved@example.com",
            }),
          ],
        }),
      );
    });
  });
});