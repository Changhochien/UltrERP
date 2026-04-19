import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { OrderForm } from "../../domain/orders/components/OrderForm";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function mockPaymentTermsFetch() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    const urlStr = typeof url === "string" ? url : url.toString();

    if (urlStr.includes("/payment-terms")) {
      return {
        ok: true,
        json: async () => ({
          items: [
            { code: "NET_30", label: "Net 30", days: 30 },
            { code: "NET_60", label: "Net 60", days: 60 },
          ],
          total: 2,
        }),
      } as Response;
    }

    if (urlStr.includes("/check-stock")) {
      return {
        ok: true,
        json: async () => ({
          product_id: "test-pid",
          warehouses: [
            { warehouse_id: "wh-1", warehouse_name: "Main", available: 5 },
          ],
          total_available: 5,
        }),
      } as Response;
    }

    return { ok: false, json: async () => ({}) } as Response;
  });
}

describe("OrderForm — stock display", () => {
  const noop = () => {};

  it("shows Stock column header", async () => {
    mockPaymentTermsFetch();
    render(
      <MemoryRouter>
        <OrderForm onCreated={noop} onCancel={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Stock")).toBeTruthy();
    });
  });

  it("shows insufficient stock warning when quantity exceeds available", async () => {
    const spy = mockPaymentTermsFetch();
    render(
      <MemoryRouter>
        <OrderForm onCreated={noop} onCancel={noop} />
      </MemoryRouter>,
    );
    // Wait for payment terms to load
    await waitFor(() => {
      expect(screen.getByText("New Order")).toBeTruthy();
    });

    // Enter a UUID-length product_id to trigger stock check
    const productInput = screen.getByLabelText("Line 1 product");
    fireEvent.change(productInput, {
      target: { value: "00000000-0000-0000-0000-000000000001" },
    });

    // Set quantity higher than mock's total_available (5)
    const qtyInput = screen.getByLabelText("Line 1 quantity");
    fireEvent.change(qtyInput, { target: { value: "10" } });

    // Wait for the stock warning to appear
    await waitFor(() => {
      expect(screen.getByText(/Insufficient stock: 5 units available/)).toBeTruthy();
    });
    spy.mockRestore();
  });
});
