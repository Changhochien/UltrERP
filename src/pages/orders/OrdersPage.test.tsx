import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const navigateMock = vi.fn();
const permissionMock = vi.hoisted(() => ({
  canWrite: vi.fn<(feature: string) => boolean>(),
}));

vi.mock("react-i18next", () => ({
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

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canWrite: permissionMock.canWrite,
  }),
}));

vi.mock("../../components/layout/PageLayout", () => ({
  PageHeader: ({ title, actions }: { title: string; actions?: React.ReactNode }) => (
    <div>
      <div>{title}</div>
      {actions}
    </div>
  ),
  SectionCard: ({ title, children }: { title: string; children: React.ReactNode }) => (
    <section>
      <h2>{title}</h2>
      {children}
    </section>
  ),
}));

vi.mock("../../components/ui/button", () => ({
  Button: ({ children, onClick, type = "button", variant }: { children: React.ReactNode; onClick?: () => void; type?: "button" | "submit"; variant?: string }) => (
    <button type={type} data-variant={variant} onClick={onClick}>{children}</button>
  ),
}));

vi.mock("../../domain/orders/components/OrderForm", () => ({
  OrderForm: () => <div>order-form</div>,
}));

vi.mock("../../domain/orders/components/OrderList", () => ({
  OrderList: () => <div>order-list</div>,
}));

vi.mock("../../domain/orders/components/OrderDetail", () => ({
  OrderDetail: () => <div>order-detail</div>,
}));

afterEach(() => {
  cleanup();
  navigateMock.mockReset();
  permissionMock.canWrite.mockReset();
});

describe("OrdersPage", () => {
  it("hides the create entrypoint for read-only order roles", async () => {
    permissionMock.canWrite.mockReturnValue(false);
    const { OrdersPage } = await import("./OrdersPage");

    render(
      <MemoryRouter initialEntries={["/orders"]}>
        <Routes>
          <Route path="*" element={<OrdersPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.queryByRole("button", { name: "New Order" })).toBeNull();
    expect(screen.getByText("order-list")).toBeTruthy();
  });

  it("blocks the create route for read-only order roles", async () => {
    permissionMock.canWrite.mockReturnValue(false);
    const { OrdersPage } = await import("./OrdersPage");

    render(
      <MemoryRouter initialEntries={["/orders/new"]}>
        <Routes>
          <Route path="*" element={<OrdersPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.queryByText("order-form")).toBeNull();
    expect(screen.getByText("orders.form.readOnly")).toBeTruthy();
    expect(screen.getByRole("button", { name: "orders.detail.backToList" })).toBeTruthy();
  });
});