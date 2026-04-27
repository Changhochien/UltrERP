import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CustomerStatementTab } from "@/domain/customers/components/CustomerStatementTab";
import { getCustomerStatement } from "../../lib/api/customers";
import { setAppTimeGetter } from "../../lib/time";

vi.mock("../../lib/api/customers", () => ({
  getCustomerStatement: vi.fn(),
}));

describe("CustomerStatementTab", () => {
  beforeEach(() => {
    setAppTimeGetter(() => new Date("2026-03-31T16:30:00Z"));
    vi.mocked(getCustomerStatement).mockResolvedValue({
      customer_id: "customer-1",
      company_name: "Acme Trading",
      currency_code: "TWD",
      opening_balance: "100.00",
      current_balance: "200.00",
      lines: [
        {
          date: "2026-04-01",
          type: "invoice",
          reference: "Invoice INV-001",
          description: "April shipment",
          debit: "100.00",
          credit: "0.00",
          balance: "200.00",
        },
      ],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    setAppTimeGetter(() => new Date());
  });

  it("uses Taiwan calendar dates for the default statement range and rendered lines", async () => {
    render(<CustomerStatementTab customerId="customer-1" customerName="Acme Trading" />);

    expect(screen.queryByText("Mar 31, 2026")).toBeNull();
    await waitFor(() => {
      expect(getCustomerStatement).toHaveBeenCalledWith(
        "customer-1",
        "2025-04-01",
        "2026-04-01",
      );
    });

    expect((await screen.findAllByText("Apr 1, 2026")).length).toBeGreaterThan(0);
  });
});