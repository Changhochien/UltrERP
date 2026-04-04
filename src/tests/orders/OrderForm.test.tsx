import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { OrderForm } from "../../domain/orders/components/OrderForm";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function mockPaymentTermsFetch() {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({
      items: [
        { code: "NET_30", label: "Net 30", days: 30 },
        { code: "NET_60", label: "Net 60", days: 60 },
        { code: "COD", label: "Cash on Delivery", days: 0 },
      ],
      total: 3,
    }),
  } as Response);
}

describe("OrderForm", () => {
  const noop = () => {};

  it("renders heading after loading", async () => {
    mockPaymentTermsFetch();
    render(
      <MemoryRouter>
        <OrderForm onCreated={noop} onCancel={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("New Order")).toBeTruthy();
    });
  });

  it("shows loading state initially", () => {
    mockPaymentTermsFetch();
    render(
      <MemoryRouter>
        <OrderForm onCreated={noop} onCancel={noop} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Loading…")).toBeTruthy();
  });

  it("renders form fields after payment terms load", async () => {
    mockPaymentTermsFetch();
    render(
      <MemoryRouter>
        <OrderForm onCreated={noop} onCancel={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByLabelText("Customer ID:")).toBeTruthy();
      expect(screen.getByLabelText("Payment terms:")).toBeTruthy();
      expect(screen.getByLabelText("Notes:")).toBeTruthy();
    });
  });

  it("renders cancel button", async () => {
    mockPaymentTermsFetch();
    render(
      <MemoryRouter>
        <OrderForm onCreated={noop} onCancel={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Cancel")).toBeTruthy();
    });
  });

  it("has disabled submit when fields are empty", async () => {
    mockPaymentTermsFetch();
    render(
      <MemoryRouter>
        <OrderForm onCreated={noop} onCancel={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      const btn = screen.getByText("Create Order");
      expect((btn as HTMLButtonElement).disabled).toBe(true);
    });
  });

  it("renders all payment terms options with NET_30 as default", async () => {
    mockPaymentTermsFetch();
    render(
      <MemoryRouter>
        <OrderForm onCreated={noop} onCancel={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      const select = screen.getByLabelText("Payment terms:") as HTMLSelectElement;
      expect(select.value).toBe("NET_30");
      const options = select.querySelectorAll("option");
      expect(options.length).toBe(3);
      expect(options[0].textContent).toBe("Net 30");
      expect(options[1].textContent).toBe("Net 60");
      expect(options[2].textContent).toBe("Cash on Delivery");
    });
  });

  it("submits order and calls onCreated with returned id", async () => {
    const orderId = "00000000-0000-0000-0000-000000000099";
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
      const urlStr = typeof url === "string" ? url : url.toString();
      if (urlStr.includes("/payment-terms")) {
        return {
          ok: true,
          json: async () => ({
            items: [{ code: "NET_30", label: "Net 30", days: 30 }],
            total: 1,
          }),
        } as Response;
      }
      if (urlStr.includes("/check-stock")) {
        return {
          ok: true,
          json: async () => ({ product_id: "", warehouses: [], total_available: 100 }),
        } as Response;
      }
      if (urlStr.includes("/orders") && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            id: orderId,
            order_number: "ORD-TEST",
            status: "pending",
            customer_id: "cust-1",
            lines: [],
            total_amount: "100.00",
          }),
        } as Response;
      }
      return { ok: false, json: async () => ({}) } as Response;
    });

    const onCreated = vi.fn();
    render(
      <MemoryRouter>
        <OrderForm onCreated={onCreated} onCancel={noop} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText("New Order")).toBeTruthy());

    // Fill required fields
    fireEvent.change(screen.getByLabelText("Customer ID:"), {
      target: { value: "00000000-0000-0000-0000-000000000001" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 product"), {
      target: { value: "00000000-0000-0000-0000-000000000002" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 description"), {
      target: { value: "Widget" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 quantity"), {
      target: { value: "5" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 unit price"), {
      target: { value: "10" },
    });

    // Submit
    const submitBtn = screen.getByText("Create Order");
    expect((submitBtn as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledWith(orderId);
    });
  });
});
