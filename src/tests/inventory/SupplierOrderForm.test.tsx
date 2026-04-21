import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SupplierOrderForm } from "../../domain/inventory/components/SupplierOrderForm";
import { setAppTimeGetter } from "../../lib/time";

const createMock = vi.fn();

vi.mock("../../components/products/ProductCombobox", () => ({
  ProductCombobox: () => <div data-testid="product-combobox" />,
}));

vi.mock("../../domain/inventory/components/SupplierCombobox", () => ({
  SupplierCombobox: () => <div data-testid="supplier-combobox" />,
}));

vi.mock("../../domain/inventory/hooks/useWarehouses", () => ({
  useWarehouses: () => ({ warehouses: [], loading: false }),
}));

vi.mock("../../domain/inventory/hooks/useSupplierOrders", () => ({
  useCreateSupplierOrder: () => ({
    create: createMock,
    submitting: false,
    error: null,
  }),
}));

describe("SupplierOrderForm", () => {
  beforeEach(() => {
    setAppTimeGetter(() => new Date("2026-03-31T16:30:00Z"));
  });

  afterEach(() => {
    vi.clearAllMocks();
    setAppTimeGetter(() => new Date());
  });

  it("uses the Taiwan calendar date for the default order date", () => {
    const { container } = render(
      <SupplierOrderForm onCreated={vi.fn()} onCancel={vi.fn()} />,
    );

    expect(container.querySelector("#so-date")?.textContent).toContain("Apr 1, 2026");
    expect(screen.queryByText("Mar 31, 2026")).toBeNull();
  });
});