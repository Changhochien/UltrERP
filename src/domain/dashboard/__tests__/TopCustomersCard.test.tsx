import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { TopCustomersCard } from "../components/TopCustomersCard";

vi.mock("../hooks/useDashboard", () => ({
  useTopCustomers: vi.fn(),
}));

import { useTopCustomers } from "../hooks/useDashboard";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("TopCustomersCard", () => {
  it("renders loading skeleton", () => {
    (useTopCustomers as ReturnType<typeof vi.fn>).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
      period: "month",
      setPeriod: vi.fn(),
      anchorDate: "2026-04-01",
      setAnchorDate: vi.fn(),
    });
    const { container } = render(<TopCustomersCard />);
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("renders error state", () => {
    (useTopCustomers as ReturnType<typeof vi.fn>).mockReturnValue({
      data: null,
      isLoading: false,
      error: "Network error",
      refetch: vi.fn(),
      period: "month",
      setPeriod: vi.fn(),
      anchorDate: "2026-04-01",
      setAnchorDate: vi.fn(),
    });
    render(<TopCustomersCard />);
    expect(screen.getByText("Network error")).toBeTruthy();
  });

  it("renders customers table with data", () => {
    (useTopCustomers as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        period: "month",
        start_date: "2026-04-01",
        end_date: "2026-04-30",
        customers: [
          { customer_id: "1", company_name: "Acme Corp", total_revenue: "50000.00", invoice_count: 10, last_invoice_date: "2026-04-01" },
          { customer_id: "2", company_name: "Beta LLC", total_revenue: "30000.00", invoice_count: 5, last_invoice_date: "2026-04-05" },
        ],
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      period: "month",
      setPeriod: vi.fn(),
      anchorDate: "2026-04-01",
      setAnchorDate: vi.fn(),
    });
    render(<TopCustomersCard />);
    expect(screen.getByText("Acme Corp")).toBeTruthy();
    expect(screen.getByText("Beta LLC")).toBeTruthy();
    expect(screen.getByText("NT$ 50,000.00")).toBeTruthy();
    expect(screen.getByText("NT$ 30,000.00")).toBeTruthy();
    expect(screen.getByText("Period: 2026-04-01 to 2026-04-30")).toBeTruthy();
    expect(screen.getByText("Top 2 total: NT$ 80,000.00")).toBeTruthy();
    expect(screen.getByText("Last invoice 2026-04-01")).toBeTruthy();
    expect(screen.getByText("Avg NT$ 5,000.00")).toBeTruthy();
    expect((screen.getByLabelText("Anchor month") as HTMLInputElement).value).toBe("2026-04");
  });

  it("renders empty state", () => {
    (useTopCustomers as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { period: "month", start_date: "2026-04-01", end_date: "2026-04-30", customers: [] },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      period: "month",
      setPeriod: vi.fn(),
      anchorDate: "2026-04-01",
      setAnchorDate: vi.fn(),
    });
    render(<TopCustomersCard />);
    expect(screen.getByTestId("top-customers-table")).toBeTruthy();
  });
});
