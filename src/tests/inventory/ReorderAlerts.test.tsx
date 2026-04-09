import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReorderAlerts } from "../../domain/inventory/components/ReorderAlerts";
import { clearTestToken, setTestToken } from "../helpers/auth";

const warehousesResponse = {
  items: [
    {
      id: "wh-1",
      tenant_id: "00000000-0000-0000-0000-000000000001",
      name: "Main Warehouse",
      code: "MAIN",
      location: "Taipei",
      address: null,
      contact_email: null,
      is_active: true,
      created_at: "2026-04-01T00:00:00Z",
    },
  ],
  total: 1,
};

const alertsResponse = {
  items: [
    {
      id: "alert-1",
      product_id: "product-1",
      product_name: "Ultra Long Product Name for Layout Pressure Test 001",
      warehouse_id: "wh-1",
      warehouse_name: "Main Warehouse",
      current_stock: 3,
      reorder_point: 25,
      status: "pending",
      created_at: "2026-04-01T00:00:00Z",
      acknowledged_at: null,
      acknowledged_by: null,
    },
  ],
  total: 1,
};

function jsonResponse(body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  }));
}

describe("ReorderAlerts", () => {
  beforeEach(() => {
    setTestToken();
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);

      if (url.includes("/api/v1/inventory/warehouses")) {
        return jsonResponse(warehousesResponse) as ReturnType<typeof fetch>;
      }

      if (url.includes("/api/v1/inventory/alerts/reorder")) {
        return jsonResponse(alertsResponse) as ReturnType<typeof fetch>;
      }

      return jsonResponse({}) as ReturnType<typeof fetch>;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearTestToken();
  });

  it("keeps the reorder table scrollable and action button unwrapped", async () => {
    render(<ReorderAlerts />);

    const table = await screen.findByRole("table");
    const acknowledgeButton = await screen.findByRole("button", {
      name: /Acknowledge alert for Ultra Long Product Name for Layout Pressure Test 001/i,
    });

    expect(table.className).toContain("min-w-[760px]");
    expect(acknowledgeButton.className).toContain("whitespace-nowrap");
    expect(acknowledgeButton.closest("td")?.className).toContain("whitespace-nowrap");
  });
});