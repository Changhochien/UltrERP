import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProductTable } from "../../domain/inventory/components/ProductTable";
import { searchProducts } from "../../lib/api/inventory";

vi.mock("react-i18next", () => ({
  useTranslation: (_ns?: string, options?: { keyPrefix?: string }) => ({
    t: (key: string, vars?: Record<string, unknown>) => {
      if (key === "products" && vars?.count != null) {
        return `${vars.count} products`;
      }
      return options?.keyPrefix ? `${options.keyPrefix}.${key}` : key;
    },
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

vi.mock("../../lib/api/inventory", () => ({
  searchProducts: vi.fn(),
}));

const ACTIVE_PRODUCT = {
  id: "product-active",
  code: "SKU-1",
  name: "Active Widget",
  category: "Hardware",
  status: "active",
  current_stock: 12,
  relevance: 1,
};

const INACTIVE_PRODUCT = {
  id: "product-inactive",
  code: "SKU-2",
  name: "Inactive Widget",
  category: "Hardware",
  status: "inactive",
  current_stock: 4,
  relevance: 1,
};

beforeEach(() => {
  vi.mocked(searchProducts).mockImplementation(async (_query, options) => ({
    items: options?.includeInactive ? [INACTIVE_PRODUCT] : [ACTIVE_PRODUCT],
    total: 1,
  }));
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ProductTable", () => {
  it("requests active products by default and can explicitly include inactive rows", async () => {
    render(<ProductTable warehouseId="warehouse-1" />);

    await waitFor(() => {
      expect(searchProducts).toHaveBeenCalledWith(
        "",
        expect.objectContaining({
          warehouseId: "warehouse-1",
          includeInactive: false,
        }),
      );
    });

    expect(await screen.findByText("Active Widget")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "inventory.productGrid.showInactive" }));

    await waitFor(() => {
      expect(searchProducts).toHaveBeenLastCalledWith(
        "",
        expect.objectContaining({
          warehouseId: "warehouse-1",
          includeInactive: true,
        }),
      );
    });

    expect(await screen.findByText("Inactive Widget")).toBeTruthy();
  });
});