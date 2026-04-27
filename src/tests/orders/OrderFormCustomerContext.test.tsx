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
  CustomerCombobox: ({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder?: string }) => (
    <input
      aria-label="Customer ID"
      value={value}
      placeholder={placeholder}
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

describe("OrderForm customer context", () => {
  it("preserves the preselected customer when creating an order", async () => {
    createMock.mockResolvedValue({ id: "order-123" });
    const onCreated = vi.fn();

    render(
      <MemoryRouter>
        <OrderForm
          initialCustomerId="cust-123"
          onCreated={onCreated}
          onCancel={() => undefined}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText(/customer context/i)).toBeTruthy();
    expect((screen.getByLabelText("Customer ID") as HTMLInputElement).value).toBe("cust-123");

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

    fireEvent.click(screen.getByRole("button", { name: "Create Order" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith(
        expect.objectContaining({
          customer_id: "cust-123",
        }),
      );
    });
    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledWith("order-123");
    });
  });

  it("submits quotation lineage fields when created from quotation handoff", async () => {
    createMock.mockResolvedValue({ id: "order-234" });

    render(
      <MemoryRouter>
        <OrderForm
          initialValues={{
            customer_id: "cust-456",
            source_quotation_id: "qtn-456",
            crm_context_snapshot: {
              source_document_type: "quotation",
              party_label: "Rotor Works",
              utm_source: "expo",
              utm_medium: "field",
              utm_campaign: "spring-2026",
              utm_content: "hero-banner",
              utm_attribution_origin: "source_document",
            },
            notes: "Initial commercial offer.",
            lines: [
              {
                product_id: "prod-2",
                source_quotation_line_no: 3,
                description: "Prefilled rotor",
                quantity: 1,
                list_unit_price: 100,
                unit_price: 100,
                discount_amount: 0,
                tax_policy_code: "standard",
              },
            ],
          }}
          conversionSource={{ quotationId: "qtn-456", partyLabel: "Rotor Works" }}
          onCreated={() => undefined}
          onCancel={() => undefined}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText(/quoted commercial context/i)).toBeTruthy();
    expect((screen.getByLabelText("UTM Source") as HTMLInputElement).value).toBe("expo");
    fireEvent.change(screen.getByLabelText("UTM Source"), {
      target: { value: "partner" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Order" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith(
        expect.objectContaining({
          customer_id: "cust-456",
          source_quotation_id: "qtn-456",
          utm_source: "partner",
          utm_medium: "field",
          utm_campaign: "spring-2026",
          utm_content: "hero-banner",
          crm_context_snapshot: expect.objectContaining({
            party_label: "Rotor Works",
          }),
          lines: [
            expect.objectContaining({
              product_id: "prod-2",
              source_quotation_line_no: 3,
            }),
          ],
        }),
      );
    });
  });

  it("allows clearing inherited quotation attribution before create", async () => {
    createMock.mockResolvedValue({ id: "order-345" });

    render(
      <MemoryRouter>
        <OrderForm
          initialValues={{
            customer_id: "cust-456",
            source_quotation_id: "qtn-456",
            crm_context_snapshot: {
              source_document_type: "quotation",
              party_label: "Rotor Works",
              utm_source: "expo",
              utm_medium: "field",
              utm_campaign: "spring-2026",
              utm_content: "hero-banner",
              utm_attribution_origin: "source_document",
            },
            lines: [
              {
                product_id: "prod-2",
                source_quotation_line_no: 3,
                description: "Prefilled rotor",
                quantity: 1,
                list_unit_price: 100,
                unit_price: 100,
                discount_amount: 0,
                tax_policy_code: "standard",
              },
            ],
          }}
          conversionSource={{ quotationId: "qtn-456", partyLabel: "Rotor Works" }}
          onCreated={() => undefined}
          onCancel={() => undefined}
        />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("UTM Source"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Order" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith(
        expect.objectContaining({
          customer_id: "cust-456",
          source_quotation_id: "qtn-456",
          utm_source: "",
          utm_medium: "field",
          utm_campaign: "spring-2026",
          utm_content: "hero-banner",
        }),
      );
    });
  });
});