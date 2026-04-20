import "../helpers/i18n";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";

import { OrderDetail } from "../../domain/orders/components/OrderDetail";
import { OrderList } from "../../domain/orders/components/OrderList";
import { ToastProvider } from "../../providers/ToastProvider";

const permissionMock = vi.hoisted(() => ({
  canWrite: vi.fn<(feature: string) => boolean>(),
}));

let detailOrder = {
  id: "order-1",
  tenant_id: "tenant-1",
  customer_id: "customer-1",
  customer_name: "Test Corp",
  order_number: "ORD-READY-001",
  status: "confirmed",
  payment_terms_code: "NET_30",
  payment_terms_days: 30,
  subtotal_amount: "1000.00",
  discount_amount: "0.00",
  discount_percent: "0.00",
  tax_amount: "50.00",
  total_amount: "1050.00",
  sales_team: [
    {
      sales_person: "Alice Chen",
      allocated_percentage: "60.00",
      commission_rate: "5.00",
      allocated_amount: "30.00",
    },
    {
      sales_person: "Bob Lin",
      allocated_percentage: "40.00",
      commission_rate: "2.50",
      allocated_amount: "10.00",
    },
  ],
  total_commission: "40.00",
  invoice_id: "invoice-1",
  invoice_number: "AA00000001",
  invoice_payment_status: "unpaid",
  notes: null,
  created_by: "system",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  confirmed_at: "2026-01-01T01:00:00Z",
  execution: {
    commercial_status: "committed",
    fulfillment_status: "ready_to_ship",
    billing_status: "unpaid",
    reservation_status: "reserved",
    ready_to_ship: true,
    has_backorder: false,
    backorder_line_count: 0,
  },
  lines: [
    {
      id: "line-1",
      product_id: "product-1",
      line_number: 1,
      quantity: "10",
      list_unit_price: "100.00",
      unit_price: "100.00",
      discount_amount: "0.00",
      tax_policy_code: "standard",
      tax_type: 1,
      tax_rate: "0.0500",
      tax_amount: "50.00",
      subtotal_amount: "1000.00",
      total_amount: "1050.00",
      description: "Widget A",
      available_stock_snapshot: 100,
      backorder_note: null,
    },
  ],
};

let listItems = [
  {
    id: "order-pending",
    order_number: "ORD-PENDING-001",
    status: "pending",
    customer_id: "customer-1",
    total_amount: "420.00",
    sales_team: [],
    total_commission: "0.00",
    invoice_number: null,
    invoice_payment_status: null,
    created_at: "2026-01-01T00:00:00Z",
    execution: {
      commercial_status: "pre_commit",
      fulfillment_status: "not_started",
      billing_status: "not_invoiced",
      reservation_status: "not_reserved",
      ready_to_ship: false,
      has_backorder: true,
      backorder_line_count: 1,
    },
  },
  {
    id: "order-confirmed",
    order_number: "ORD-CONFIRMED-001",
    status: "confirmed",
    customer_id: "customer-2",
    total_amount: "1050.00",
    sales_team: [
      {
        sales_person: "Alice Chen",
        allocated_percentage: "60.00",
        commission_rate: "5.00",
        allocated_amount: "30.00",
      },
      {
        sales_person: "Bob Lin",
        allocated_percentage: "40.00",
        commission_rate: "2.50",
        allocated_amount: "10.00",
      },
    ],
    total_commission: "40.00",
    invoice_number: "AA00000001",
    invoice_payment_status: "unpaid",
    created_at: "2026-01-02T00:00:00Z",
    execution: {
      commercial_status: "committed",
      fulfillment_status: "ready_to_ship",
      billing_status: "unpaid",
      reservation_status: "reserved",
      ready_to_ship: true,
      has_backorder: false,
      backorder_line_count: 0,
    },
  },
];

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

vi.mock("../../domain/orders/hooks/useOrders", () => ({
  useOrderDetail: () => ({
    order: detailOrder,
    loading: false,
    error: null,
    reload: vi.fn(),
  }),
  useOrders: () => ({
    items: listItems,
    total: listItems.length,
    page: 1,
    pageSize: 20,
    loading: false,
    error: null,
    reload: vi.fn(),
  }),
  statusBadgeVariant: () => "neutral",
  statusLabel: (status: string) => status,
}));

