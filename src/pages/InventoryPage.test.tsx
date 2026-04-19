import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const permissionMock = vi.hoisted(() => ({
  canWrite: vi.fn<(feature: string) => boolean>(),
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
  ProductTable: () => <div>product-table</div>,
}));

vi.mock("../domain/inventory/components/AlertPanel", () => ({
  AlertPanel: () => <div>alert-panel</div>,
}));

vi.mock("../domain/inventory/components/MetricCards", () => ({
  MetricCards: () => <div>metric-cards</div>,
}));

vi.mock("../components/layout/PageLayout", () => ({
  PageHeader: ({ title }: { title: string }) => <div>{title}</div>,
  PageTabs: () => null,
}));

vi.mock("../domain/inventory/components/ProductDetailDrawer", () => ({
  ProductDetailDrawer: () => null,
}));

vi.mock("../domain/inventory/components/StockAdjustmentForm", () => ({
  StockAdjustmentForm: () => null,
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
});
