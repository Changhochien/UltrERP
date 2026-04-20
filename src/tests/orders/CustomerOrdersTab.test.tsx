import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { CustomerOrdersTab } from "../../components/customers/CustomerOrdersTab";

const navigateMock = vi.fn();
const fetchOrdersMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../../lib/api/orders", () => ({
  fetchOrders: (...args: unknown[]) => fetchOrdersMock(...args),
}));

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    canWrite: (permission: string) => permission === "orders",
  }),
}));

afterEach(() => {
  navigateMock.mockReset();
  fetchOrdersMock.mockReset();
  vi.clearAllMocks();
});

describe("CustomerOrdersTab", () => {
  it("offers a customer-linked order entry point", async () => {
    fetchOrdersMock.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    render(
      <MemoryRouter>
        <CustomerOrdersTab customerId="cust-123" />
      </MemoryRouter>,
    );

    const button = await screen.findByRole("button", { name: "Create Order" });
    fireEvent.click(button);

    expect(navigateMock).toHaveBeenCalledWith("/orders/new?customer_id=cust-123");
  });

  it("sorts customer orders by order number when the header is clicked", async () => {
    fetchOrdersMock.mockResolvedValue({
      items: [
        {
          id: "order-2",
          order_number: "ORD-200",
          created_at: "2026-04-02T00:00:00Z",
          total_amount: "200.00",
          status: "confirmed",
        },
        {
          id: "order-1",
          order_number: "ORD-100",
          created_at: "2026-04-01T00:00:00Z",
          total_amount: "100.00",
          status: "pending",
        },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    });

    render(
      <MemoryRouter>
        <CustomerOrdersTab customerId="cust-123" />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getAllByText(/ORD-/).map((node) => node.textContent)).toEqual([
        "ORD-200",
        "ORD-100",
      ]);
    });

    fireEvent.click(screen.getByRole("button", { name: "Order #" }));

    await waitFor(() => {
      expect(screen.getAllByText(/ORD-/).map((node) => node.textContent)).toEqual([
        "ORD-100",
        "ORD-200",
      ]);
    });
  });
});