vi.mock("../../lib/api/orders", () => ({
  updateOrderStatus: vi.fn(),
}));

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canWrite: permissionMock.canWrite,
  }),
}));

vi.mock("../../components/customers/CustomerCombobox", () => ({
  CustomerCombobox: () => <div>Customer filter</div>,
}));

vi.mock("../../components/filters/SearchInput", () => ({
  SearchInput: () => <div>Search filter</div>,
}));

vi.mock("../../components/filters/DateRangeFilter", () => ({
  DateRangeFilter: () => <div>Date filter</div>,
}));

vi.mock("../../components/filters/StatusMultiSelect", () => ({
  StatusMultiSelect: () => <div>Status filter</div>,
}));

vi.mock("../../components/filters/ActiveFilterBar", () => ({
  ActiveFilterBar: () => <div>Active filters</div>,
}));

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location-search">{location.search}</output>;
}

beforeEach(() => {
  permissionMock.canWrite.mockReset();
  permissionMock.canWrite.mockImplementation((feature) => feature === "orders");
  detailOrder = {
    ...detailOrder,
    status: "confirmed",
    invoice_id: "invoice-1",
    invoice_number: "AA00000001",
    execution: {
      commercial_status: "committed",
      fulfillment_status: "ready_to_ship",
      billing_status: "unpaid",
      reservation_status: "reserved",
      ready_to_ship: true,
      has_backorder: false,
      backorder_line_count: 0,
    },
  };
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("Order workflow presentation", () => {
  it("separates fulfillment actions from billing context on the detail view", () => {
    render(
      <ToastProvider>
        <MemoryRouter>
          <OrderDetail orderId="order-1" onBack={() => undefined} />
        </MemoryRouter>
      </ToastProvider>,
    );

    expect(screen.getAllByText("Billing Context").length).toBeGreaterThan(0);
    expect(screen.getByText("Workflow timeline")).toBeTruthy();
    expect(screen.getByText("Grouped actions")).toBeTruthy();
    expect(screen.getByText("Commercial actions")).toBeTruthy();
    expect(screen.getByText("Warehouse actions")).toBeTruthy();
    expect(screen.getByText("Billing navigation")).toBeTruthy();
    expect(screen.getByText("Commission split")).toBeTruthy();
    expect(screen.getByText("Alice Chen")).toBeTruthy();
    expect(screen.getAllByText("$40.00").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Ship Order" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "View AA00000001" })).toBeTruthy();
    expect(screen.getAllByText(/unpaid/i).length).toBeGreaterThan(0);
  });

  it("shows fulfillment and billing cues separately on the list surface", () => {
    render(
      <MemoryRouter>
        <OrderList onSelect={() => undefined} />
      </MemoryRouter>,
    );

    expect(screen.getByText("ORD-PENDING-001")).toBeTruthy();
    expect(screen.getByText("ORD-CONFIRMED-001")).toBeTruthy();
    expect(screen.getByText("Pre-commit intake")).toBeTruthy();
    expect(screen.getByText("Commercially committed")).toBeTruthy();
    expect(screen.getByText("Reserved")).toBeTruthy();
    expect(screen.getByText("Backorder risk: 1 line")).toBeTruthy();
    expect(screen.getByText("Invoice on confirmation")).toBeTruthy();
    expect(screen.getByText("Commission")).toBeTruthy();
    expect(screen.getByText("2 reps")).toBeTruthy();
    expect(screen.getAllByText("Unpaid").length).toBeGreaterThan(0);
  });

  it("syncs quick views into the URL state", () => {
    render(
      <MemoryRouter initialEntries={["/orders"]}>
        <LocationProbe />
        <OrderList onSelect={() => undefined} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Ready to ship" }));

    expect(screen.getByTestId("location-search").textContent).toContain("view=ready_to_ship");
  });
});