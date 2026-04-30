import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { INVOICE_CREATE_ROUTE, ORDER_CREATE_ROUTE } from "../../lib/routes";
import { DashboardPage } from "./DashboardPage";

const navigateMock = vi.hoisted(() => vi.fn());
const permissionState = vi.hoisted(() => ({
  readable: new Set<string>(),
  writable: new Set<string>(),
}));

vi.mock("react-i18next", () => ({
  initReactI18next: {
    type: "3rdParty",
    init: () => undefined,
  },
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../../domain/dashboard/hooks/useDashboard", () => ({
  useRevenueSummary: () => ({ data: null, isLoading: false, error: null }),
}));

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canAccess: (feature: string) => permissionState.readable.has(feature) || permissionState.writable.has(feature),
    canWrite: (feature: string) => permissionState.writable.has(feature),
  }),
}));

vi.mock("../../domain/dashboard/components/RevenueCard", () => ({
  RevenueCard: () => <div>RevenueCard</div>,
}));

vi.mock("../../domain/dashboard/components/TopProductsCard", () => ({
  TopProductsCard: () => <div>TopProductsCard</div>,
}));

vi.mock("../../domain/dashboard/components/LowStockAlertsCard", () => ({
  LowStockAlertsCard: () => <div>LowStockAlertsCard</div>,
}));

vi.mock("../../domain/dashboard/components/VisitorStatsCard", () => ({
  VisitorStatsCard: () => <div>VisitorStatsCard</div>,
}));

afterEach(() => {
  cleanup();
  navigateMock.mockReset();
  permissionState.readable.clear();
  permissionState.writable.clear();
});

describe("DashboardPage", () => {
  it("shows only the actions and cards allowed by permissions", () => {
    permissionState.readable = new Set(["customers", "inventory", "orders"]);
    permissionState.writable = new Set(["orders"]);

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("RevenueCard")).toBeTruthy();
    expect(screen.getByText("VisitorStatsCard")).toBeTruthy();
    expect(screen.getByText("TopProductsCard")).toBeTruthy();
    expect(screen.getByText("LowStockAlertsCard")).toBeTruthy();

    expect(screen.getByText("quickActions.customers")).toBeTruthy();
    expect(screen.getAllByText("quickActions.newOrder")).toHaveLength(2);

    expect(screen.queryByText("quickActions.newInvoice")).toBeNull();
    expect(screen.queryByText("quickActions.admin")).toBeNull();
  });

  it("navigates from the primary quick actions", () => {
    permissionState.writable = new Set(["orders", "invoices"]);

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByText("quickActions.newOrder")[0]!);
    fireEvent.click(screen.getAllByText("quickActions.newInvoice")[0]!);

    expect(navigateMock).toHaveBeenNthCalledWith(1, ORDER_CREATE_ROUTE);
    expect(navigateMock).toHaveBeenNthCalledWith(2, INVOICE_CREATE_ROUTE);
  });
});