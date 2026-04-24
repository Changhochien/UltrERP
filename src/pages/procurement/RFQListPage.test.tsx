import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const getProcurementSummaryMock = vi.hoisted(() => vi.fn());
const getQuoteTurnaroundStatsMock = vi.hoisted(() => vi.fn());
const getSupplierPerformanceStatsMock = vi.hoisted(() => vi.fn());

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../components/layout/PageLayout", () => ({
  PageHeader: ({ title, description }: { title: string; description?: string }) => (
    <div>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  ),
  SectionCard: ({ children }: { children: React.ReactNode }) => <section>{children}</section>,
}));

vi.mock("../../components/ui/button", () => ({
  Button: ({
    children,
    onClick,
    disabled,
    type = "button",
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    type?: "button" | "submit";
  }) => (
    <button type={type} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  ),
}));

vi.mock("../../components/ui/input", () => ({
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}));

vi.mock("../../components/ui/StatusBadge", () => ({
  StatusBadge: ({ status }: { status: string }) => <span>{status}</span>,
}));

vi.mock("../../domain/procurement/hooks/useRFQ", () => ({
  useRFQList: () => ({
    data: {
      items: [
        {
          id: "rfq-1",
          name: "PRQ-0001",
          status: "submitted",
          company: "UltrERP Taiwan",
          transaction_date: "2026-04-24",
          supplier_count: 3,
          quotes_received: 2,
        },
      ],
      page: 1,
      pages: 1,
      total: 1,
    },
    loading: false,
    error: null,
  }),
}));

vi.mock("../../lib/api/procurement", () => ({
  getProcurementSummary: getProcurementSummaryMock,
  getQuoteTurnaroundStats: getQuoteTurnaroundStatsMock,
  getSupplierPerformanceStats: getSupplierPerformanceStatsMock,
}));

afterEach(() => {
  cleanup();
  getProcurementSummaryMock.mockReset();
  getQuoteTurnaroundStatsMock.mockReset();
  getSupplierPerformanceStatsMock.mockReset();
});

describe("RFQListPage", () => {
  it("renders procurement reporting insights on the sourcing workspace", async () => {
    getProcurementSummaryMock.mockResolvedValue({
      period: { from: "2026-03-25", to: "2026-04-24" },
      rfqs: { total: 18, submitted: 12, pending: 6 },
      supplier_quotations: { total: 14, submitted: 9, pending: 5 },
      awards: { total: 4 },
      purchase_orders: { total: 9, active: 7, draft: 2 },
      supplier_controls: { blocked_suppliers: 2, warned_suppliers: 5 },
    });
    getQuoteTurnaroundStatsMock.mockResolvedValue({
      rfq_id: null,
      total_quotes: 9,
      avg_turnaround_days: 3.5,
      min_turnaround_days: 1.2,
      max_turnaround_days: 6.8,
    });
    getSupplierPerformanceStatsMock.mockResolvedValue({
      supplier_id: null,
      overall: {
        total_quotes: 6,
        awarded_quotes: 4,
        award_rate: 65.5,
      },
      by_supplier: [
        {
          supplier_name: "Alpha Parts Co.",
          supplier_id: "sup-1",
          total_quotes: 5,
          awarded_quotes: 3,
          award_rate: 60,
        },
        {
          supplier_name: "Beta Supplies Ltd.",
          supplier_id: "sup-2",
          total_quotes: 2,
          awarded_quotes: 2,
          award_rate: 100,
        },
      ],
      supplier_controls: {
        total_suppliers: 8,
        blocked_count: 2,
        warn_rfq_count: 1,
        warn_po_count: 1,
        prevent_rfq_count: 1,
        prevent_po_count: 1,
      },
    });

    const { RFQListPage } = await import("./RFQListPage");

    render(
      <MemoryRouter>
        <RFQListPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(getProcurementSummaryMock).toHaveBeenCalledTimes(1);
      expect(getQuoteTurnaroundStatsMock).toHaveBeenCalledTimes(1);
      expect(getSupplierPerformanceStatsMock).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText("procurement.reporting.title")).toBeTruthy();
    expect(screen.getByText("12 / 18")).toBeTruthy();
    expect(screen.getByText("3.5")).toBeTruthy();
    expect(screen.getByText("65.5%")).toBeTruthy();
    expect(screen.getByText("Alpha Parts Co.")).toBeTruthy();
  });
});