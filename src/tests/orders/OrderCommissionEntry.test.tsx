import "../helpers/i18n";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { OrderForm } from "../../domain/orders/components/OrderForm";

const createMock = vi.fn();
const trackEventMock = vi.fn();

vi.mock("../../domain/orders/hooks/useOrders", () => ({
  usePaymentTerms: () => ({
    items: [{ code: "NET_30", label: "Net 30", days: 30 }],
    loading: false,
    error: null,
  }),
  useCreateOrder: () => ({
    create: (...args: unknown[]) => createMock(...args),
    submitting: false,
    error: null,
    fieldErrors: [],
  }),
}));

vi.mock("@/domain/customers/components/CustomerCombobox", () => ({
  CustomerCombobox: ({ value, onChange }: { value: string; onChange: (value: string) => void }) => (
    <input
      aria-label="Customer ID"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  ),
}));

vi.mock("../../components/products/ProductCombobox", () => ({
  ProductCombobox: ({ value, onChange, onProductSelected }: { value: string; onChange: (value: string) => void; onProductSelected?: (product: { name: string }) => void }) => (
    <input
      aria-label="Line 1 product"
      value={value}
      onChange={(event) => {
        onChange(event.target.value);
        onProductSelected?.({ name: "Widget" });
      }}
    />
  ),
}));

vi.mock("../../lib/analytics", () => ({
  trackEvent: (...args: unknown[]) => trackEventMock(...args),
  AnalyticsEvents: {
    ORDER_CREATED: "order_created",
  },
}));

beforeEach(() => {
  createMock.mockReset();
  trackEventMock.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("Order commission entry", () => {
  it("submits commission assignments with the create payload", async () => {
    createMock.mockResolvedValue({ id: "order-123" });

    render(
      <MemoryRouter>
        <OrderForm onCreated={() => undefined} onCancel={() => undefined} />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Customer ID"), {
      target: { value: "cust-123" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 product"), {
      target: { value: "prod-1" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 description"), {
      target: { value: "Widget" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 quantity"), {
      target: { value: "2" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 unit price"), {
      target: { value: "10" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Add sales rep" }));
    fireEvent.change(screen.getByLabelText("Commission rep 1 salesperson"), {
      target: { value: "Alice Chen" },
    });
    fireEvent.change(screen.getByLabelText("Commission rep 1 allocation percentage"), {
      target: { value: "60" },
    });
    fireEvent.change(screen.getByLabelText("Commission rep 1 commission rate"), {
      target: { value: "5" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create Order" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith(
        expect.objectContaining({
          customer_id: "cust-123",
          sales_team: [
            {
              sales_person: "Alice Chen",
              allocated_percentage: 60,
              commission_rate: 5,
            },
          ],
        }),
      );
    });
  });

  it("normalizes discount percent to the backend decimal fraction", async () => {
    createMock.mockResolvedValue({ id: "order-456" });

    render(
      <MemoryRouter>
        <OrderForm onCreated={() => undefined} onCancel={() => undefined} />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Customer ID"), {
      target: { value: "cust-123" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 product"), {
      target: { value: "prod-1" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 description"), {
      target: { value: "Widget" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 quantity"), {
      target: { value: "2" },
    });
    fireEvent.change(screen.getByLabelText("Line 1 unit price"), {
      target: { value: "10" },
    });
    fireEvent.change(screen.getByLabelText(/Disc. %/i), {
      target: { value: "5" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create Order" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith(
        expect.objectContaining({
          discount_percent: 0.05,
        }),
      );
    });
  });
});