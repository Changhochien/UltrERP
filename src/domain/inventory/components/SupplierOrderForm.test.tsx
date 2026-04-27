import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { SupplierOrderForm } from "./SupplierOrderForm";

const createSupplierOrderMock = vi.fn();
const fetchProductSupplierMock = vi.fn();

vi.mock("../../../lib/api/inventory", () => ({
  fetchProductSupplier: (...args: unknown[]) => fetchProductSupplierMock(...args),
}));

vi.mock("../hooks/useSupplierOrders", () => ({
  useCreateSupplierOrder: () => ({
    create: createSupplierOrderMock,
    submitting: false,
    error: null,
  }),
}));

vi.mock("./SupplierCombobox", () => ({
  SupplierCombobox: ({ value, onChange, ariaLabel }: { value: string; onChange: (value: string) => void; ariaLabel?: string }) => (
    <input aria-label={ariaLabel ?? "Supplier"} value={value} onChange={(event) => onChange(event.target.value)} />
  ),
}));

vi.mock("../hooks/useWarehouses", () => ({
  useWarehouses: () => ({
    warehouses: [{ id: "wh-1", name: "Main Warehouse" }],
    loading: false,
  }),
}));

vi.mock("@/domain/inventory/components/ProductCombobox", () => ({
  ProductCombobox: ({ value, onChange, ariaLabel }: { value: string; onChange: (value: string) => void; ariaLabel?: string }) => (
    <input aria-label={ariaLabel ?? "Product"} value={value} onChange={(event) => onChange(event.target.value)} />
  ),
}));

afterEach(() => {
  cleanup();
  createSupplierOrderMock.mockReset();
  fetchProductSupplierMock.mockReset();
  vi.restoreAllMocks();
});

describe("SupplierOrderForm", () => {
  it("preserves an explicit zero unit price when submitting", async () => {
    createSupplierOrderMock.mockResolvedValue({ id: "so-1" });

    render(<SupplierOrderForm onCreated={vi.fn()} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Supplier"), {
      target: { value: "sup-1" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 product"), {
      target: { value: "prod-1" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 warehouse"), {
      target: { value: "wh-1" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 unit cost"), {
      target: { value: "0" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create Order" }));

    await waitFor(() => {
      expect(createSupplierOrderMock).toHaveBeenCalledTimes(1);
    });

    expect(createSupplierOrderMock).toHaveBeenCalledWith({
      supplier_id: "sup-1",
      order_date: expect.any(String),
      expected_arrival_date: undefined,
      lines: [
        {
          product_id: "prod-1",
          warehouse_id: "wh-1",
          quantity_ordered: 1,
          unit_price: 0,
        },
      ],
    });
  });

  it("hydrates prefilled supplier draft values", () => {
    render(
      <SupplierOrderForm
        initialSupplierId="sup-9"
        initialLines={[
          {
            product_id: "prod-9",
            warehouse_id: "wh-1",
            quantity: 6,
            unit_cost: "12.50",
          },
        ]}
        onCreated={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect((screen.getByLabelText("Supplier") as HTMLInputElement).value).toBe("sup-9");
    expect((screen.getByLabelText("Line 1 product") as HTMLInputElement).value).toBe("prod-9");
    expect((screen.getByLabelText("Line 1 warehouse") as HTMLSelectElement).value).toBe("wh-1");
    expect((screen.getByLabelText("Line 1 quantity") as HTMLInputElement).value).toBe("6");
    expect((screen.getByLabelText("Line 1 unit cost") as HTMLInputElement).value).toBe("12.50");
  });

  it("prefills the supplier when one product resolves to a single default", async () => {
    fetchProductSupplierMock.mockResolvedValue({
      ok: true,
      data: {
        supplier_id: "sup-1",
        name: "Acme Supply",
        unit_cost: 11.5,
        default_lead_time_days: 5,
      },
    });

    render(
      <SupplierOrderForm
        initialLines={[{ product_id: "prod-1", warehouse_id: "wh-1", quantity: 4 }]}
        onCreated={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect((screen.getByLabelText("Supplier") as HTMLInputElement).value).toBe("sup-1");
    });
  });

  it("leaves supplier blank and shows a conflict when defaults disagree", async () => {
    fetchProductSupplierMock.mockImplementation(async (productId: string) => {
      if (productId === "prod-1") {
        return {
          ok: true,
          data: {
            supplier_id: "sup-1",
            name: "Acme Supply",
            unit_cost: 11.5,
            default_lead_time_days: 5,
          },
        };
      }

      return {
        ok: true,
        data: {
          supplier_id: "sup-2",
          name: "Beta Supply",
          unit_cost: 9.75,
          default_lead_time_days: 7,
        },
      };
    });

    render(
      <SupplierOrderForm
        initialLines={[
          { product_id: "prod-1", warehouse_id: "wh-1", quantity: 2 },
          { product_id: "prod-2", warehouse_id: "wh-1", quantity: 3 },
        ]}
        onCreated={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect((screen.getByLabelText("Supplier") as HTMLInputElement).value).toBe("");
    });
    expect(
      await screen.findByText("Selected products have different default suppliers. Choose one manually."),
    ).toBeTruthy();
  });
});