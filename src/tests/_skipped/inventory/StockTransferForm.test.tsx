import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { StockTransferForm } from "../../domain/inventory/components/StockTransferForm";

const mocks = vi.hoisted(() => ({
  createTransfer: vi.fn(),
  onSuccess: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: (_ns?: string, options?: { keyPrefix?: string }) => ({
    t: (key: string, vars?: Record<string, unknown>) => {
      if (options?.keyPrefix === "inventory.transferForm" && key === "success") {
        return `transfer-success-${vars?.transferId}`;
      }
      if (options?.keyPrefix === "inventory.transferForm" && key === "confirmDescription") {
        return `confirm-${vars?.quantity}-${vars?.fromWarehouse}-${vars?.toWarehouse}`;
      }
      return options?.keyPrefix ? `${options.keyPrefix}.${key}` : key;
    },
  }),
}));

vi.mock("@/domain/inventory/hooks/useWarehouses", () => ({
  useWarehouses: () => ({
    warehouses: [
      { id: "wh-1", name: "Main Warehouse", code: "MAIN" },
      { id: "wh-2", name: "Outlet Warehouse", code: "OUTLET" },
    ],
    loading: false,
    error: null,
  }),
}));

vi.mock("@/domain/inventory/components/ProductCombobox", () => ({
  ProductCombobox: ({ value, onChange }: { value: string; onChange: (value: string) => void }) => (
    <button type="button" onClick={() => onChange("product-1")}>
      {value || "pick-product"}
    </button>
  ),
}));

vi.mock("@/lib/api/inventory", () => ({
  createTransfer: (...args: unknown[]) => mocks.createTransfer(...args),
}));

beforeEach(() => {
  mocks.createTransfer.mockResolvedValue({
    ok: true,
    data: {
      id: "transfer-1",
      tenant_id: "tenant-1",
      product_id: "product-1",
      from_warehouse_id: "wh-1",
      to_warehouse_id: "wh-2",
      quantity: 4,
      actor_id: "system",
      notes: "Rebalance",
      created_at: "2026-04-20T12:00:00Z",
    },
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("StockTransferForm", () => {
  it("submits a transfer and notifies the parent on success", async () => {
    render(
      <StockTransferForm
        defaultFromWarehouseId="wh-1"
        onSuccess={mocks.onSuccess}
      />,
    );

    fireEvent.change(screen.getByLabelText("inventory.transferForm.toWarehouse"), {
      target: { value: "wh-2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "pick-product" }));
    fireEvent.change(screen.getByLabelText("inventory.transferForm.quantity"), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByLabelText("inventory.transferForm.notes"), {
      target: { value: "Rebalance" },
    });

    fireEvent.click(screen.getByRole("button", { name: "inventory.transferForm.submit" }));
    fireEvent.click(screen.getByRole("button", { name: "inventory.transferForm.confirm" }));

    await waitFor(() => {
      expect(mocks.createTransfer).toHaveBeenCalledWith({
        from_warehouse_id: "wh-1",
        to_warehouse_id: "wh-2",
        product_id: "product-1",
        quantity: 4,
        notes: "Rebalance",
      });
    });
    await waitFor(() => {
      expect(mocks.onSuccess).toHaveBeenCalledWith(expect.objectContaining({ id: "transfer-1" }));
    });
    expect(screen.getByText("transfer-success-transfer-1")).toBeTruthy();
  });

  it("shows transfer errors without calling the success callback", async () => {
    mocks.createTransfer.mockResolvedValueOnce({
      ok: false,
      error: "Insufficient stock: 0 units available",
    });

    render(
      <StockTransferForm
        defaultFromWarehouseId="wh-1"
        onSuccess={mocks.onSuccess}
      />,
    );

    fireEvent.change(screen.getByLabelText("inventory.transferForm.toWarehouse"), {
      target: { value: "wh-2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "pick-product" }));
    fireEvent.click(screen.getByRole("button", { name: "inventory.transferForm.submit" }));
    fireEvent.click(screen.getByRole("button", { name: "inventory.transferForm.confirm" }));

    await waitFor(() => {
      expect(screen.getByText("Insufficient stock: 0 units available")).toBeTruthy();
    });
    expect(mocks.onSuccess).not.toHaveBeenCalled();
  });

  it("blocks fractional quantities before submission", async () => {
    render(
      <StockTransferForm
        defaultFromWarehouseId="wh-1"
        onSuccess={mocks.onSuccess}
      />,
    );

    fireEvent.change(screen.getByLabelText("inventory.transferForm.toWarehouse"), {
      target: { value: "wh-2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "pick-product" }));
    fireEvent.change(screen.getByLabelText("inventory.transferForm.quantity"), {
      target: { value: "1.5" },
    });

    expect(screen.getByText("inventory.transferForm.quantityInteger")).toBeTruthy();
    expect(
      (screen.getByRole("button", { name: "inventory.transferForm.submit" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(mocks.createTransfer).not.toHaveBeenCalled();
  });
});