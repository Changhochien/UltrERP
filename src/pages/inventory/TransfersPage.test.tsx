import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { TransfersPage } from "./TransfersPage";

const mocks = vi.hoisted(() => ({
  canWrite: vi.fn(() => true),
  navigate: vi.fn(),
  fetchTransferDetail: vi.fn(),
  fetchTransferHistory: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: (_ns?: string, options?: { keyPrefix?: string }) => ({
    t: (key: string, vars?: Record<string, unknown>) => {
      if (options?.keyPrefix === "inventory.transfersPage" && key === "historyCount") {
        return `${vars?.count} transfers`;
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

vi.mock("@/hooks/usePermissions", () => ({
  usePermissions: () => ({
    canWrite: mocks.canWrite,
  }),
}));

vi.mock("../../domain/inventory/hooks/useWarehouses", () => ({
  useWarehouses: () => ({
    warehouses: [
      { id: "warehouse-1", name: "Main Warehouse", code: "MAIN" },
      { id: "warehouse-2", name: "Outlet Warehouse", code: "OUTLET" },
    ],
    loading: false,
  }),
}));

vi.mock("@/components/products/ProductCombobox", () => ({
  ProductCombobox: ({ value }: { value: string }) => <div>{value || "product-filter"}</div>,
}));

vi.mock("../../domain/inventory/components/StockTransferForm", () => ({
  StockTransferForm: ({ onSuccess }: { onSuccess?: (transfer: { id: string }) => void }) => (
    <button type="button" onClick={() => onSuccess?.({ id: "transfer-2" })}>
      complete-transfer
    </button>
  ),
}));

vi.mock("@/lib/api/inventory", () => ({
  fetchTransferDetail: (...args: unknown[]) => mocks.fetchTransferDetail(...args),
  fetchTransferHistory: (...args: unknown[]) => mocks.fetchTransferHistory(...args),
}));

beforeEach(() => {
  mocks.fetchTransferHistory.mockResolvedValue({
    ok: true,
    data: {
      items: [
        {
          id: "transfer-1",
          tenant_id: "tenant-1",
          product_id: "product-1",
          product_code: "SKU-1",
          product_name: "Widget",
          from_warehouse_id: "warehouse-1",
          from_warehouse_name: "Main Warehouse",
          from_warehouse_code: "MAIN",
          to_warehouse_id: "warehouse-2",
          to_warehouse_name: "Outlet Warehouse",
          to_warehouse_code: "OUTLET",
          quantity: 5,
          actor_id: "owner@example.com",
          notes: "Floor rebalance",
          created_at: "2026-04-20T12:00:00Z",
        },
      ],
      total: 1,
    },
  });
  mocks.fetchTransferDetail.mockResolvedValue({
    ok: true,
    data: {
      id: "transfer-1",
      tenant_id: "tenant-1",
      product_id: "product-1",
      product_code: "SKU-1",
      product_name: "Widget",
      from_warehouse_id: "warehouse-1",
      from_warehouse_name: "Main Warehouse",
      from_warehouse_code: "MAIN",
      to_warehouse_id: "warehouse-2",
      to_warehouse_name: "Outlet Warehouse",
      to_warehouse_code: "OUTLET",
      quantity: 5,
      actor_id: "owner@example.com",
      notes: "Floor rebalance",
      created_at: "2026-04-20T12:00:00Z",
    },
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("TransfersPage", () => {
  it("renders transfer history rows and shows detail metadata", async () => {
    render(
      <MemoryRouter initialEntries={["/inventory/transfers?productId=product-1"]}>
        <TransfersPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Widget")).toBeTruthy();
    expect(screen.getByText("owner@example.com")).toBeTruthy();
    expect(screen.getByText("Floor rebalance")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "inventory.transfersPage.viewDetails" }));

    await waitFor(() => {
      expect(mocks.fetchTransferDetail).toHaveBeenCalledWith("transfer-1");
    });
    expect(await screen.findByText("inventory.transfersPage.detail.title")).toBeTruthy();
    expect(screen.getAllByText("owner@example.com").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Floor rebalance").length).toBeGreaterThan(0);
  });

  it("refreshes transfer history after the transfer form reports success", async () => {
    render(
      <MemoryRouter initialEntries={["/inventory/transfers"]}>
        <TransfersPage />
      </MemoryRouter>,
    );

    await screen.findByText("Widget");
    fireEvent.click(screen.getByRole("button", { name: "complete-transfer" }));

    await waitFor(() => {
      expect(mocks.fetchTransferHistory).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(mocks.fetchTransferDetail).toHaveBeenCalledWith("transfer-2");
    });
  });
});