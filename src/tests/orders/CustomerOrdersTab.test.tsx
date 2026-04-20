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
});