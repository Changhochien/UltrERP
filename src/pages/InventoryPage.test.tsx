import * as React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const permissionMock = vi.hoisted(() => ({
  canWrite: vi.fn<(feature: string) => boolean>(),
}));

const inventoryPageState = vi.hoisted(() => ({
  lastProductSearchValue: "",
  lastHideToolbarSearch: false,
  stockAdjustmentMountId: 0,
  createProductMountId: 0,
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canWrite: permissionMock.canWrite,
  }),
}));

vi.mock("../domain/inventory/context/WarehouseContext", () => ({
  WarehouseProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useWarehouseContext: () => ({
    selectedWarehouse: null,
    setSelectedWarehouse: vi.fn(),
  }),
}));

vi.mock("../domain/inventory/components/WarehouseSelector", () => ({
  WarehouseSelector: () => <div>warehouse-selector</div>,
}));

vi.mock("../domain/inventory/components/ProductTable", () => ({
  ProductTable: ({ searchValue, hideToolbarSearch }: { searchValue?: string; hideToolbarSearch?: boolean }) => {
    inventoryPageState.lastProductSearchValue = searchValue ?? "";
    inventoryPageState.lastHideToolbarSearch = Boolean(hideToolbarSearch);

    return <div>product-table</div>;
  },
}));

vi.mock("../domain/inventory/components/CommandBar", () => ({
  CommandBar: ({
    onSearch,
    onAdjustStock,
  }: {
    onSearch?: (value: string) => void;
    onAdjustStock?: () => void;
  }) => (
    <div>
      <button type="button" onClick={() => onSearch?.("steel bolt")}>command-bar</button>
      <button type="button" onClick={() => onAdjustStock?.()}>open-adjust-stock</button>
    </div>
  ),
}));

vi.mock("../domain/inventory/components/AlertFeed", () => ({
  AlertFeed: () => <div>alert-panel</div>,
}));

vi.mock("../domain/inventory/components/MetricCards", () => ({
  MetricCards: () => <div>metric-cards</div>,
}));

vi.mock("../components/layout/PageLayout", () => ({
  PageHeader: ({ title, actions }: { title: string; actions?: React.ReactNode }) => (
    <div>
      <div>{title}</div>
      {actions}
    </div>
  ),
  PageTabs: () => null,
}));

vi.mock("../domain/inventory/components/ProductDetailDrawer", () => ({
  ProductDetailDrawer: () => null,
}));

vi.mock("../domain/inventory/components/CreateProductForm", () => ({
  CreateProductForm: ({ onCancel }: { onCancel?: () => void }) => {
    const [mountId] = React.useState(() => {
      inventoryPageState.createProductMountId += 1;
      return inventoryPageState.createProductMountId;
    });

    return (
      <div>
        <div>{`create-product-form-${mountId}`}</div>
        <button type="button" onClick={() => onCancel?.()}>cancel-create-product</button>
      </div>
    );
  },
}));

vi.mock("../domain/inventory/components/StockAdjustmentForm", () => ({
  StockAdjustmentForm: () => {
    const [mountId] = React.useState(() => {
      inventoryPageState.stockAdjustmentMountId += 1;
      return inventoryPageState.stockAdjustmentMountId;
    });

    return <div>{`stock-adjustment-form-${mountId}`}</div>;
  },
}));

vi.mock("../domain/inventory/components/StockTransferForm", () => ({
  StockTransferForm: () => null,
}));

vi.mock("../domain/inventory/components/ReorderPointAdmin", () => ({
  ReorderPointAdmin: () => <div>reorder-point-admin</div>,
}));

afterEach(() => {
  cleanup();
  permissionMock.canWrite.mockReset();
  inventoryPageState.lastProductSearchValue = "";
  inventoryPageState.lastHideToolbarSearch = false;
  inventoryPageState.stockAdjustmentMountId = 0;
  inventoryPageState.createProductMountId = 0;
});

describe("InventoryPage", () => {
  it("shows reorder point admin for inventory write roles", async () => {
    permissionMock.canWrite.mockImplementation((feature) => feature === "inventory");
    const { InventoryPage } = await import("./InventoryPage");

    render(
      <MemoryRouter>
        <InventoryPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("reorder-point-admin")).toBeTruthy();
  });

  it("hides reorder point admin for read-only inventory roles", async () => {
    permissionMock.canWrite.mockReturnValue(false);
    const { InventoryPage } = await import("./InventoryPage");

    render(
      <MemoryRouter>
        <InventoryPage />
      </MemoryRouter>,
    );

    expect(screen.queryByText("reorder-point-admin")).toBeNull();
  });

  it("wires the command bar search into the live product table", async () => {
    permissionMock.canWrite.mockImplementation((feature) => feature === "inventory");
    const { InventoryPage } = await import("./InventoryPage");

    render(
      <MemoryRouter>
        <InventoryPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("alert-panel")).toBeTruthy();
    expect(inventoryPageState.lastHideToolbarSearch).toBe(true);
    expect(inventoryPageState.lastProductSearchValue).toBe("");

    fireEvent.click(screen.getByRole("button", { name: "command-bar" }));

    expect(inventoryPageState.lastProductSearchValue).toBe("steel bolt");
  });

  it("opens the stock adjustment dialog from the live command bar", async () => {
    permissionMock.canWrite.mockImplementation((feature) => feature === "inventory");
    const { InventoryPage } = await import("./InventoryPage");

    render(
      <MemoryRouter>
        <InventoryPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "open-adjust-stock" }));

    const firstInstance = screen.getByText(/stock-adjustment-form-/).textContent;

    expect(firstInstance).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    fireEvent.click(screen.getByRole("button", { name: "open-adjust-stock" }));

    expect(screen.getByText(/stock-adjustment-form-/).textContent).not.toBe(firstInstance);
  });

  it("reopens add product with a fresh form instance", async () => {
    permissionMock.canWrite.mockImplementation((feature) => feature === "inventory");
    const { InventoryPage } = await import("./InventoryPage");

    render(
      <MemoryRouter>
        <InventoryPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "inventory.page.addProduct" }));

    const firstInstance = screen.getByText(/create-product-form-/).textContent;

    expect(firstInstance).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "cancel-create-product" }));
    fireEvent.click(screen.getByRole("button", { name: "inventory.page.addProduct" }));

    expect(screen.getByText(/create-product-form-/).textContent).not.toBe(firstInstance);
  });
});
