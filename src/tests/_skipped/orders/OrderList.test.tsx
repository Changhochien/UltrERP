import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { OrderList } from "../../domain/orders/components/OrderList";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function mockFetchOrders(items: object[], total = 0) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({
      items,
      total,
      page: 1,
      page_size: 20,
    }),
  } as Response);
}

describe("OrderList", () => {
  const noop = () => {};

  it("renders heading", async () => {
    mockFetchOrders([]);
    render(
      <MemoryRouter>
        <OrderList onSelect={noop} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Orders")).toBeTruthy();
  });

  it("shows empty message when no orders", async () => {
    mockFetchOrders([]);
    render(
      <MemoryRouter>
        <OrderList onSelect={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("No orders found.")).toBeTruthy();
    });
  });

  it("renders order rows from API", async () => {
    mockFetchOrders(
      [
        {
          id: "order-1",
          order_number: "ORD-20260401-ABCD1234",
          status: "pending",
          customer_id: "cust-1",
          total_amount: "1050.00",
          created_at: "2026-04-01T00:00:00Z",
        },
      ],
      1,
    );
    render(
      <MemoryRouter>
        <OrderList onSelect={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("ORD-20260401-ABCD1234")).toBeTruthy();
      expect(screen.getAllByText("Pending").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows status filter dropdown", () => {
    mockFetchOrders([]);
    render(
      <MemoryRouter>
        <OrderList onSelect={noop} />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText("Status:")).toBeTruthy();
  });
});
