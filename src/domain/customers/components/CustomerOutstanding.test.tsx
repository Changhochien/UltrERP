import type { ReactNode } from "react";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CustomerOutstanding } from "./CustomerOutstanding";

const useCustomerOutstandingMock = vi.hoisted(() => vi.fn());

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key,
  }),
}));

vi.mock("../../../components/layout/PageLayout", () => ({
  SectionCard: ({ title, description, children }: { title: string; description: string; children: ReactNode }) => (
    <section>
      <h2>{title}</h2>
      <p>{description}</p>
      {children}
    </section>
  ),
  SurfaceMessage: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

vi.mock("../../../components/ui/badge", () => ({
  Badge: ({ children }: { children: ReactNode }) => <span>{children}</span>,
}));

vi.mock("../../invoices/hooks/useInvoices", () => ({
  useCustomerOutstanding: (...args: Parameters<typeof useCustomerOutstandingMock>) =>
    useCustomerOutstandingMock(...args),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CustomerOutstanding", () => {
  it("shows a loading state", () => {
    useCustomerOutstandingMock.mockReturnValue({ summary: null, loading: true, error: null });

    render(<CustomerOutstanding customerId="cust-1" />);

    expect(screen.getByText("Loading outstanding…")).toBeTruthy();
  });

  it("shows an error state", () => {
    useCustomerOutstandingMock.mockReturnValue({ summary: null, loading: false, error: "boom" });

    render(<CustomerOutstanding customerId="cust-1" />);

    expect(screen.getByText("Error: boom")).toBeTruthy();
  });

  it("renders the outstanding balance summary", () => {
    useCustomerOutstandingMock.mockReturnValue({
      loading: false,
      error: null,
      summary: {
        total_outstanding: "1200.00",
        overdue_count: 1,
        overdue_amount: "500.00",
        invoice_count: 3,
        currency_code: "TWD",
      },
    });

    render(<CustomerOutstanding customerId="cust-1" />);

    expect(screen.getByTestId("customer-outstanding")).toBeTruthy();
    expect(screen.getByText("Outstanding Balance")).toBeTruthy();
    expect(screen.getByText(/TWD 1200\.00/)).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("1 invoices (TWD 500.00)")).toBeTruthy();
  });
});